from typing import TYPE_CHECKING, Annotated

import strawberry
from strawberry import relay
from typing_extensions import TypeAlias

import strawberry_django
from strawberry_django.relay import ListConnectionWithTotalCount

from .models import TreeNodeBook

if TYPE_CHECKING:
    from .a import TreeNodeAuthorType


@strawberry_django.filter(TreeNodeBook)
class TreeNodeBookFilter:
    name: str


@strawberry_django.order(TreeNodeBook)
class TreeNodeBookOrder:
    name: str


@strawberry_django.type(
    TreeNodeBook, filters=TreeNodeBookFilter, order=TreeNodeBookOrder
)
class TreeNodeBookType(relay.Node):
    name: str
    author: Annotated["TreeNodeAuthorType", strawberry.lazy("tests.relay.treenode.a")]


TreeNodeBookConnection: TypeAlias = ListConnectionWithTotalCount[TreeNodeBookType]
