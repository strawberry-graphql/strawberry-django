---
title: Authentication
---

# Authentication

`strawberry_django` provides built-in mutations and queries for session-based authentication with Django's authentication system.

> [!WARNING]
> This solution is designed for web browsers that support cookies. It will not work for clients that can't store cookies (e.g., mobile apps). For those scenarios, use token-based authentication methods like JWT with [strawberry-django-auth](https://github.com/nrbnlulu/strawberry-django-auth).

## Quick Start

### Define Types

```python title="types.py"
import strawberry_django
from strawberry import auto
from django.contrib.auth import get_user_model

@strawberry_django.type(get_user_model())
class User:
    username: auto
    email: auto

@strawberry_django.input(get_user_model())
class UserInput:
    username: auto
    password: auto
    email: auto  # Optional: add other fields as needed
```

### Define Schema

```python title="schema.py"
import strawberry
import strawberry_django
from .types import User, UserInput

@strawberry.type
class Query:
    me: User = strawberry_django.auth.current_user()

@strawberry.type
class Mutation:
    login: User = strawberry_django.auth.login()
    logout = strawberry_django.auth.logout()
    register: User = strawberry_django.auth.register(UserInput)
```

## Available Functions

### `current_user()`

A field that returns the currently authenticated user.

```python
me: User = strawberry_django.auth.current_user()
```

**Behavior:**

- Returns the authenticated user object
- Raises `ValidationError("User is not logged in.")` if the user is not authenticated

**GraphQL Usage:**

```graphql
query {
  me {
    username
    email
  }
}
```

### `login()`

A mutation that authenticates a user with username and password.

```python
login: User = strawberry_django.auth.login()
```

**Arguments (automatically generated):**

- `username: String!` - The username
- `password: String!` - The password

**Behavior:**

- Uses Django's `authenticate()` to verify credentials
- Creates a session using Django's `login()`
- Supports both WSGI and ASGI (including Django Channels)
- Returns the authenticated user on success
- Raises `ValidationError("Incorrect username/password")` on failure

**GraphQL Usage:**

```graphql
mutation {
  login(username: "myuser", password: "mypassword") {
    username
    email
  }
}
```

### `logout()`

A mutation that logs out the current user.

```python
logout = strawberry_django.auth.logout()
```

**Behavior:**

- Ends the current session using Django's `logout()`
- Supports both WSGI and ASGI (including Django Channels)
- Returns `true` if a user was logged out, `false` if no user was logged in

**GraphQL Usage:**

```graphql
mutation {
  logout
}
```

### `register(input_type)`

A mutation that creates a new user account.

```python
register: User = strawberry_django.auth.register(UserInput)
```

**Arguments:**

- `input_type` - A strawberry_django input type for user creation

**Behavior:**

- Validates the password using Django's `validate_password()` (checks against `AUTH_PASSWORD_VALIDATORS`)
- Creates the user with a properly hashed password using `set_password()`
- Returns the created user object
- Raises validation errors if password doesn't meet requirements

**GraphQL Usage:**

```graphql
mutation {
  register(
    data: {
      username: "newuser"
      password: "securepassword123"
      email: "user@example.com"
    }
  ) {
    username
    email
  }
}
```

## Password Validation

The `register` mutation automatically validates passwords against Django's `AUTH_PASSWORD_VALIDATORS`. Configure validators in your settings:

```python title="settings.py"
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
```

## Using with Custom User Models

The auth functions work with custom user models. Ensure your type and input reference the correct model:

```python title="types.py"
from django.contrib.auth import get_user_model

@strawberry_django.type(get_user_model())
class User:
    # Your custom user fields
    username: auto
    email: auto
    first_name: auto
    last_name: auto
```

## Optional User Return Type

You can make login return `None` on failure instead of raising an error:

```python
@strawberry.type
class Mutation:
    login: User | None = strawberry_django.auth.login()
```

This way, unsuccessful logins return `null` instead of a GraphQL error.

## Accessing User in Resolvers

You can access the current user in any resolver:

```python
from strawberry.types import Info

@strawberry.type
class Query:
    @strawberry.field
    def my_data(self, info: Info) -> str:
        user = info.context.request.user
        if not user.is_authenticated:
            raise PermissionError("Not authenticated")
        return f"Hello, {user.username}!"
```

Or use the utility function:

```python
from strawberry_django.auth.utils import get_current_user

@strawberry.field
def my_data(self, info: Info) -> str:
    user = get_current_user(info)
    # ...
```

## Django Channels Support

The login and logout mutations automatically detect Django Channels and use the appropriate authentication methods:

- For standard WSGI/ASGI: Uses `django.contrib.auth.login/logout`
- For Channels WebSocket: Uses `channels.auth.login/logout`

This allows authentication to work seamlessly with [subscriptions](./subscriptions.md).

## Session Configuration

Ensure your Django session settings are properly configured:

```python title="settings.py"
# Required middleware
MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # ...
]

# Session settings
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # Or cache, file, etc.
SESSION_COOKIE_SECURE = True  # For HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'  # Or 'Strict' for more security
```

## Error Handling

Authentication errors are raised as `ValidationError`:

```python
from django.core.exceptions import ValidationError

# Login failure
ValidationError("Incorrect username/password")

# Not logged in (current_user)
ValidationError("User is not logged in.")

# Password validation failure (register)
ValidationError("This password is too short...")
```

You can catch these in your frontend or use [error handling extensions](./error-handling.md).

## See Also

- [Permissions](./permissions.md) - Protecting fields and operations
- [Django Channels](../integrations/channels.md) - WebSocket authentication setup
- [strawberry-django-auth](https://github.com/nrbnlulu/strawberry-django-auth) - JWT authentication
