# Authentication

```python
from strawberry_django import auth

@strawberry.type
class Query:
    me: User = auth.current_user()

@strawberry.type
class Mutation:
    login: User = auth.login()
    logout = auth.logout()
```
