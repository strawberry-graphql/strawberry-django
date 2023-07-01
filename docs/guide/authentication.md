# Authentication

!!! warning

    This solution is enough for web browsers, but will not work for clients that
    doesn't have a way to store cookies in it (e.g. mobile apps). For those it is
    recommended to use token authentication methods. JWT can be used with
    [strawberry-django-jwt](https://github.com/KundaPanda/strawberry-django-jwt)
    lib.

`strawberry_django` provides mutations to get authentication going right away.
The `auth.register` mutation performs password validation using Django's `validate_password` method.

```{.python title=types.py}
import strawberry
from strawberry import auto
from django.contrib.auth import get_user_model

@strawberry.django.type(get_user_model())
class User:
    username: auto
    email: auto

@strawberry.django.input(get_user_model())
class UserInput:
    username: auto
    password: auto
```

```{.python title=schema.py}
from strawberry.django import auth
from .types import User, UserInput

@strawberry.type
class Query:
    me: User = auth.current_user()

@strawberry.type
class Mutation:
    login: User = auth.login()
    logout = auth.logout()
    register: User = auth.register(UserInput)
```
