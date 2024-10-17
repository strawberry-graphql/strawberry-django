from typing import TYPE_CHECKING, Annotated

import strawberry
from strawberry import relay
from typing_extensions import TypeAlias

import strawberry_django
from strawberry_django.relay import ListConnectionWithTotalCount

from .models import RelayBook

if TYPE_CHECKING:
    from .a import AuthorType


@strawberry_django.filter(RelayBook)
class BookFilter:
    name: str


@strawberry_django.order(RelayBook)
class BookOrder:
    name: str


@strawberry_django.type(RelayBook, filters=BookFilter, order=BookOrder)
class BookType(relay.Node):
    name: str
    author: Annotated["AuthorType", strawberry.lazy("tests.relay.lazy.a")]


BookConnection: TypeAlias = ListConnectionWithTotalCount[BookType]
