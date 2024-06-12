from typing import TYPE_CHECKING

import strawberry
from strawberry import relay
from typing_extensions import Annotated, TypeAlias

import strawberry_django
from strawberry_django.relay import ListConnectionWithTotalCount

from .models import RelayAuthor

if TYPE_CHECKING:
    from .b import BookConnection


@strawberry_django.type(RelayAuthor)
class AuthorType(relay.Node):
    name: str
    books: Annotated["BookConnection", strawberry.lazy("tests.relay.lazy.b")] = (
        strawberry_django.connection()
    )
    children: 'AuthorConnection' = strawberry_django.connection()


AuthorConnection: TypeAlias = ListConnectionWithTotalCount[AuthorType]
