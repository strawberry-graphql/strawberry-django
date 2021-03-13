import strawberry, strawberry_django
from . import models
from .types import types

Query = strawberry_django.queries(models.User, models.Group, types=types)
Mutation = strawberry_django.mutations(models.User, models.Group, types=types)
schema = strawberry.Schema(query=Query, mutation=Mutation)
