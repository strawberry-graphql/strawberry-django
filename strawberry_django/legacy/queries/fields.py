from typing import List, Optional
import strawberry
from . import resolvers
from .. import utils
from .arguments import resolve_type_args

def queries(*args, types=None):
    type_args = resolve_type_args(args, types=types)
    query_fields = {}
    for model, object_type in type_args:
        object_name = utils.camel_to_snake(model._meta.object_name)
        query_fields[f'{object_name}'] = resolvers.get_object_resolver(model, object_type)
        query_fields[f'{object_name}s'] = resolvers.get_list_resolver(model, object_type)
    return strawberry.type(type('Query', (), query_fields))

queries.get = resolvers.get_object_resolver
queries.list = resolvers.get_list_resolver
