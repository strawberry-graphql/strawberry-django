# Strawberry GraphQL Django extension

[![CI](https://github.com/la4de/strawberry-graphql-django/actions/workflows/main.yml/badge.svg)](https://github.com/la4de/strawberry-graphql-django/actions/workflows/main.yml)
[![PyPI](https://img.shields.io/pypi/v/strawberry-graphql-django)](https://pypi.org/project/strawberry-graphql-django/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/strawberry-graphql-django)](https://pypi.org/project/strawberry-graphql-django/)

This library provides helpers to generate types, mutations and resolvers for Django models.

> NOTE: Package v0.1.0 introduced new API. See more detailed description about new API from [the ticket](https://github.com/strawberry-graphql/strawberry-graphql-django/issues/10). Old version is still available in [v0.0.x](https://github.com/strawberry-graphql/strawberry-graphql-django/tree/v0.0.x) branch.

Installing strawberry-graphql-django packet from the python package repository.
```shell
pip install strawberry-graphql-django
```


## Example project files

See example Django project [examples/django](https://github.com/strawberry-graphql/strawberry-graphql-django/tree/main/examples/django).

models.py
```python
from django.db import models

class User(models.Model):
    name = models.CharField(max_length=50)
    groups = models.ManyToManyField('Group', related_name='users')

class Group(models.Model):
    name = models.CharField(max_length=50)
```

types.py
```python
import strawberry
import strawberry_django
from . import models

# model types are collected into register. type converters use
# register to resolve types of relation fields
types = strawberry_django.TypeRegister()

@types.register
@strawberry_django.type(models.User, types=types)
class User:
    # types can be extended with own fields and resolvers
    @strawberry.field
    def name_upper(root) -> str:
        return root.name.upper()

@types.register
@strawberry_django.type(models.Group, fields=['id'], types=types)
class Group:
    # fields can be remapped
    group_name: str = strawberry_django.field(field_name='name')

@types.register
@strawberry_django.input(models.User)
class UserInput:
    pass
```

schema.py
```python
import strawberry, strawberry_django
from . import models
from .types import types

Query = strawberry_django.queries(models.User, models.Group, types=types)
Mutation = strawberry_django.mutations(models.User, types=types)
schema = strawberry.Schema(query=Query, mutation=Mutation)
```

urls.py
```python
from django.urls import include, path
from strawberry.django.views import AsyncGraphQLView
from .schema import schema

urlpatterns = [
    path('graphql', AsyncGraphQLView.as_view(schema=schema)),
]
```

Now we have models, types, schema and graphql view. It is time to crete database and start development server.
```shell
manage.py makemigrations
manage.py migrate
manage.py runserver
```

## Mutations and Queries

Once the server is running you can open your browser to http://localhost:8000/graphql and start testing auto generated queries and mutations.

Create new user.
```
mutation {
  createUsers(data: { name: "my user" }) {
    id
  }
}
```

Make first queries.
```
query {
  user(id: 1) {
    name
    groups {
      groupName
    }
  }
  users(filters: ["name__contains='my'"]) {
    id
    name
    nameUpper
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
  deleteUsers(filters: ["id=1"])
}
```

## Typed filtering with Django Filter

Install django-filters `pip install django-filter`

Then add `django_filters` to your INSTALLED_APPS.

```python
INSTALLED_APPS = [
    ...
    'django_filters',
]
```

Write a `FilterSet` and decorate it with `strawberry_django.create_filter`:

```python
import strawberry_django
import django_filters


@strawberry_django.filter
class UserFilter(django_filters.FilterSet):
    # These fields definitions are optional, 
    # they can be automatically generated.

    name = django_filters.CharFilter(lookup_expr="icontains")
    search = django_filters.CharFilter(method="filter_search")

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value) |
            Q(group__name__icontains=value) |
            Q(tag__name__icontains=value)
        )

    class Meta:
        model = models.User
        fields = ["name", "search"]
```

Create the input type with `UserFilter`, and filter a queryset with `strawberry_django.filters.apply`

```python
@strawberry.type
class Query:
    @strawberry.field
    def user_ids(self, filters: Optional[UserFilter] = UNSET) -> List[int]:
        queryset = models.User.objects.all()
        queryset = strawberry_django.filters.apply(filters, queryset)
        return queryset.order_by("pk").values_list("pk", flat=True)
```

The schema will be:
```
type Query {
  userIds(filters: UserFilter): [Int!]!
}

input UserFilter {
  name: String
  search: String
}
```

And can be queried with:
```
query getUserIds {
    userIds (filters: {"name": "user1", "search": "tag2"})
}
```

See django-filter docs for details on writing FilterSets: https://django-filter.readthedocs.io

## Django authentication examples

`strawberry_django` provides mutations for authentications.

schema.py:
```
class IsAuthenticated(strawberry.BasePermission):
    def has_permission(self, source: Any, info: Info, **kwargs) -> bool:
        self.message = "Not authenticated"
        return info.context.request.user.is_authenticated

@strawberry.type
class Query:
    @strawberry.field(permission_classes=[IsAuthenticated])
    def current_user(self, info: Info) -> types.User:
        return info.context.request.user

schema = strawberry.Schema(query=Query, mutation=strawberry_django.AuthMutation)
```

Login and logout with:
```
mutation {
  login(username:"myuser", password:"mypassword")
  logout()
}
```

Get current user with:
```
query {
  currentUser {
    id
    firstName
    lastName
  }
}
```

## Running unit tests
```
poetry install
poetry run pytest
```

## Contributing

I would be more than happy to get pull requests, improvement ideas and feedback from you.
