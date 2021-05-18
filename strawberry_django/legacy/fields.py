import strawberry
from typing import Callable, List, Optional, Dict
import dataclasses
from . import utils, queries

@dataclasses.dataclass
class DjangoField:
    resolver: Callable
    field_name: Optional[str]
    kwargs: dict

    def resolve(self, is_relation, is_m2m):
        resolver = queries.resolvers.get_resolver(self.resolver, self.field_name, is_relation, is_m2m)
        field = strawberry.field(resolver, **self.kwargs)
        return field


def field(resolver=None, field_name=None, **kwargs):
    if resolver:
        resolver = queries.resolvers.get_resolver(resolver)
        return strawberry.field(resolver)

    return DjangoField(resolver, field_name, kwargs)

mutation = field
