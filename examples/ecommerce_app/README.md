# E-commerce Example

An example GraphQL API demonstrating Strawberry Django features and best practices through an e-commerce use case with users, products, shopping cart, and orders.

## What This Example Demonstrates

This example showcases:

- **Modular Django app structure** - Organized code across user, product, and order apps
- **Multiple query patterns** - Single nodes, paginated lists, and Relay connections
- **Filtering and ordering** - Type-safe filtering and ordering on queries
- **Authentication & permissions** - Login/logout with permission checks using extensions
- **Custom mutations** - Shopping cart operations and checkout flow
- **Query optimization** - Using `@model_property` to work with the DjangoOptimizerExtension
- **Custom context** - Type-safe context with user helpers and dataloaders
- **Relay interface** - Node interface implementation for global IDs
- **Session handling** - Session-based cart before authentication

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
   - Admin user (username: `admin`, password: `admin`)
   - Test user (username: `testuser`, password: `test123`)
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
    username
    name
    email
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
    status
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
      username
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
def my_field(self, info: Info) -> SomeType:
    user = info.context.get_user(required=True)  # Type-safe!
    # Note: This is an illustrative example - dataloaders are not yet implemented in this demo
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

## Admin Interface

Access the Django admin at http://localhost:8000/admin/

Default credentials:
- **Username:** admin
- **Password:** admin

## Debug Toolbar

When running in debug mode, the Django Debug Toolbar is available to inspect queries and performance. Look for the toolbar on the right side when accessing the GraphQL endpoint through a browser.
