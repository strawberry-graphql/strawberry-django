import pytest
import strawberry
import strawberry_django
from .. import types

@pytest.fixture
def schema():
    Query = strawberry_django.queries(types.User)
    Mutation = strawberry_django.mutations(types.User, types.Group, types.Tag, types=types.types)
    schema = strawberry.Schema(Query, mutation=Mutation)
    return schema

@pytest.fixture
def mutation(schema, db):
    def mutation(mutation, variable_values=None):
        if not mutation.startswith('mutation'):
            mutation = 'mutation ' + mutation
        return schema.execute_sync(mutation, variable_values=variable_values)
    return mutation
