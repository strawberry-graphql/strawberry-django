---
title: Django Debug Toolbar
---

# django-debug-toolbar

This integration provides integration between the
[Django Debug Toolbar](https://github.com/jazzband/django-debug-toolbar) and
`strawberry`, allowing it to display stats like `SQL Queries`, `CPU Time`, `Cache Hits`, etc
for queries and mutations done inside the [graphiql page](https://github.com/graphql/graphiql).

To use it, make sure you have the
[Django Debug Toolbar](https://github.com/jazzband/django-debug-toolbar) installed
and configured, then change its middleware settings from:

```python title="settings.py"
MIDDLEWARE = [
    ...
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    ...
]
```

To:

```python title="settings.py"
MIDDLEWARE = [
    ...
    "strawberry_django.middlewares.debug_toolbar.DebugToolbarMiddleware",
    ...
]
```

Finally, ensure app `"strawberry_django"` is added to your `INSTALLED_APPS` in Django settings.
