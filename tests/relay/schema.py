from typing import (
    Any,
    ClassVar,
    Iterable,
    List,
    Optional,
)

import strawberry
import strawberry.django
from django.db import models
from strawberry import relay
from strawberry.permission import BasePermission
from strawberry.types import Info
from typing_extensions import Annotated

from strawberry_django.relay import ListConnectionWithTotalCount


class FruitModel(models.Model):
    class Meta:
        ordering: ClassVar[List[str]] = ["id"]

    name = models.CharField(max_length=255)
    color = models.CharField(max_length=255)


@strawberry.django.filter(FruitModel, lookups=True)
class FruitFilter:
    name: strawberry.auto
    color: strawberry.auto


@strawberry.django.order(FruitModel)
class FruitOrder:
    name: strawberry.auto
    color: strawberry.auto


@strawberry.django.type(FruitModel)
class Fruit(relay.Node):
    name: strawberry.auto
    color: strawberry.auto


class DummyPermission(BasePermission):
    message = "Dummy message"

    async def has_permission(self, source: Any, info: Info, **kwargs: Any) -> bool:
        return True


@strawberry.type
class Query:
    node: relay.Node = strawberry.django.node()
    node_with_async_permissions: relay.Node = strawberry.django.node(
        permission_classes=[DummyPermission],
    )
    nodes: List[relay.Node] = strawberry.django.node()
    node_optional: Optional[relay.Node] = strawberry.django.node()
    nodes_optional: List[Optional[relay.Node]] = strawberry.django.node()
    fruits: ListConnectionWithTotalCount[Fruit] = strawberry.django.connection()
    fruits_lazy: ListConnectionWithTotalCount[
        Annotated["Fruit", strawberry.lazy("tests.relay.schema")]
    ] = strawberry.django.connection()
    fruits_with_filters_and_order: ListConnectionWithTotalCount[Fruit] = (
        strawberry.django.connection(
            filters=FruitFilter,
            order=FruitOrder,
        )
    )

    @strawberry.django.connection(ListConnectionWithTotalCount[Fruit])
    def fruits_custom_resolver(self, info: Info) -> Iterable[FruitModel]:
        return FruitModel.objects.all()

    @strawberry.django.connection(
        ListConnectionWithTotalCount[Fruit],
        filters=FruitFilter,
        order=FruitOrder,
    )
    def fruits_custom_resolver_with_filters_and_order(
        self,
        info: Info,
    ) -> Iterable[FruitModel]:
        return FruitModel.objects.all()


schema = strawberry.Schema(query=Query)
