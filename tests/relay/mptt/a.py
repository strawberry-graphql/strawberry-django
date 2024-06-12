from typing import TYPE_CHECKING

import strawberry
from strawberry import relay
from typing_extensions import Annotated, TypeAlias

import strawberry_django
from strawberry_django.relay import ListConnectionWithTotalCount

from .models import MPTTAuthor

if TYPE_CHECKING:
    from .b import MPTTBookConnection


@strawberry_django.type(MPTTAuthor)
class MPTTAuthorType(relay.Node):
    name: str
    books: Annotated["MPTTBookConnection", strawberry.lazy("tests.relay.mptt.b")] = (
        strawberry_django.connection()
    )
    children: "MPTTAuthorConnection" = strawberry_django.connection()


MPTTAuthorConnection: TypeAlias = ListConnectionWithTotalCount[MPTTAuthorType]
