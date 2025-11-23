---
title: Error Handling
---

# Error Handling

Proper error handling is crucial for building robust GraphQL APIs. Strawberry Django provides several mechanisms to handle errors gracefully and return meaningful information to clients.

## Django Error Handling in Mutations

Strawberry Django can automatically handle common Django errors and convert them into structured GraphQL responses. This feature is available for mutations using the `handle_django_errors` parameter.

### Basic Usage

```python title="mutations.py"
import strawberry
import strawberry_django
from django.core.exceptions import ValidationError
from typing import cast

@strawberry.type
class Mutation:
    @strawberry_django.mutation(handle_django_errors=True)
    def create_product(self, name: str, price: float) -> Product:
        if price < 0:
            raise ValidationError("Price must be positive")

        product = models.Product.objects.create(
            name=name,
            price=price
        )
        return cast(Product, product)
```

### Handled Exception Types

When `handle_django_errors=True`, the following Django exceptions are automatically handled:

1. **`ValidationError`**: Field validation errors
2. **`PermissionDenied`**: Permission-related errors
3. **`ObjectDoesNotExist`**: Object lookup errors

### Generated Schema

When error handling is enabled, your mutation return type becomes a union:

```graphql
enum OperationMessageKind {
  INFO
  WARNING
  ERROR
  PERMISSION
  VALIDATION
}

type OperationMessage {
  """
  The kind of this message.
  """
  kind: OperationMessageKind!

  """
  The error message.
  """
  message: String!

  """
  The field that caused the error, or null if it isn't
  associated with any particular field.
  """
  field: String

  """
  The error code, or null if no error code was set.
  """
  code: String
}

type OperationInfo {
  """
  List of messages returned by the operation.
  """
  messages: [OperationMessage!]!
}

union CreateProductPayload = Product | OperationInfo

type Mutation {
  createProduct(name: String!, price: Float!): CreateProductPayload!
}
```

### Querying with Error Handling

Clients can check for errors using GraphQL fragments:

```graphql
mutation CreateProduct($name: String!, $price: Float!) {
  createProduct(name: $name, price: $price) {
    ... on Product {
      id
      name
      price
    }
    ... on OperationInfo {
      messages {
        kind
        message
        field
        code
      }
    }
  }
}
```

## Field-Level Validation Errors

Django's `ValidationError` can include field-specific errors that will be properly mapped:

```python title="mutations.py"
from django.core.exceptions import ValidationError

@strawberry.type
class Mutation:
    @strawberry_django.mutation(handle_django_errors=True)
    def update_user(self, user_id: strawberry.ID, email: str, age: int) -> User:
        user = models.User.objects.get(pk=user_id)

        # Multiple field-specific errors
        errors = {}
        if not email or "@" not in email:
            errors["email"] = "Invalid email address"
        if age < 0 or age > 150:
            errors["age"] = "Age must be between 0 and 150"

        if errors:
            raise ValidationError(errors)

        user.email = email
        user.age = age
        user.save()
        return user
```

Response with field-specific errors:

```json
{
  "data": {
    "updateUser": {
      "messages": [
        {
          "kind": "VALIDATION",
          "message": "Invalid email address",
          "field": "email",
          "code": null
        },
        {
          "kind": "VALIDATION",
          "message": "Age must be between 0 and 150",
          "field": "age",
          "code": null
        }
      ]
    }
  }
}
```

## Global Error Handling Configuration

You can set error handling as the default for all mutations:

```python title="settings.py"
STRAWBERRY_DJANGO = {
    "MUTATIONS_DEFAULT_HANDLE_ERRORS": True,
}
```

With this setting, all mutations will handle Django errors by default unless explicitly turned off:

```python
@strawberry_django.mutation(handle_django_errors=False)
def some_mutation(self, data: str) -> Result:
    # This mutation will NOT handle Django errors automatically
    pass
```

## Custom Error Handling

### Custom Exception Classes

You can create custom exception classes for domain-specific errors:

```python title="exceptions.py"
from django.core.exceptions import ValidationError

class InsufficientStockError(ValidationError):
    """Raised when trying to order more items than available in stock."""
    def __init__(self, product_name: str, requested: int, available: int):
        super().__init__(
            f"Insufficient stock for {product_name}. "
            f"Requested: {requested}, Available: {available}",
            code="insufficient_stock"
        )
```

```python title="mutations.py"
from .exceptions import InsufficientStockError

@strawberry.type
class Mutation:
    @strawberry_django.mutation(handle_django_errors=True)
    def create_order(self, product_id: strawberry.ID, quantity: int) -> Order:
        product = models.Product.objects.get(pk=product_id)

        if product.stock < quantity:
            raise InsufficientStockError(
                product.name,
                quantity,
                product.stock
            )

        # Create order...
        order = models.Order.objects.create(product=product, quantity=quantity)
        product.stock -= quantity
        product.save()

        return order
```

### Manual Error Handling

For cases where you want more control, handle errors manually:

```python title="mutations.py"
from typing import Annotated
from django.core.exceptions import ValidationError

@strawberry.type
class ProductError:
    message: str
    code: str

@strawberry.type
class ProductSuccess:
    product: Product

ProductResult = Annotated[ProductSuccess | ProductError, strawberry.union("ProductResult")]

@strawberry.type
class Mutation:
    @strawberry_django.mutation
    def create_product(self, name: str, price: float) -> ProductResult:
        try:
            if price < 0:
                return ProductError(
                    message="Price must be positive",
                    code="INVALID_PRICE"
                )

            product = models.Product.objects.create(name=name, price=price)
        except Exception as e:
            return ProductError(
                message=str(e),
                code="UNKNOWN_ERROR"
            )

        return ProductSuccess(product=product)
```

## Permission Errors

Permission errors are automatically handled when using the [Permission Extension](./permissions.md):

```python title="types.py"
from strawberry_django.permissions import IsAuthenticated, HasPerm

@strawberry_django.type(models.Document)
class Document:
    title: auto

    @strawberry_django.field(extensions=[IsAuthenticated()])
    def content(self) -> str:
        return self.content

    @strawberry_django.field(extensions=[HasPerm("documents.view_sensitive")])
    def sensitive_data(self) -> str:
        return self.sensitive_data
```

When permission checks fail:

- If the field is optional, it returns `None`
- If the field is a list, it returns an empty list
- If the field is required, it raises a `PermissionDenied` error
- If using `handle_django_errors=True`, it returns an `OperationInfo`

## Model Validation Errors

Django model's `full_clean()` validation is automatically triggered:

```python title="models.py"
from django.db import models
from django.core.exceptions import ValidationError

class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.IntegerField(default=0)

    def clean(self):
        if self.discount_percentage < 0 or self.discount_percentage > 100:
            raise ValidationError({
                'discount_percentage': 'Discount must be between 0 and 100'
            })
        if self.price < 0:
            raise ValidationError({
                'price': 'Price cannot be negative'
            })
```

These validation errors are automatically caught when using CUD mutations:

```python title="mutations.py"
from strawberry_django import mutations

@strawberry.type
class Mutation:
    create_product: Product = mutations.create(
        ProductInput,
        handle_django_errors=True
    )
    update_product: Product = mutations.update(
        ProductPartialInput,
        handle_django_errors=True
    )
```

## Async Error Handling

Error handling works the same way with async resolvers:

```python title="mutations.py"
@strawberry.type
class Mutation:
    @strawberry_django.mutation(handle_django_errors=True)
    async def create_user_async(self, email: str, username: str) -> User:
        # Validation
        if await models.User.objects.filter(email=email).aexists():
            raise ValidationError({
                'email': 'A user with this email already exists'
            })

        # Creation
        user = await models.User.objects.acreate(
            email=email,
            username=username
        )
        return user
```

## Error Handling in Input Mutations

Input mutations also support error handling:

```python title="mutations.py"
@strawberry_django.input(models.Product)
class ProductInput:
    name: auto
    price: auto
    category_id: auto

@strawberry.type
class Mutation:
    @strawberry_django.input_mutation(handle_django_errors=True)
    def create_product(self, info, data: ProductInput) -> Product:
        # The InputMutationExtension will handle converting
        # the input to a proper data argument
        try:
            category = models.Category.objects.get(pk=data.category_id)
        except models.Category.DoesNotExist:
            raise ValidationError({
                'category_id': 'Category does not exist'
            })

        product = models.Product.objects.create(
            name=data.name,
            price=data.price,
            category=category
        )
        return product
```

## Best Practices

### 1. Use handle_django_errors for Standard Operations

For CRUD operations, enable automatic error handling:

```python
@strawberry.type
class Mutation:
    create_user: User = mutations.create(UserInput, handle_django_errors=True)
    update_user: User = mutations.update(UserPartialInput, handle_django_errors=True)
    delete_user: User = mutations.delete(NodeInput, handle_django_errors=True)
```

### 2. Provide Meaningful Error Messages

Always include clear, actionable error messages:

```python
# ❌ Poor error message
if not valid:
    raise ValidationError("Invalid")

# ✅ Good error message
if not is_valid_email(email):
    raise ValidationError({
        'email': 'Please provide a valid email address in the format: user@example.com'
    })
```

### 3. Use Error Codes for Client Handling

Include error codes for programmatic error handling:

```python
raise ValidationError(
    "Product is out of stock",
    code="OUT_OF_STOCK"
)
```

### 4. Validate Early

Validate inputs before performing expensive operations:

```python
@strawberry_django.mutation(handle_django_errors=True)
def bulk_create_users(self, users: list[UserInput]) -> list[User]:
    # Validate all inputs first
    errors = {}
    for i, user_input in enumerate(users):
        if not is_valid_email(user_input.email):
            errors[f"users.{i}.email"] = "Invalid email"

    if errors:
        raise ValidationError(errors)

    # Then perform the bulk operation
    return [
        models.User.objects.create(**user_input)
        for user_input in users
    ]
```

## Troubleshooting

### Error handling not working

Ensure you've enabled error handling:

```python
# In mutation definition
@strawberry_django.mutation(handle_django_errors=True)

# Or globally in settings
STRAWBERRY_DJANGO = {
    "MUTATIONS_DEFAULT_HANDLE_ERRORS": True,
}
```

### Errors not showing field information

Use Django's dict-style ValidationError:

```python
# ❌ Field info not included
raise ValidationError("Invalid email")

# ✅ Field info included
raise ValidationError({'email': 'Invalid email'})
```

### Custom exceptions not handled

Only Django's built-in exceptions are automatically handled. For custom exceptions, either:

1. Inherit from Django's exception classes
2. Catch and re-raise as Django exceptions
3. Use manual error handling with custom union types

## See Also

- [Mutations](./mutations.md) - Creating and updating data
- [Permissions](./permissions.md) - Authorization and access control
- [Validation](#) - Input validation patterns (coming soon)
