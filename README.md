# Strawberry GraphQL Django extension

This library provides helpers to generate fields, mutations and resolvers from you Django models.

models.py:
```python
from django.db import models

class User(models.Model):
    name = models.CharField(max_length=50)
    age = models.IntegerField()
    groups = models.ManyToManyField('Group', related_name='users')

class Group(models.Model):
    name = models.CharField(max_length=50)
```

schema.py:
```python
import strawberry
from strawberry_django import ModelResolver
from .models import User, Group

class UserResolver(ModelResolver):
    model = User

class GroupResolver(ModelResolver):
    model = Group

@strawberry.type
class Query(UserResolver.query(), GroupResolver.query()):
    pass

@strawberry.type
class Mutation(UserResolver.mutation(), GroupResolver.mutation()):
    pass

schema = strawberry.Schema(query=Query, mutation=Mutation)
```

urls.py:
```python
from strawberry.django.views import GraphQLView
from .schema import schema

urlpatterns = [
    path('graphql', GraphQLView.as_view(schema=schema)),
]
```

Create database and start server
```shell
manage.py runserver
```

Open http://localhost:8000/graphql and start testing.
Create user and make first query
```
mutation {
  createUser(data: {name: "hello", age: 20} ) {
    id
  }
}
```
```
query {
  user(id: 1) {
    name
    age
  }
  users(filter: ["name__contains=my"]) {
    id
    name
  }
}
```
