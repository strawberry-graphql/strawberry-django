# Strawberry Django Example

This is a comprehensive example demonstrating modern best practices for building a GraphQL API with Strawberry Django. It showcases:

- **Modular app structure** - Organized into user, product, and order apps
- **Relay-style GraphQL** - Using Node interface and connections
- **Authentication & permissions** - Login/logout mutations with permission checks
- **Filtering & ordering** - Type-safe filtering and ordering on queries
- **Pagination** - Both offset and cursor-based pagination
- **Shopping cart** - Complete e-commerce cart and checkout flow
- **Query optimization** - Using DjangoOptimizerExtension to prevent N+1 queries
- **Custom context** - Type-safe context with user helpers and dataloaders

## Features Demonstrated

### User Management
- Custom user model with avatar and age calculation
- Login/logout mutations
- Current user query (`me`)
- Field deprecation example

### Product Catalog
- Products with brands and images
- Enum types for product kinds
- Multiple query types (single, list, connection)
- Filtering by name, kind, and brand
- Ordering support

### Shopping Cart & Orders
- Session-based shopping cart
- Add/update/remove cart items
- Cart checkout flow
- Order history with user filtering
- Staff-only order queries

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

4. **Run the server:**
   ```shell
   poetry run python manage.py runserver
   ```

5. **Open GraphiQL:**
   Navigate to http://localhost:8000/graphql/

## Usage

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

### Query Products

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

### Add to Cart

```graphql
mutation {
  cartAddItem(product: { id: "UHJvZHVjdFR5cGU6MQ==" }, quantity: 2) {
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

### Checkout

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
    }
    total
  }
}
```

## Project Structure

```
app/
├── base/              # Shared types and utilities
│   ├── types.py       # Context and Info type definitions
│   └── dataloaders.py # DataLoader implementations
├── user/              # User management
│   ├── models.py      # User and Email models
│   ├── types.py       # GraphQL types and filters
│   └── schema.py      # Queries and mutations
├── product/           # Product catalog
│   ├── models.py      # Product, Brand, ProductImage models
│   ├── types.py       # GraphQL types and filters
│   └── schema.py      # Queries and mutations
├── order/             # Shopping and orders
│   ├── models.py      # Cart, Order models
│   ├── types.py       # GraphQL types
│   └── schema.py      # Queries and mutations
├── management/
│   └── commands/
│       └── populate_db.py  # Sample data generator
├── schema.py          # Root schema merging all apps
├── views.py           # Custom GraphQL view
├── urls.py            # URL configuration
└── settings.py        # Django settings
```

## Key Patterns

### Using Modern APIs

This example uses the current non-deprecated Strawberry Django APIs:

- `@strawberry_django.type()` for GraphQL types
- `@strawberry_django.filter_type()` for filters (not `.filters.filter()`)
- `@strawberry_django.order_type()` for ordering (not `.ordering.order()`)
- `strawberry_django.relay.DjangoListConnection` (not `ListConnectionWithTotalCount`)
- `@strawberry_django.field()` for custom resolvers
- `@strawberry_django.mutation()` for mutations

### Type-Safe Context

The example includes a custom context with type-safe user access:

```python
@strawberry_django.field
def my_field(self, info: Info) -> SomeType:
    user = info.context.get_user(required=True)  # Type-safe!
    # ...
```

### Model Properties with Optimization

Using `@model_property` decorator for computed fields that work with the optimizer:

```python
@model_property(only=["quantity", "price"])
def total(self) -> decimal.Decimal:
    return self.quantity * self.price
```

## Admin Access

- **URL:** http://localhost:8000/admin/
- **Username:** admin
- **Password:** admin

## Debug Toolbar

When `DEBUG=True`, the Django Debug Toolbar is available at:
http://localhost:8000/__debug__/

This shows all queries executed, useful for optimizing performance.
