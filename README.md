# Strawberry GraphQL Django extension

This library provides helpers to generate fields, mutations and resolvers for Django models.

## Sample project files

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
from strawberry_django import ModelResolver, ModelPermissions
from .models import User, Group

class UserResolver(ModelResolver):
    model = User
    @strawberry.field
    def age_in_months(info, root) -> int:
        return root.age * 16

class GroupResolver(ModelResolver):
    model = Group
    fields = ['name', 'users']
    # only users who have permissions for group models can access and modify
    permissions_classess = [ModelPermissions]
    def get_queryset(self):
        qs = super().get_queryset()
        return qs

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

Add models and schema. Create database. Start development server.
```shell
pip install strawberry-graphql-django
manage.py makemigrations
manage.py migrate
manage.py runserver
```

## Mutations and Queries

Open http://localhost:8000/graphql and start testing.

Create new user.
```
mutation {
  createUser(data: {name: "my user", age: 20}) {
    id
  }
}
```

Make first queries.
```
query {
  user(id: 1) {
    name
    age
    groups {
        name
    }
  }
  users(filters: ["name__contains=my", "!age__gt=60"]) {
    id
    name
    age_in_months
  }
}
```

Update user data.
```
mutation {
  updateUsers(data: {name: "new name"}, filters: ["id=1"]) {
    id
    name
  }
}
```

Finally delete user.
```
mutation {
  deleteUsers(filter: ["id=1"]) {
    id
  }
}
```

## Next steps
* check python package metadata and dependencies
* improve relation field handling
* add documentation
* add resolvers for user login and logout
* example app and demo site
