---
title: Django Channels
---

# Django Channels

Strawberry provides an integration with
[django-channels](https://channels.readthedocs.io/en/stable/) to enable
[subscriptions](../guide/subscriptions.md) and WebSocket support with Django.

## Overview

Django doesn't support WebSockets out of the box. Django Channels extends Django to handle WebSockets and other asynchronous protocols. Strawberry's Channels integration allows you to:

- Use GraphQL subscriptions
- Handle GraphQL over WebSocket connections
- Mix regular Django HTTP requests with GraphQL

## Installation

Install the required packages:

```bash
pip install channels daphne
```

For production deployments, you may also need a channel layer backend:

```bash
pip install channels-redis  # For Redis-backed channel layers
```

## Configuration

### 1. Update INSTALLED_APPS

Add `daphne` and `channels` to your `INSTALLED_APPS` in `settings.py`:

```python title="settings.py"
INSTALLED_APPS = [
    'daphne',  # Must be before staticfiles for runserver override
    'django.contrib.staticfiles',
    # ... other apps
    'channels',
    'strawberry_django',
]
```

### 2. Configure ASGI Application

Set the ASGI application path:

```python title="settings.py"
ASGI_APPLICATION = 'myproject.asgi.application'
```

### 3. Set Up ASGI Routing

Create or update your `asgi.py` file:

```python title="myproject/asgi.py"
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")

# Initialize Django ASGI application early to ensure AppRegistry is populated
# before importing any models
django_asgi_app = get_asgi_application()

# Import schema AFTER django setup
from myproject.schema import schema
from strawberry_django.routers import AuthGraphQLProtocolTypeRouter

application = AuthGraphQLProtocolTypeRouter(
    schema,
    django_application=django_asgi_app,
)
```

## AuthGraphQLProtocolTypeRouter

`strawberry_django` provides `AuthGraphQLProtocolTypeRouter`, a convenience class that sets up GraphQL on both HTTP and WebSocket with authentication support.

```python
from strawberry_django.routers import AuthGraphQLProtocolTypeRouter

application = AuthGraphQLProtocolTypeRouter(
    schema,                           # Your Strawberry schema
    django_application=django_asgi,   # Optional: Django ASGI app for non-GraphQL routes
    url_pattern="^graphql",           # Optional: URL pattern (default: "^graphql")
)
```

### What it provides

- **AuthMiddlewareStack**: Automatically populates `request.user` for authenticated sessions
- **AllowedHostsOriginValidator**: WebSocket security based on `ALLOWED_HOSTS`
- **Dual protocol routing**: Routes both HTTP and WebSocket to GraphQL

### Custom URL Pattern

```python
# Route GraphQL to /api/graphql instead of /graphql
application = AuthGraphQLProtocolTypeRouter(
    schema,
    django_application=django_asgi_app,
    url_pattern="^api/graphql",
)
```

## Difference from Strawberry's GraphQLProtocolTypeRouter

Strawberry core provides `GraphQLProtocolTypeRouter`, but `strawberry_django` provides `AuthGraphQLProtocolTypeRouter` with these enhancements:

| Feature                  | GraphQLProtocolTypeRouter | AuthGraphQLProtocolTypeRouter     |
| ------------------------ | ------------------------- | --------------------------------- |
| Auth middleware          | No                        | Yes (AuthMiddlewareStack)         |
| Host validation          | No                        | Yes (AllowedHostsOriginValidator) |
| `request.user` available | No                        | Yes                               |

Use `AuthGraphQLProtocolTypeRouter` when you need:

- User authentication in resolvers
- Permission checks
- Session-based authentication

## Channel Layers

For subscriptions that need to broadcast to multiple clients (e.g., chat applications), configure a channel layer:

```python title="settings.py"
# Development (in-memory, single-process only)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}

# Production (Redis)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}
```

## Accessing User in Resolvers

With `AuthGraphQLProtocolTypeRouter`, you can access the authenticated user:

```python
import strawberry
from strawberry.types import Info

@strawberry.type
class Query:
    @strawberry.field
    def me(self, info: Info) -> str:
        user = info.context.request.user
        if user.is_authenticated:
            return f"Hello, {user.username}!"
        return "Hello, anonymous!"
```

## Running the Server

### Development

With Daphne installed and configured, `runserver` automatically uses ASGI:

```bash
python manage.py runserver
```

### Production

Use an ASGI server like Daphne, Uvicorn, or Hypercorn:

```bash
# Daphne
daphne myproject.asgi:application

# Uvicorn
uvicorn myproject.asgi:application --host 0.0.0.0 --port 8000

# Hypercorn
hypercorn myproject.asgi:application --bind 0.0.0.0:8000
```

## Advanced: Custom Routing

For more complex setups, you can create custom routing:

```python title="myproject/asgi.py"
import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application
from django.urls import re_path
from strawberry.channels.handlers.http_handler import GraphQLHTTPConsumer
from strawberry.channels.handlers.ws_handler import GraphQLWSConsumer

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django_asgi_app = get_asgi_application()

from myproject.schema import schema

application = ProtocolTypeRouter({
    "http": AuthMiddlewareStack(
        URLRouter([
            re_path(r"^graphql$", GraphQLHTTPConsumer.as_asgi(schema=schema)),
            re_path(r"^", django_asgi_app),
        ])
    ),
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter([
                re_path(r"^graphql$", GraphQLWSConsumer.as_asgi(schema=schema)),
            ])
        )
    ),
})
```

## Troubleshooting

### Subscriptions not working

1. **Check ASGI_APPLICATION** is correctly set in settings
2. **Ensure schema is imported after** `get_asgi_application()` to avoid AppRegistryNotReady errors
3. **Use an ASGI server** - standard `runserver` without Daphne uses WSGI

### User is AnonymousUser

1. Ensure you're using `AuthGraphQLProtocolTypeRouter` (not `GraphQLProtocolTypeRouter`)
2. Check that `AuthMiddlewareStack` is in your routing
3. Verify session cookies are being sent with WebSocket requests

### WebSocket connection refused

1. Check `ALLOWED_HOSTS` in settings includes your hostname
2. Ensure the URL pattern matches your client's WebSocket URL
3. Check browser console for CORS or security errors

## See Also

- [Subscriptions Guide](../guide/subscriptions.md) - Creating subscriptions
- [Strawberry Channels Docs](https://strawberry.rocks/docs/integrations/channels) - Core integration docs
- [Django Channels Docs](https://channels.readthedocs.io/en/stable/) - Full Channels documentation
