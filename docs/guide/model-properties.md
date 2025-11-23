---
title: Model Properties
---

# Model Properties

Model properties allow you to add computed fields directly to your Django models while providing optimization hints for the GraphQL query optimizer. This feature is particularly useful when you want to expose derived data in your GraphQL schema without triggering N+1 queries or deferred attribute issues.

## Overview

Strawberry Django provides two decorators for adding model properties:

- `@model_property`: Similar to Python's `@property` but with optimization hints
- `@cached_model_property`: Similar to Django's `@cached_property` but with optimization hints

Both decorators accept the same optimization parameters as `strawberry_django.field()`, allowing the optimizer to properly prefetch or select related data.

## Basic Usage

### Basic Model Property

```python title="models.py"
from decimal import Decimal
from django.db import models
from strawberry_django.descriptors import model_property

class OrderItem(models.Model):
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()

    @model_property(only=["price", "quantity"])
    def total(self) -> Decimal:
        """Calculate the total price for this order item."""
        return self.price * self.quantity
```

```python title="types.py"
import strawberry_django
from strawberry import auto

@strawberry_django.type(models.OrderItem)
class OrderItem:
    price: auto
    quantity: auto
    total: auto  # Automatically resolved with optimization hints
```

The `only` parameter tells the optimizer to ensure `price` and `quantity` are fetched from the database when `total` is requested.

### Cached Model Property

For expensive computations that should only be calculated once per instance, use `@cached_model_property`:

```python title="models.py"
from django.db import models
from strawberry_django.descriptors import cached_model_property

class Product(models.Model):
    name = models.CharField(max_length=100)

    @cached_model_property(
        prefetch_related=["reviews"]
    )
    def average_rating(self) -> float:
        """Calculate average rating from all reviews."""
        reviews = list(self.reviews.all())
        if not reviews:
            return 0.0
        return sum(r.rating for r in reviews) / len(reviews)
```

The computed value is cached on the instance after the first access, avoiding redundant calculations.

## Optimization Parameters

Model properties support the same optimization hints as `strawberry_django.field()`: `only`, `select_related`, and `prefetch_related`. See the [Query Optimizer guide](./optimizer.md) for detailed information on these parameters.

You can also use a lambda for more complex prefetch scenarios:

```python title="models.py"
from django.db.models import Prefetch

class Author(models.Model):
    name = models.CharField(max_length=100)

    @model_property(
        prefetch_related=[
            lambda info: Prefetch(
                "books",
                queryset=Book.objects.filter(published=True)
            )
        ]
    )
    def published_book_count(self) -> int:
        return len(self.books.all())
```

### `annotate`

Add database annotations for complex calculations:

```python title="models.py"
from django.db.models import Count

class Category(models.Model):
    name = models.CharField(max_length=100)

    @model_property(
        annotate={
            "_product_count": Count("products")
        }
    )
    def product_count(self) -> int:
        """Get the count of products in this category."""
        return self._product_count  # type: ignore
```

You can also use lambdas for dynamic annotations:

```python title="models.py"
from django.db.models import Avg

class Product(models.Model):
    name = models.CharField(max_length=100)

    @model_property(
        annotate={
            "_avg_rating": lambda info: Avg("reviews__rating")
        }
    )
    def average_rating(self) -> float:
        return self._avg_rating or 0.0  # type: ignore
```

## Combining with GraphQL Types

Model properties integrate seamlessly with `strawberry.auto`:

```python title="models.py"
from decimal import Decimal
from django.db import models
from django.db.models import Sum
from strawberry_django.descriptors import model_property, cached_model_property

class Order(models.Model):
    customer = models.ForeignKey("Customer", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20)

    @model_property(
        prefetch_related=["items"],
        annotate={"_total": Sum("items__total")}
    )
    def total_amount(self) -> Decimal:
        """Calculate total order amount."""
        return self._total or Decimal(0)  # type: ignore

    @cached_model_property(select_related=["customer"])
    def customer_name(self) -> str:
        """Get the customer's full name."""
        return f"{self.customer.first_name} {self.customer.last_name}"
```

```python title="types.py"
import strawberry_django
from strawberry import auto

@strawberry_django.type(models.Order)
class Order:
    created_at: auto
    status: auto
    total_amount: auto      # Uses model_property optimization hints
    customer_name: auto     # Uses cached_model_property hints
```

## Common Patterns

### Conditional Logic with Info Context

For properties that need request context, you can combine model properties with field resolvers:

```python title="types.py"
import strawberry_django
from strawberry import auto
from strawberry.types import Info

@strawberry_django.type(models.Product)
class Product:
    name: auto
    price: auto

    @strawberry_django.field(only=["price"])
    def discounted_price(self, info: Info) -> Decimal:
        """Apply user-specific discount."""
        user = info.context.request.user
        discount = user.discount_rate if user.is_authenticated else 0
        return self.price * (1 - discount)
```

### Combining Multiple Optimization Hints

```python title="models.py"
from django.db.models import Count, Avg, Q

class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey("Category", on_delete=models.CASCADE)

    @model_property(
        select_related=["category"],
        prefetch_related=["reviews"],
        annotate={
            "_review_count": Count("reviews"),
            "_avg_rating": Avg("reviews__rating"),
        },
        only=["name", "category__name"]
    )
    def summary(self) -> str:
        """Generate a product summary with category and ratings."""
        reviews = self._review_count  # type: ignore
        rating = self._avg_rating or 0.0  # type: ignore
        return f"{self.name} ({self.category.name}) - {rating:.1f}★ ({reviews} reviews)"
```

## Best Practices

1. **Always provide optimization hints**: If your property accesses model fields or relations, specify them in the decorator parameters.

2. **Use cached_model_property for expensive operations**: If the calculation is expensive and doesn't depend on mutable data, use caching.

3. **Keep properties focused**: Complex business logic should be in separate service classes, not in model properties.

4. **Type annotations are required**: Always provide return type annotations for model properties.

5. **Document your properties**: Add clear docstrings that will appear in your GraphQL schema.

6. **Test with the optimizer**: Ensure your optimization hints actually work by checking the generated SQL queries.

7. **Use `len()` instead of `.count()` with prefetch_related**: When accessing prefetched relationships, use `len()` to avoid bypassing the prefetch cache:

```python
# ❌ Bad: .count() bypasses prefetch cache and hits database
@model_property(prefetch_related=["books"])
def book_count(self) -> int:
    return self.books.count()  # Issues a COUNT(*) query!

# ✅ Good: len() uses prefetch cache
@model_property(prefetch_related=["books"])
def book_count(self) -> int:
    return len(self.books.all())  # Uses prefetched data

# ✅ Best: Use database annotation when prefetch not needed
@model_property(annotate={"_book_count": Count("books")})
def book_count(self) -> int:
    return self._book_count  # type: ignore
```

## Troubleshooting

### Property triggers extra queries

If your model property is still causing N+1 queries:

1. Check that optimization hints match the actual database access
2. Ensure the [Query Optimizer Extension](./optimizer.md) is enabled
3. Verify that `only` includes all accessed fields
4. Use `select_related` for foreign keys, not `prefetch_related`

### Type resolution errors

If Strawberry can't resolve the type:

```python
# ❌ Missing return type annotation
@model_property(only=["name"])
def display_name(self):
    return self.name.upper()

# ✅ With return type annotation
@model_property(only=["name"])
def display_name(self) -> str:
    return self.name.upper()
```

## See Also

- [Query Optimizer](./optimizer.md) - Understanding optimization hints
- [Custom Resolvers](./resolvers.md) - Alternative approaches for computed fields
- [Fields](./fields.md) - Basic field definition and customization
