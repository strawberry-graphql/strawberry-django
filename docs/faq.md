# Frequently Asked Questions (FAQ)

## How to access Django request object in resolvers?

The request object is accessible via the `info.context.request` object.

```python
def resolver(root, info: Info):
    request = info.context.request
```

## How to access the current user object in resolvers?

The current user object is accessible via the `get_current_user` method.

```python
from strawberry_django.auth.queries import get_current_user

def resolver(root, info: Info):
    current_user = get_current_user(info)
```

## Autocompletion with editors

Some editors like VSCode may not be able to resolve symbols and types without explicit `strawberry.django` import. Adding following line to code fixes that problem.

```python
import strawberry.django
```

## Example project?

See complete Django project from github repository folder [examples/django](https://github.com/strawberry-graphql/strawberry-graphql-django/tree/main/examples/django).
