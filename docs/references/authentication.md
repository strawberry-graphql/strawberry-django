# Authentication

strawberry_django provides mutations to get authentication going right
away. The auth.register mutation performs password validation using Django's
validate_password().

```python
# types.py
import strawberry_django
from strawberry_django import auto
from django.contrib.auth import get_user_model

@strawberry_django.type(get_user_model())
class User:
    username: auto
    email: auto

@strawberry_django.input(get_user_model())
class UserInput:
    username: auto
    password: auto

# schema.py
from strawberry_django import auth
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
