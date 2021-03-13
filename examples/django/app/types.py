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

@types.register
@strawberry_django.input(models.Group)
class GroupInput:
    pass
