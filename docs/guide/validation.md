# Validation

Strawberry Django integrates with Django's validation system to automatically validate GraphQL inputs using Django's model validation, field validators, and forms.

## Overview

Validation in Strawberry Django happens automatically when using `handle_django_errors=True` in mutations. The system calls Django's `Model.full_clean()` before saving, which validates:

- Field-level constraints and validators
- Model-level validation in `clean()` methods
- Unique constraints

For complete details on Django validation, see the [Django Validators documentation](https://docs.djangoproject.com/en/stable/ref/validators/).

## Automatic Validation

Use `handle_django_errors=True` to enable automatic validation:

```python
import strawberry
import strawberry_django
from strawberry_django import mutations

@strawberry_django.input(models.User)
class UserInput:
    email: auto
    username: auto
    age: auto

@strawberry.type
class Mutation:
    create_user: User = mutations.create(
        UserInput,
        handle_django_errors=True  # Automatically validates
    )
```

When validation fails, errors are returned in the GraphQL response:

```graphql
mutation {
  createUser(data: { email: "invalid", age: 15 }) {
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
          "field": "email",
          "message": "Enter a valid email address",
          "kind": "VALIDATION"
        },
        {
          "field": "age",
          "message": "Users must be at least 18 years old",
          "kind": "VALIDATION"
        }
      ]
    }
  }
}
```

## Model Validation

Define validation logic in your Django models using the `clean()` method:

```python
from django.db import models
from django.core.exceptions import ValidationError

class User(models.Model):
    email = models.EmailField(unique=True)
    age = models.IntegerField()
    username = models.CharField(max_length=50)

    def clean(self):
        """Custom model validation"""
        super().clean()  # Always call parent first
        errors = {}

        if self.age < 18:
            errors['age'] = "Must be at least 18 years old"

        if self.username and len(self.username) < 3:
            errors['username'] = "Must be at least 3 characters"

        if errors:
            raise ValidationError(errors)
```

This validation runs automatically when using `handle_django_errors=True`. See [Django Model Validation](https://docs.djangoproject.com/en/stable/ref/models/instances/#validating-objects) for more details.

## Field Validators

Django field validators work automatically with Strawberry Django:

```python
from django.db import models
from django.core.validators import MinValueValidator, RegexValidator

class Product(models.Model):
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    sku = models.CharField(
        max_length=20,
        validators=[RegexValidator(r'^[A-Z0-9-]+$')]
    )
```

See [Django Validators](https://docs.djangoproject.com/en/stable/ref/validators/) for built-in validators and how to create custom validators.

## Custom Mutation Validation

For custom validation logic in mutations, raise `ValidationError` with field-specific errors:

```python
import strawberry
import strawberry_django
from django.core.exceptions import ValidationError

@strawberry.type
class Mutation:
    @strawberry_django.mutation(handle_django_errors=True)
    def create_user(self, email: str, age: int) -> User:
        errors = {}

        if not email or "@" not in email:
            errors["email"] = "Invalid email address"

        if age < 18:
            errors["age"] = "Must be at least 18 years old"

        if errors:
            raise ValidationError(errors)

        return models.User.objects.create(email=email, age=age)
```

## Async Validation

For async mutations, use Django's async ORM methods (Django 4.1+):

```python
import strawberry
from django.core.exceptions import ValidationError

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_article(self, title: str) -> Article:
        # Check for duplicate using async
        exists = await models.Article.objects.filter(title=title).aexists()

        if exists:
            raise ValidationError({'title': "Article with this title already exists"})

        return await models.Article.objects.acreate(title=title)
```

For older Django versions, wrap ORM calls in `sync_to_async`. See [Django Async documentation](https://docs.djangoproject.com/en/stable/topics/async/) for details.

## Form Validation

Integrate Django forms for complex validation:

```python
import strawberry
import strawberry_django
from django import forms
from django.core.exceptions import ValidationError

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'username', 'age']

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("Username already taken")
        return username

@strawberry.type
class Mutation:
    @strawberry_django.mutation
    def create_user(self, data: UserInput) -> User:
        form = UserForm({'email': data.email, 'username': data.username, 'age': data.age})

        if not form.is_valid():
            # Convert form errors to ValidationError
            error_dict = {field: error_list[0] for field, error_list in form.errors.items()}
            raise ValidationError(error_dict)

        return form.save()
```

See [Django Forms documentation](https://docs.djangoproject.com/en/stable/topics/forms/) for more on form validation.

## Best Practices

1. **Always use `handle_django_errors=True`** in mutations to enable automatic validation

2. **Put business logic in `Model.clean()`** instead of scattering it across resolvers

3. **Use dict-style ValidationError** for field-specific errors:

   ```python
   raise ValidationError({'field': 'Error message'})
   ```

4. **Test validation** using the test client:
   ```python
   def test_validation(db):
       client = TestClient("/graphql")
       res = client.query("""
           mutation {
               createUser(data: { email: "invalid", age: 15 }) {
                   ... on OperationInfo {
                       messages { field message }
                   }
               }
           }
       """)
       assert res.data["createUser"]["messages"]
   ```

## Common Issues

### Validation Not Running

If validation isn't running automatically, ensure:

1. You're using `handle_django_errors=True`
2. You're using mutation generators or calling `full_clean()` manually

```python
# ✅ Validation runs automatically
create_user: User = mutations.create(UserInput, handle_django_errors=True)

# ❌ Validation doesn't run
user = User.objects.create(email='invalid')  # Bypasses validation
```

### Unique Constraint Errors

Unique constraints raise `IntegrityError` instead of `ValidationError`. Validate in `clean()` to convert to field errors:

```python
def clean(self):
    if User.objects.filter(email=self.email).exclude(pk=self.pk).exists():
        raise ValidationError({'email': "Email already exists"})
```

## See Also

- [Django Model Validation](https://docs.djangoproject.com/en/stable/ref/models/instances/#validating-objects)
- [Django Validators](https://docs.djangoproject.com/en/stable/ref/validators/)
- [Django Forms](https://docs.djangoproject.com/en/stable/topics/forms/)
- [Error Handling](./error-handling.md) - Comprehensive error handling guide
- [Mutations](./mutations.md) - Mutation basics
