# Validation

Validation is a critical part of any GraphQL API. Strawberry Django provides seamless integration with Django's built-in validation system, including model validation, form validation, and custom validators.

## Table of Contents

- [Overview](#overview)
- [Model Validation](#model-validation)
- [Field-Level Validation](#field-level-validation)
- [Custom Validators](#custom-validators)
- [Form Validation Integration](#form-validation-integration)
- [Input Type Validation](#input-type-validation)
- [Async Validation](#async-validation)
- [Validation Extensions](#validation-extensions)
- [Best Practices](#best-practices)
- [Common Patterns](#common-patterns)
- [Troubleshooting](#troubleshooting)

## Overview

Strawberry Django integrates with Django's validation system at multiple levels:

1. **Model validation** - Uses Django's `Model.full_clean()` automatically
2. **Field validation** - Leverages Django field validators
3. **Form validation** - Integrates with Django forms and ModelForms
4. **Custom validation** - Support for custom validation logic
5. **Extension-based validation** - Validation extension for caching

### When Validation Happens

```python
import strawberry
from strawberry_django import mutations

@strawberry.type
class Mutation:
    create_user: User = mutations.create(
        models.User,
        handle_django_errors=True  # Validation happens automatically
    )
```

By default, validation occurs:

- Before saving in mutations (via `Model.full_clean()`)
- When using `handle_django_errors=True`
- In custom resolvers when you call validation methods

## Model Validation

Django models have a `full_clean()` method that validates all fields and runs model-level validators.

### Basic Model Validation

```python
# models.py
from django.db import models
from django.core.exceptions import ValidationError

class User(models.Model):
    email = models.EmailField(unique=True)
    age = models.IntegerField()
    username = models.CharField(max_length=50)

    def clean(self):
        """Custom model validation"""
        if self.age < 18:
            raise ValidationError("Users must be at least 18 years old")

        if self.username and len(self.username) < 3:
            raise ValidationError({
                'username': "Username must be at least 3 characters"
            })
```

```python
# schema.py
import strawberry
from strawberry_django import mutations
from . import models

@strawberry.type
class Mutation:
    create_user: User = mutations.create(
        models.User,
        handle_django_errors=True  # Automatically calls full_clean()
    )
```

When `handle_django_errors=True`, the mutation will:

1. Create a model instance from input
2. Call `instance.full_clean()` to validate
3. Save if validation passes
4. Return validation errors in a structured format if it fails

### ValidationError Response Format

```graphql
mutation {
  createUser(data: { email: "test@example.com", age: 15, username: "ab" }) {
    ... on User {
      id
      email
    }
    ... on OperationInfo {
      messages {
        field
        message
        kind
      }
    }
  }
}
```

Response with validation errors:

```json
{
  "data": {
    "createUser": {
      "messages": [
        {
          "field": "__all__",
          "message": "Users must be at least 18 years old",
          "kind": "VALIDATION"
        },
        {
          "field": "username",
          "message": "Username must be at least 3 characters",
          "kind": "VALIDATION"
        }
      ]
    }
  }
}
```

### Field Constraints

Django field constraints are automatically validated:

```python
from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    stock = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(10000)]
    )
    sku = models.CharField(
        max_length=20,
        unique=True,
        validators=[RegexValidator(r'^[A-Z0-9-]+$')]
    )
```

All validators run automatically during `full_clean()`.

## Field-Level Validation

Add validation to specific fields using Django's validator framework.

### Built-in Validators

```python
from django.db import models
from django.core.validators import (
    EmailValidator,
    URLValidator,
    RegexValidator,
    MinValueValidator,
    MaxValueValidator,
    MinLengthValidator,
    MaxLengthValidator,
)

class UserProfile(models.Model):
    email = models.EmailField(
        validators=[EmailValidator(message="Invalid email format")]
    )
    website = models.URLField(
        validators=[URLValidator(schemes=['http', 'https'])]
    )
    phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$')]
    )
    bio = models.TextField(
        validators=[
            MinLengthValidator(10),
            MaxLengthValidator(500)
        ]
    )
```

### Custom Field Validators

```python
from django.core.exceptions import ValidationError

def validate_even_number(value):
    if value % 2 != 0:
        raise ValidationError(
            f'{value} is not an even number',
            params={'value': value},
        )

def validate_file_size(value):
    filesize = value.size
    if filesize > 5 * 1024 * 1024:  # 5MB
        raise ValidationError("Maximum file size is 5MB")

class Document(models.Model):
    even_field = models.IntegerField(validators=[validate_even_number])
    file = models.FileField(
        upload_to='documents/',
        validators=[validate_file_size]
    )
```

### Conditional Validation

```python
from django.db import models
from django.core.exceptions import ValidationError

class Subscription(models.Model):
    TIER_CHOICES = [
        ('free', 'Free'),
        ('premium', 'Premium'),
        ('enterprise', 'Enterprise'),
    ]

    tier = models.CharField(max_length=20, choices=TIER_CHOICES)
    max_users = models.IntegerField(null=True, blank=True)
    custom_domain = models.CharField(max_length=255, blank=True)

    def clean(self):
        if self.tier == 'free' and self.max_users and self.max_users > 5:
            raise ValidationError({
                'max_users': "Free tier is limited to 5 users"
            })

        if self.tier == 'enterprise' and not self.custom_domain:
            raise ValidationError({
                'custom_domain': "Enterprise tier requires a custom domain"
            })
```

## Custom Validators

Create reusable validators for complex validation logic.

### Reusable Validator Functions

```python
from django.core.exceptions import ValidationError
import re

def validate_strong_password(value):
    """Validate password strength"""
    if len(value) < 8:
        raise ValidationError("Password must be at least 8 characters")

    if not re.search(r'[A-Z]', value):
        raise ValidationError("Password must contain an uppercase letter")

    if not re.search(r'[a-z]', value):
        raise ValidationError("Password must contain a lowercase letter")

    if not re.search(r'\d', value):
        raise ValidationError("Password must contain a digit")

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
        raise ValidationError("Password must contain a special character")

def validate_no_profanity(value):
    """Check for profanity in text"""
    profanity_list = ['bad', 'words', 'here']  # Use a real list

    for word in profanity_list:
        if word.lower() in value.lower():
            raise ValidationError(
                "Content contains inappropriate language",
                code='profanity'
            )

class UserAccount(models.Model):
    username = models.CharField(
        max_length=50,
        validators=[validate_no_profanity]
    )
    password = models.CharField(
        max_length=128,
        validators=[validate_strong_password]
    )
```

### Class-Based Validators

```python
from django.core.validators import BaseValidator
from django.core.exceptions import ValidationError

class UniqueEmailDomainValidator(BaseValidator):
    """Ensure email domain is unique across users"""
    message = "A user with this email domain already exists"
    code = "duplicate_domain"

    def __call__(self, value):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        domain = value.split('@')[1] if '@' in value else ''

        if User.objects.filter(email__endswith=f'@{domain}').exists():
            raise ValidationError(self.message, code=self.code)

class BusinessHoursValidator(BaseValidator):
    """Validate datetime is within business hours"""
    message = "Must be within business hours (9 AM - 5 PM)"

    def __call__(self, value):
        if value.hour < 9 or value.hour >= 17:
            raise ValidationError(self.message, code='outside_business_hours')

class Appointment(models.Model):
    scheduled_time = models.DateTimeField(
        validators=[BusinessHoursValidator(None)]
    )
```

### Cross-Field Validation

```python
from django.db import models
from django.core.exceptions import ValidationError

class Event(models.Model):
    name = models.CharField(max_length=200)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    max_attendees = models.IntegerField()
    min_attendees = models.IntegerField()

    def clean(self):
        # Date validation
        if self.start_date and self.end_date:
            if self.end_date <= self.start_date:
                raise ValidationError({
                    'end_date': "End date must be after start date"
                })

        # Attendee validation
        if self.min_attendees and self.max_attendees:
            if self.min_attendees > self.max_attendees:
                raise ValidationError({
                    'min_attendees': "Minimum cannot exceed maximum attendees"
                })

        # Business rule validation
        duration = self.end_date - self.start_date
        if duration.days > 30:
            raise ValidationError(
                "Events cannot be longer than 30 days"
            )
```

## Form Validation Integration

Integrate Django forms for complex validation scenarios.

### Using ModelForms

```python
from django import forms
from django.core.exceptions import ValidationError

class UserForm(forms.ModelForm):
    password_confirm = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['email', 'username', 'password']

    def clean_username(self):
        """Field-specific validation"""
        username = self.cleaned_data['username']

        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("Username already taken")

        return username

    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            raise ValidationError("Passwords do not match")

        return cleaned_data
```

```python
# Using forms in mutations
import strawberry
from strawberry_django import mutations
from . import models, forms

@strawberry.type
class Mutation:
    @mutations.create(models.User, handle_django_errors=True)
    def create_user(self, info, data) -> User:
        # Validate using form
        form = forms.UserForm(data)
        if not form.is_valid():
            # Convert form errors to ValidationError
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = error_list[0]
            raise ValidationError(errors)

        # Save using validated data
        return form.save()
```

### Form Validation in Custom Resolvers

```python
import strawberry
from strawberry import mutation
from django.core.exceptions import ValidationError
from . import models, forms

@strawberry.type
class Mutation:
    @mutation
    def register_user(
        self,
        email: str,
        username: str,
        password: str,
        password_confirm: str
    ) -> User:
        # Create form instance
        form = forms.UserForm({
            'email': email,
            'username': username,
            'password': password,
            'password_confirm': password_confirm
        })

        # Validate
        if not form.is_valid():
            error_dict = {}
            for field, errors in form.errors.items():
                error_dict[field] = ', '.join(errors)
            raise ValidationError(error_dict)

        # Save and return
        user = form.save()
        return user
```

## Input Type Validation

Add validation directly to Strawberry input types.

### Basic Input Validation

```python
import strawberry
from typing import Optional
from django.core.exceptions import ValidationError

@strawberry.input
class CreateUserInput:
    email: str
    username: str
    age: int
    password: str

    def __post_init__(self):
        """Validate input after initialization"""
        errors = {}

        # Email validation
        if '@' not in self.email:
            errors['email'] = "Invalid email format"

        # Username validation
        if len(self.username) < 3:
            errors['username'] = "Username must be at least 3 characters"

        # Age validation
        if self.age < 18:
            errors['age'] = "Must be at least 18 years old"

        # Password validation
        if len(self.password) < 8:
            errors['password'] = "Password must be at least 8 characters"

        if errors:
            raise ValidationError(errors)
```

### Using Validators in Input Types

```python
import strawberry
from django.core.validators import EmailValidator, URLValidator
from django.core.exceptions import ValidationError

@strawberry.input
class ProfileInput:
    email: str
    website: Optional[str] = None
    bio: Optional[str] = None

    def __post_init__(self):
        errors = {}

        # Validate email
        email_validator = EmailValidator()
        try:
            email_validator(self.email)
        except ValidationError as e:
            errors['email'] = str(e)

        # Validate website
        if self.website:
            url_validator = URLValidator()
            try:
                url_validator(self.website)
            except ValidationError as e:
                errors['website'] = str(e)

        # Validate bio length
        if self.bio and len(self.bio) > 500:
            errors['bio'] = "Bio must be 500 characters or less"

        if errors:
            raise ValidationError(errors)
```

### Nested Input Validation

```python
import strawberry
from typing import List
from django.core.exceptions import ValidationError

@strawberry.input
class AddressInput:
    street: str
    city: str
    postal_code: str
    country: str

    def __post_init__(self):
        if len(self.postal_code) != 5:
            raise ValidationError({
                'postal_code': "Postal code must be 5 digits"
            })

@strawberry.input
class CreateCompanyInput:
    name: str
    addresses: List[AddressInput]

    def __post_init__(self):
        # Validate company has at least one address
        if not self.addresses:
            raise ValidationError({
                'addresses': "Company must have at least one address"
            })

        # Validate maximum addresses
        if len(self.addresses) > 10:
            raise ValidationError({
                'addresses': "Company cannot have more than 10 addresses"
            })

        # Each AddressInput validates itself in __post_init__
```

## Async Validation

Handle validation in async contexts.

### Async Model Validation

```python
from django.db import models
from django.core.exceptions import ValidationError
from asgiref.sync import sync_to_async

class Article(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()

    async def aclean(self):
        """Async version of clean()"""
        # Check for duplicate titles
        exists = await sync_to_async(
            Article.objects.filter(title=self.title).exists
        )()

        if exists:
            raise ValidationError({
                'title': "Article with this title already exists"
            })
```

### Async Mutations with Validation

```python
import strawberry
from strawberry_django import mutations
from asgiref.sync import sync_to_async
from . import models

@strawberry.type
class Mutation:
    @mutations.create(models.Article, handle_django_errors=True)
    async def create_article(self, info, data) -> Article:
        # Create instance
        instance = models.Article(**data)

        # Async validation
        await instance.aclean()

        # Save
        await sync_to_async(instance.save)()

        return instance
```

### External API Validation

```python
import strawberry
from strawberry import mutation
import httpx
from django.core.exceptions import ValidationError

@strawberry.type
class Mutation:
    @mutation
    async def verify_email(self, email: str) -> bool:
        """Verify email using external API"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.emailverifier.com/verify?email={email}"
            )

            if response.status_code != 200:
                raise ValidationError({
                    'email': "Could not verify email"
                })

            data = response.json()
            if not data.get('is_valid'):
                raise ValidationError({
                    'email': "Email address is not valid"
                })

            return True
```

## Validation Extensions

Use the Django validation cache extension for performance.

### Setup Validation Cache Extension

```python
import strawberry
from strawberry_django.extensions import DjangoValidationCache

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    extensions=[
        DjangoValidationCache(),  # Cache validation results
    ]
)
```

### How It Works

The validation cache extension:

1. Caches `full_clean()` results during a request
2. Prevents duplicate validation calls
3. Improves performance for complex mutations
4. Automatically cleared after each request

```python
@strawberry.type
class Mutation:
    create_user: User = mutations.create(
        models.User,
        handle_django_errors=True  # Uses cached validation
    )

    update_user: User = mutations.update(
        models.User,
        handle_django_errors=True  # Uses cached validation
    )
```

## Best Practices

### 1. Always Use handle_django_errors

```python
# Good
@strawberry.type
class Mutation:
    create_user: User = mutations.create(
        models.User,
        handle_django_errors=True
    )

# Avoid
@strawberry.type
class Mutation:
    create_user: User = mutations.create(models.User)
```

### 2. Put Business Logic in Model.clean()

```python
# Good - business logic in model
class Order(models.Model):
    quantity = models.IntegerField()
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    def clean(self):
        if self.quantity > self.product.stock:
            raise ValidationError("Not enough stock available")

# Avoid - business logic scattered
@mutation
def create_order(quantity: int, product_id: int):
    product = Product.objects.get(id=product_id)
    if quantity > product.stock:  # Logic in resolver
        raise ValidationError("Not enough stock")
```

### 3. Use Validators for Reusable Logic

```python
# Good - reusable validator
def validate_credit_card(value):
    if not luhn_check(value):
        raise ValidationError("Invalid credit card number")

class Payment(models.Model):
    card_number = models.CharField(
        max_length=16,
        validators=[validate_credit_card]
    )

# Avoid - validation in multiple places
def clean(self):
    if not luhn_check(self.card_number):
        raise ValidationError("Invalid credit card number")
```

### 4. Validate Early in Input Types

```python
# Good - validate at input level
@strawberry.input
class CreateOrderInput:
    quantity: int

    def __post_init__(self):
        if self.quantity <= 0:
            raise ValidationError("Quantity must be positive")

# Also good - validate at model level
class Order(models.Model):
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
```

### 5. Structure Validation Errors Clearly

```python
# Good - structured errors
def clean(self):
    errors = {}

    if self.start_date >= self.end_date:
        errors['end_date'] = "Must be after start date"

    if self.price < 0:
        errors['price'] = "Must be non-negative"

    if errors:
        raise ValidationError(errors)

# Avoid - generic errors
def clean(self):
    if self.start_date >= self.end_date or self.price < 0:
        raise ValidationError("Invalid data")
```

## Common Patterns

### Pattern 1: Unique Together Validation

```python
from django.db import models
from django.core.exceptions import ValidationError

class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    semester = models.CharField(max_length=20)

    class Meta:
        unique_together = [['student', 'course', 'semester']]

    def clean(self):
        # Check unique_together with friendly error
        if Enrollment.objects.filter(
            student=self.student,
            course=self.course,
            semester=self.semester
        ).exclude(pk=self.pk).exists():
            raise ValidationError({
                'course': f"Already enrolled in {self.course.name}"
            })
```

### Pattern 2: Status Transition Validation

```python
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    ALLOWED_TRANSITIONS = {
        'pending': ['processing', 'cancelled'],
        'processing': ['shipped', 'cancelled'],
        'shipped': ['delivered'],
        'delivered': [],
        'cancelled': [],
    }

    def clean(self):
        if self.pk:  # Existing order
            old_status = Order.objects.get(pk=self.pk).status

            if self.status != old_status:
                allowed = self.ALLOWED_TRANSITIONS.get(old_status, [])

                if self.status not in allowed:
                    raise ValidationError({
                        'status': f"Cannot change from {old_status} to {self.status}"
                    })
```

### Pattern 3: Conditional Required Fields

```python
class Payment(models.Model):
    METHOD_CHOICES = [
        ('card', 'Credit Card'),
        ('bank', 'Bank Transfer'),
        ('paypal', 'PayPal'),
    ]

    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    card_number = models.CharField(max_length=16, blank=True)
    bank_account = models.CharField(max_length=50, blank=True)
    paypal_email = models.EmailField(blank=True)

    def clean(self):
        if self.method == 'card' and not self.card_number:
            raise ValidationError({
                'card_number': "Required for card payments"
            })

        if self.method == 'bank' and not self.bank_account:
            raise ValidationError({
                'bank_account': "Required for bank transfers"
            })

        if self.method == 'paypal' and not self.paypal_email:
            raise ValidationError({
                'paypal_email': "Required for PayPal payments"
            })
```

### Pattern 4: Budget/Quota Validation

```python
class Project(models.Model):
    name = models.CharField(max_length=200)
    budget = models.DecimalField(max_digits=10, decimal_places=2)

    def get_total_expenses(self):
        return self.expenses.aggregate(
            total=models.Sum('amount')
        )['total'] or 0

class Expense(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='expenses'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def clean(self):
        if self.project:
            current_total = self.project.get_total_expenses()

            if self.pk:  # Update
                old_amount = Expense.objects.get(pk=self.pk).amount
                current_total -= old_amount

            new_total = current_total + self.amount

            if new_total > self.project.budget:
                raise ValidationError({
                    'amount': f"Would exceed budget of {self.project.budget}"
                })
```

## Troubleshooting

### Validation Not Running

**Problem**: Model validation doesn't run automatically.

```python
# Problem: Validation bypassed
User.objects.create(email='invalid', age=5)  # No validation!

# Solution: Use save() with full_clean() or use mutations
user = User(email='invalid', age=5)
user.full_clean()  # Raises ValidationError
user.save()

# Or use mutations (calls full_clean automatically)
create_user: User = mutations.create(
    models.User,
    handle_django_errors=True  # Calls full_clean()
)
```

### Errors Not Showing in GraphQL Response

**Problem**: ValidationError raised but not in response.

```python
# Problem: Missing handle_django_errors
create_user: User = mutations.create(models.User)

# Solution: Enable error handling
create_user: User = mutations.create(
    models.User,
    handle_django_errors=True
)
```

### Async Validation Issues

**Problem**: Sync validation in async context causes errors.

```python
# Problem: Sync database call in async
async def create_user(email: str):
    if User.objects.filter(email=email).exists():  # Error!
        raise ValidationError("Email taken")

# Solution: Use sync_to_async
from asgiref.sync import sync_to_async

async def create_user(email: str):
    exists = await sync_to_async(
        User.objects.filter(email=email).exists
    )()
    if exists:
        raise ValidationError("Email taken")
```

### Unique Constraint Errors

**Problem**: IntegrityError instead of ValidationError.

```python
# Problem: Unique constraint at database level
class User(models.Model):
    email = models.EmailField(unique=True)

# IntegrityError raised instead of ValidationError

# Solution: Validate in clean()
def clean(self):
    if User.objects.filter(email=self.email).exclude(pk=self.pk).exists():
        raise ValidationError({'email': "Email already exists"})
```

### Form Validation in Mutations

**Problem**: Form errors not converted properly.

```python
# Problem: Form errors not raised as ValidationError
form = UserForm(data)
if not form.is_valid():
    return None  # Silent failure

# Solution: Convert form errors
if not form.is_valid():
    error_dict = {}
    for field, errors in form.errors.items():
        error_dict[field] = errors[0]
    raise ValidationError(error_dict)
```

### Cross-Field Validation Timing

**Problem**: Cross-field validation fails due to None values.

```python
# Problem: Fields not set yet
def clean(self):
    if self.end_date <= self.start_date:  # May be None
        raise ValidationError("Invalid dates")

# Solution: Check for None
def clean(self):
    if self.start_date and self.end_date:
        if self.end_date <= self.start_date:
            raise ValidationError("Invalid dates")
```

## See Also

- [Error Handling](error-handling.md) - Comprehensive error handling guide
- [Nested Mutations](nested-mutations.md) - Validation in nested mutations
- [Mutations](mutations.md) - Mutation basics
- [Django Validators](https://docs.djangoproject.com/en/stable/ref/validators/) - Django's validator reference
