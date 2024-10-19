from collections.abc import Awaitable
from typing import Any, Union

import pytest
import strawberry
from strawberry import BasePermission, Info

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from tests import models


@pytest.mark.django_db(transaction=True)
async def test_with_async_permission(db):
    class AsyncPermission(BasePermission):
        async def has_permission(  # type: ignore
            self,
            source: Any,
            info: Info,
            **kwargs: Any,
        ) -> Union[bool, Awaitable[bool]]:
            return True

    @strawberry_django.type(models.Fruit)
    class Fruit:
        name: strawberry.auto

    @strawberry_django.type(models.Color)
    class Color:
        name: strawberry.auto
        fruits: list[Fruit] = strawberry_django.field(
            permission_classes=[AsyncPermission]
        )

    @strawberry.type(name="Query")
    class Query:
        colors: list[Color] = strawberry_django.field()

    red = await models.Color.objects.acreate(name="Red")
    yellow = await models.Color.objects.acreate(name="Yellow")

    await models.Fruit.objects.acreate(name="Apple", color=red)
    await models.Fruit.objects.acreate(name="Banana", color=yellow)
    await models.Fruit.objects.acreate(name="Strawberry", color=red)

    schema = strawberry.Schema(query=Query)
    query = """
        query {
          colors {
            name
            fruits {
              name
            }
          }
        }
    """

    result = await schema.execute(query)
    assert result.errors is None
    assert result.data == {
        "colors": [
            {
                "name": "Red",
                "fruits": [
                    {"name": "Apple"},
                    {"name": "Strawberry"},
                ],
            },
            {
                "name": "Yellow",
                "fruits": [{"name": "Banana"}],
            },
        ]
    }


@pytest.mark.django_db(transaction=True)
async def test_with_async_permission_and_optimizer(db):
    class AsyncPermission(BasePermission):
        async def has_permission(  # type: ignore
            self,
            source: Any,
            info: Info,
            **kwargs: Any,
        ) -> Union[bool, Awaitable[bool]]:
            return True

    @strawberry_django.type(models.Fruit)
    class Fruit:
        name: strawberry.auto

    @strawberry_django.type(models.Color)
    class Color:
        name: strawberry.auto
        fruits: list[Fruit] = strawberry_django.field(
            permission_classes=[AsyncPermission]
        )

    @strawberry.type(name="Query")
    class Query:
        colors: list[Color] = strawberry_django.field()

    red = await models.Color.objects.acreate(name="Red")
    yellow = await models.Color.objects.acreate(name="Yellow")

    await models.Fruit.objects.acreate(name="Apple", color=red)
    await models.Fruit.objects.acreate(name="Banana", color=yellow)
    await models.Fruit.objects.acreate(name="Strawberry", color=red)

    schema = strawberry.Schema(
        query=Query,
        extensions=[DjangoOptimizerExtension()],
    )
    query = """
        query {
          colors {
            name
            fruits {
              name
            }
          }
        }
    """

    result = await schema.execute(query)
    assert result.errors is None
    assert result.data == {
        "colors": [
            {
                "name": "Red",
                "fruits": [
                    {"name": "Apple"},
                    {"name": "Strawberry"},
                ],
            },
            {
                "name": "Yellow",
                "fruits": [{"name": "Banana"}],
            },
        ]
    }


@pytest.mark.django_db(transaction=True)
def test_with_sync_permission(db):
    class AsyncPermission(BasePermission):
        def has_permission(
            self,
            source: Any,
            info: Info,
            **kwargs: Any,
        ) -> Union[bool, Awaitable[bool]]:
            return True

    @strawberry_django.type(models.Fruit)
    class Fruit:
        name: strawberry.auto

    @strawberry_django.type(models.Color)
    class Color:
        name: strawberry.auto
        fruits: list[Fruit] = strawberry_django.field(
            permission_classes=[AsyncPermission]
        )

    @strawberry.type(name="Query")
    class Query:
        colors: list[Color] = strawberry_django.field()

    red = models.Color.objects.create(name="Red")
    yellow = models.Color.objects.create(name="Yellow")

    models.Fruit.objects.create(name="Apple", color=red)
    models.Fruit.objects.create(name="Banana", color=yellow)
    models.Fruit.objects.create(name="Strawberry", color=red)

    schema = strawberry.Schema(query=Query)
    query = """
        query {
          colors {
            name
            fruits {
              name
            }
          }
        }
    """

    result = schema.execute_sync(query)
    assert result.errors is None
    assert result.data == {
        "colors": [
            {
                "name": "Red",
                "fruits": [
                    {"name": "Apple"},
                    {"name": "Strawberry"},
                ],
            },
            {
                "name": "Yellow",
                "fruits": [{"name": "Banana"}],
            },
        ]
    }


@pytest.mark.django_db(transaction=True)
def test_with_sync_permission_and_optimizer(db):
    class AsyncPermission(BasePermission):
        def has_permission(
            self,
            source: Any,
            info: Info,
            **kwargs: Any,
        ) -> Union[bool, Awaitable[bool]]:
            return True

    @strawberry_django.type(models.Fruit)
    class Fruit:
        name: strawberry.auto

    @strawberry_django.type(models.Color)
    class Color:
        name: strawberry.auto
        fruits: list[Fruit] = strawberry_django.field(
            permission_classes=[AsyncPermission]
        )

    @strawberry.type(name="Query")
    class Query:
        colors: list[Color] = strawberry_django.field()

    red = models.Color.objects.create(name="Red")
    yellow = models.Color.objects.create(name="Yellow")

    models.Fruit.objects.create(name="Apple", color=red)
    models.Fruit.objects.create(name="Banana", color=yellow)
    models.Fruit.objects.create(name="Strawberry", color=red)

    schema = strawberry.Schema(
        query=Query,
        extensions=[DjangoOptimizerExtension()],
    )
    query = """
        query {
          colors {
            name
            fruits {
              name
            }
          }
        }
    """

    result = schema.execute_sync(query)
    assert result.errors is None
    assert result.data == {
        "colors": [
            {
                "name": "Red",
                "fruits": [
                    {"name": "Apple"},
                    {"name": "Strawberry"},
                ],
            },
            {
                "name": "Yellow",
                "fruits": [{"name": "Banana"}],
            },
        ]
    }
