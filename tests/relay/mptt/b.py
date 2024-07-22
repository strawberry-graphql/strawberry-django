from typing import TYPE_CHECKING

import strawberry
from strawberry import relay
from typing_extensions import Annotated, TypeAlias

import strawberry_django
from strawberry_django.relay import ListConnectionWithTotalCount

from .models import MPTTBook

if TYPE_CHECKING:
    from .a import MPTTAuthorType


@strawberry_django.filter(MPTTBook)
class MPTTBookFilter:
    name: str


@strawberry_django.order(MPTTBook)
class MPTTBookOrder:
    name: str


@strawberry_django.type(MPTTBook, filters=MPTTBookFilter, order=MPTTBookOrder)
class MPTTBookType(relay.Node):
    name: str
    author: Annotated["MPTTAuthorType", strawberry.lazy("tests.relay.mptt.a")]


MPTTBookConnection: TypeAlias = ListConnectionWithTotalCount[MPTTBookType]
