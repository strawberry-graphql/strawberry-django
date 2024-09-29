---
title: Authentication
---

# Authentication

> [!WARNING]
> This solution is enough for web browsers, but will not work for clients that
> doesn't have a way to store cookies in it (e.g. mobile apps). For those it is
> recommended to use token authentication methods. JWT can be used with
> [strawberry-django-auth](https://github.com/nrbnlulu/strawberry-django-auth)
> lib.

`strawberry_django` provides mutations to get authentication going right away.
The `auth.register` mutation performs password validation using Django's `validate_password` method.

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
```

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
