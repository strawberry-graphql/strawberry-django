# E-commerce Example

A complete e-commerce GraphQL API built with Strawberry Django, demonstrating modern best practices including authentication, shopping cart, order management, and query optimization.

## Features

### User Management
- Custom user model with email addresses and profile information
- Login/logout mutations
- Current user query (`me`)
- User filtering and ordering

### Product Catalog
- Products with brands and multiple images
- Enum types for product categories (physical/virtual)
- Advanced filtering by name, kind, and brand
- Ordering support
- Multiple query patterns (single node, paginated list, relay connections)

### Shopping Cart & Orders
- Session-based shopping cart (no login required)
- Add, update, and remove items
- Cart checkout flow (requires authentication)
- Order history per user
- Staff-only access to all orders

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

### Query Products with Filtering

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
  myOrdersConn(first: 10) {
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

## Key Concepts

### Modular App Structure

The example is organized into Django apps (user, product, order) with each having:
- `models.py` - Django ORM models
- `types.py` - Strawberry GraphQL types with filters/ordering
- `schema.py` - Queries and mutations

All schemas are merged in the root `schema.py`.

### Custom Context

The example includes a custom context class with helper methods:

```python
@strawberry_django.field
def my_field(self, info: Info) -> SomeType:
    # Get user or None if not authenticated
    user = info.context.get_user()

    # Get user or raise PermissionDenied
    user = info.context.get_user(required=True)

    # Access dataloaders
    brand = await info.context.dataloaders.brand_loader.load(brand_id)
```

### Permission Extensions

Using Strawberry Django's permission extensions:

```python
# Only authenticated users can access
@strawberry_django.connection(extensions=[IsAuthenticated()])
def my_orders(self, info: Info) -> Iterable[Order]:
    ...

# Only staff users can access
orders_conn: DjangoListConnection[OrderType] = strawberry_django.connection(
    extensions=[IsStaff()]
)
```

### Query Optimization

The example uses `@model_property` for computed fields that work with the query optimizer:

```python
@model_property(only=["quantity", "price"])
def total(self) -> decimal.Decimal:
    return self.quantity * self.price
```

This tells the optimizer to only fetch the specified fields, preventing unnecessary database queries.

### Filtering and Ordering

Using the modern Strawberry Django filter/order APIs:

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

## Admin Interface

Access the Django admin at http://localhost:8000/admin/

Default credentials:
- **Username:** admin
- **Password:** admin

## Debug Toolbar

When running in debug mode, the Django Debug Toolbar is available to inspect queries and performance. Look for the toolbar on the right side of the page when accessing the GraphQL endpoint through a browser.

## Technologies Used

- **Django 5.0+** - Web framework
- **Strawberry GraphQL** - GraphQL library for Python
- **Strawberry Django** - Django integration for Strawberry
- **django-choices-field** - Better enum field support
- **Pillow** - Image handling for product images
