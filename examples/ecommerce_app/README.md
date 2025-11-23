# E-commerce Example

A comprehensive GraphQL API example demonstrating **Strawberry Django** features and best practices through a realistic e-commerce application with users, products, shopping carts, and orders.

## 🎯 Learning Objectives

This example is designed to help you learn Strawberry Django by demonstrating real-world patterns you'll use in production applications. After exploring this example, you'll understand:

### Core Concepts
- **Modular Django app structure** - How to organize GraphQL schemas across multiple Django apps
- **Type-safe GraphQL** - Using Python type hints for automatic schema generation
- **Relay Node interface** - Implementing global object identification
- **Multiple query patterns** - Single nodes, offset pagination, and cursor-based Relay connections

### Optimization & Performance
- **Query optimization** - Using `@model_property` with optimization hints to prevent N+1 queries
- **DataLoaders** - Batching and caching database queries (see `app/base/dataloaders.py`)
- **Prefetching strategies** - Efficient loading of related data

### Security & Authentication
- **Authentication** - Session-based login/logout
- **Permissions** - Using permission extensions (`IsAuthenticated`, `IsStaff`)
- **Field-level security** - Controlling access to specific fields

### Advanced Features
- **Custom context** - Type-safe context with helper methods and dataloaders
- **Error handling** - Automatic Django error conversion with `handle_django_errors`
- **Transaction handling** - Using `@transaction.atomic` for data consistency
- **Session management** - Anonymous cart with session storage
- **Computed fields** - Business logic in model properties and resolvers
- **Type enums** - Exposing Django TextChoices to GraphQL

## Setup

1. **Install dependencies:**
   ```shell
   poetry install
   ```

2. **Run migrations:**
   ```shell
   poetry run python manage.py migrate
   ```

3. **Populate sample data:**
   ```shell
   poetry run python manage.py populate_db
   ```

   This creates:
   - Admin user (username: `admin`, password: `admin`) <!-- test password only -->
   - Test user (username: `testuser`, password: `test123`) <!-- test password only -->
   - Sample brands and products

4. **Run the server:**
   ```shell
   poetry run python manage.py runserver
   ```

5. **Open GraphiQL:**
   Navigate to http://localhost:8000/graphql/

## Example Queries

### Login

```graphql
mutation {
  login(username: "testuser", password: "test123") {
    id
    name
    emails {
      email
      isPrimary
    }
  }
}
```

### Query Products with Filtering and Ordering

```graphql
query {
  products(
    filters: { name: { iContains: "pro" } }
    order: { name: ASC }
    pagination: { limit: 10 }
  ) {
    id
    name
    brand {
      name
    }
    price
    formattedPrice
    kind
  }
}
```

### Advanced Filtering - Nested Filters

```graphql
query {
  products(
    filters: {
      brand: { name: { iContains: "apple" } }
      kind: { exact: PHYSICAL }
    }
    pagination: { limit: 5 }
  ) {
    id
    name
    brand {
      name
    }
    kind
  }
}
```

### Products with Relay Connection

```graphql
query {
  productsConn(first: 10) {
    edges {
      node {
        id
        name
        price
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
```

### Add to Cart

```graphql
mutation {
  cartAddItem(
    product: { id: "UHJvZHVjdFR5cGU6MQ==" }
    quantity: 2
  ) {
    id
    product {
      name
      price
    }
    quantity
    total
  }
}
```

### View Cart

```graphql
query {
  myCart {
    items {
      product {
        name
      }
      quantity
      total
    }
    total
  }
}
```

### Checkout Cart

Must be logged in to checkout.

```graphql
mutation {
  cartCheckout {
    id
    user {
      name
    }
    items {
      product {
        name
      }
      quantity
      price
      total
    }
    total
  }
}
```

### View My Orders

```graphql
query {
  myOrders(first: 10) {
    edges {
      node {
        id
        total
        items {
          product {
            name
          }
          quantity
          price
        }
      }
    }
  }
}
```

## Project Structure

```
app/
├── base/              # Shared types and utilities
│   ├── types.py       # Context and Info type definitions
│   └── dataloaders.py # DataLoader implementations
├── user/              # User management app
│   ├── models.py      # User and Email models
│   ├── types.py       # GraphQL types and filters
│   └── schema.py      # Queries and mutations
├── product/           # Product catalog app
│   ├── models.py      # Product, Brand, ProductImage models
│   ├── types.py       # GraphQL types and filters
│   └── schema.py      # Queries and mutations
├── order/             # Shopping and orders app
│   ├── models.py      # Cart, CartItem, Order, OrderItem models
│   ├── types.py       # GraphQL types
│   └── schema.py      # Queries and mutations
├── management/
│   └── commands/
│       └── populate_db.py  # Sample data generator
├── schema.py          # Root schema merging all apps
├── views.py           # Custom async GraphQL view
├── urls.py            # URL configuration
└── settings.py        # Django settings
```

## Key Patterns & Best Practices

### 1. Modular Schema Organization

Each Django app has its own GraphQL schema that gets merged into the root schema:

```python
# app/schema.py
from strawberry.tools import merge_types

Query = merge_types("Query", (UserQuery, ProductQuery, OrderQuery))
Mutation = merge_types("Mutation", (UserMutation, ProductMutation, OrderMutation))

schema = strawberry.Schema(query=Query, mutation=Mutation)
```

### 2. Custom Context with Type Safety

Define a custom context class for type-safe access to request data:

```python
# app/base/types.py
@dataclasses.dataclass
class Context(StrawberryDjangoContext):
    dataloaders: DataLoaders

    def get_user(self, *, required: Literal[True] | None = None) -> User | None:
        # Implementation with proper typing
        ...

Info = info.Info["Context", None]
```

Usage in resolvers:

```python
@strawberry_django.field
async def my_field(self, info: Info, brand_id: int) -> SomeType:
    user = info.context.get_user(required=True)  # Type-safe!
    # Use dataloaders to efficiently batch queries
    brand = await info.context.dataloaders.brand_loader.load(brand_id)
```

### 3. Permission Extensions

Use permission extensions instead of manual checks in resolvers:

```python
# Only authenticated users
@strawberry_django.connection(extensions=[IsAuthenticated()])
def my_orders(self, info: Info) -> Iterable[Order]:
    ...

# Only staff users
orders_conn: DjangoListConnection[OrderType] = strawberry_django.connection(
    extensions=[IsStaff()]
)
```

### 4. Query Optimization with @model_property

Use `@model_property` for computed fields to enable query optimization:

```python
from strawberry_django.descriptors import model_property

class OrderItem(models.Model):
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=24, decimal_places=2)

    @model_property(only=["quantity", "price"])
    def total(self) -> decimal.Decimal:
        return self.quantity * self.price
```

This tells the optimizer exactly which fields to fetch, preventing unnecessary database queries.

### 5. Modern Filter and Order Types

Use the current Strawberry Django APIs for filters and ordering:

```python
@strawberry_django.filter_type(User)
class UserFilter:
    username: auto
    email: auto

@strawberry_django.order_type(User)
class UserOrder:
    username: auto
    email: auto
```

Apply them to fields:

```python
users: list[UserType] = strawberry_django.field(
    filters=UserFilter,
    order=UserOrder,
    pagination=True,
)
```

### 6. Multiple Query Patterns

Provide different ways to query data based on use case:

```python
# Single node by ID
product: ProductType = strawberry_django.node()

# Paginated list with offset pagination
products: list[ProductType] = strawberry_django.field(pagination=True)

# Relay connection with cursor pagination
products_conn: DjangoListConnection[ProductType] = strawberry_django.connection()
```

### 7. Mutation Error Handling

Use `handle_django_errors=True` to automatically handle Django validation errors:

```python
@strawberry_django.mutation(handle_django_errors=True)
@transaction.atomic
def cart_add_item(
    self,
    info: Info,
    product: strawberry_django.NodeInput,
    quantity: int = 1,
) -> CartItemType:
    if quantity <= 0:
        raise ValidationError({"quantity": _("Quantity must be at least 1")})
    # ...
```

### 8. Using Relay Node Interface

Implement the Node interface for global object identification:

```python
@strawberry_django.type(Product)
class ProductType(relay.Node):
    # Fields are automatically exposed
    pass
```

This enables queries like:

```graphql
query {
  product(id: "UHJvZHVjdFR5cGU6MQ==") {
    name
    price
  }
}
```

### 9. Understanding the Query Optimizer

The DjangoOptimizerExtension automatically optimizes queries based on your GraphQL selection:

```graphql
# This query
query {
  products(pagination: { limit: 10 }) {
    name
    brand {
      name
    }
    formattedPrice
  }
}

# Automatically generates optimal SQL with:
# - SELECT only needed fields (name, price for formattedPrice, brand_id)
# - JOIN brand table (select_related)
# - No N+1 queries
```

The optimizer works because:
- `@model_property` decorators specify field dependencies
- `@strawberry_django.field` with `only`, `select_related`, `prefetch_related`
- Automatic analysis of field requirements

## Testing

Example tests are provided in the `tests/` directory showing how to test Strawberry Django applications:

```bash
# Run tests with pytest
poetry run pytest tests/

# Run with coverage
poetry run pytest --cov=app tests/
```

The tests demonstrate:
- Testing queries and mutations
- Handling authentication in tests
- Using fixtures for test data
- Testing with GraphQL test client

## Admin Interface

Access the Django admin at http://localhost:8000/admin/

Default credentials:
- **Username:** admin
- **Password:** admin

## Debug Toolbar

When running in debug mode, the Django Debug Toolbar is available to inspect queries and performance. Look for the toolbar on the right side when accessing the GraphQL endpoint through a browser.

## Learning Path

If you're new to Strawberry Django, we recommend exploring the example in this order:

1. **Start with models** (`app/user/models.py`, `app/product/models.py`) - See how Django models are defined with type hints and `@model_property`
2. **Explore types** (`app/user/types.py`, `app/product/types.py`) - Learn how models are exposed as GraphQL types
3. **Study schemas** (`app/user/schema.py`, `app/order/schema.py`) - Understand queries, mutations, and permissions
4. **Check context** (`app/base/types.py`, `app/base/dataloaders.py`) - See how context and dataloaders work
5. **Review root schema** (`app/schema.py`) - Learn how to merge schemas from multiple apps
6. **Try queries** - Use GraphiQL to experiment with the example queries in this README
7. **Read tests** (`tests/`) - See how to test your GraphQL API

## Common Patterns Reference

### Adding a New Model

1. Create the Django model with type hints
2. Add `@model_property` for computed fields
3. Create a GraphQL type with `@strawberry_django.type`
4. Add queries/mutations in schema.py
5. Merge into root schema

### Adding Permissions

```python
# Query-level permission
@strawberry_django.field(extensions=[IsAuthenticated()])
def my_data(self, info: Info) -> list[MyType]:
    ...

# Field-level permission
@strawberry_django.field(extensions=[IsStaff()])
def sensitive_field(self, root: MyModel) -> str:
    return root.secret_data
```

### Optimizing Queries

```python
# For model properties
@model_property(
    only=["field1", "field2"],  # SELECT these fields
    select_related=["fk_relation"],  # JOIN these FKs
    prefetch_related=["m2m_relation"],  # Prefetch these M2M/reverse FKs
)
def computed_value(self) -> int:
    ...

# For custom resolvers
@strawberry_django.field(
    only=["name"],
    select_related=["brand"],
)
def custom_resolver(self, root: Product) -> str:
    return f"{root.brand.name}: {root.name}"
```

## Common Pitfalls and Solutions

### ❌ Forgetting to specify optimization hints

```python
# BAD - Will cause N+1 queries
@model_property
def full_name(self) -> str:
    return f"{self.first_name} {self.last_name}"  # Deferred attribute error!
```

```python
# GOOD - Specifies required fields
@model_property(only=["first_name", "last_name"])
def full_name(self) -> str:
    return f"{self.first_name} {self.last_name}"
```

### ❌ Not using transactions for multi-step operations

```python
# BAD - No atomicity
def checkout(self, user):
    order = Order.objects.create(user=user, cart=self)
    for item in self.items.all():
        order.items.create(...)  # If this fails, order still exists!
```

```python
# GOOD - Atomic operation
@transaction.atomic
def checkout(self, user):
    order = Order.objects.create(user=user, cart=self)
    for item in self.items.all():
        order.items.create(...)  # All-or-nothing
```

### ❌ Capturing variables by reference in lambdas

```python
# BAD - cart.pk might change before callback runs
transaction.on_commit(
    lambda: info.context.request.session.update({"cart_pk": cart.pk})
)
```

```python
# GOOD - Capture by value with default argument
transaction.on_commit(
    lambda pk=cart.pk: info.context.request.session.update({"cart_pk": pk})
)
```

### ❌ Not handling async contexts properly

```python
# BAD - Sync code in async resolver
async def my_resolver(self, info: Info):
    user = info.context.request.user  # Might cause SynchronousOnlyOperation
```

```python
# GOOD - Use async helpers
async def my_resolver(self, info: Info):
    user = await info.context.aget_user()  # Properly wrapped
```

## Additional Resources

- [Strawberry Django Documentation](https://strawberry.rocks/docs/django)
- [Strawberry GraphQL Documentation](https://strawberry.rocks/)
- [Django Documentation](https://docs.djangoproject.com/)
- [GraphQL Specification](https://spec.graphql.org/)

## Need Help?

- Check the [Strawberry Django FAQ](https://strawberry.rocks/docs/django/faq)
- Visit the [GitHub Discussions](https://github.com/strawberry-graphql/strawberry-django/discussions)
- Join the [Discord Community](https://discord.gg/ZkRTEJQ)
