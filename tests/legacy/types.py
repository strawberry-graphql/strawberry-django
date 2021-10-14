import strawberry_django

from . import models

types = strawberry_django.TypeRegister()


@types.register
@strawberry_django.type(models.User, types=types)
class User:
    pass


@types.register
@strawberry_django.type(models.Group, types=types)
class Group:
    pass


@types.register
@strawberry_django.type(models.Tag, types=types)
class Tag:
    pass


@types.register
@strawberry_django.input(models.User, types=types)
class UserInput:
    pass


@types.register
@strawberry_django.input(models.Group, types=types)
class GroupInput:
    pass


@types.register
@strawberry_django.input(models.Tag, types=types)
class TagInput:
    pass
