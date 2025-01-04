from typing import TYPE_CHECKING, Annotated

import strawberry
from strawberry import relay
from typing_extensions import TypeAlias

import strawberry_django
from strawberry_django.relay import ListConnectionWithTotalCount

from .models import TreeNodeAuthor

if TYPE_CHECKING:
    from .b import TreeNodeBookConnection


@strawberry_django.type(TreeNodeAuthor)
class TreeNodeAuthorType(relay.Node):
    name: str
    books: Annotated[
        "TreeNodeBookConnection", strawberry.lazy("tests.relay.treenode.b")
    ] = strawberry_django.connection()
    children: "TreeNodeAuthorConnection" = strawberry_django.connection()


TreeNodeAuthorConnection: TypeAlias = ListConnectionWithTotalCount[TreeNodeAuthorType]
