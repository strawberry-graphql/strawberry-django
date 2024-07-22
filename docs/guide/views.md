---
title: Views
---

# Serving the API

Strawberry works both with ASGI (async) and WSGI (sync). This integration
supports both ways of serving django.

ASGI is the best way to enjoy everything that strawberry has to offer and
is highly recommended unless you can't for some reason. By using WSGI
you will be missing support for some interesting features, such as
[Data Loaders](https://strawberry.rocks/docs/guides/dataloaders).

# Serving as ASGI (async)

Expose the strawberry API when using ASGI by setting your urls.py like this:

```{.python title=urls.py}
from django.urls import path
from strawberry.django.views import AsyncGraphQLView

from .schema import schema

urlpatterns = [
    path('graphql', AsyncGraphQLView.as_view(schema=schema)),
]
```

# Serving WSGI (sync)

Expose the strawberry API when using WSGI by setting your urls.py like this:

```{.python title=urls.py}
from django.urls import path
from strawberry.django.views import GraphQLView

from .schema import schema

urlpatterns = [
    path('graphql', GraphQLView.as_view(schema=schema)),
]
```
