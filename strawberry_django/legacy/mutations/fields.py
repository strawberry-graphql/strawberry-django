import strawberry
from . import resolvers
from .. import utils
from ..queries.arguments import resolve_type_args


def mutations(*args, types=None):
    type_args = resolve_type_args(args, types=types, is_input=True)
    mutation_fields = {}
    for model, output_type, input_type in type_args:
        object_name = utils.camel_to_snake(model._meta.object_name)
        mutation_fields[f'create_{object_name}'] = resolvers.create(model, output_type, input_type)
        mutation_fields[f'create_{object_name}s'] = resolvers.create_batch(model, output_type, input_type)
        mutation_fields[f'update_{object_name}s'] = resolvers.update(model, output_type, input_type)
        mutation_fields[f'delete_{object_name}s'] = resolvers.delete(model, output_type, input_type)
    return strawberry.type(type('Mutation', (), mutation_fields))

mutations.create = resolvers.create
mutations.create_batch = resolvers.create_batch
mutations.update = resolvers.update
mutations.delete = resolvers.delete 
