import pytest
import strawberry
import strawberry_django
from .. import models, types


def generate_mutation(mutation_type):
    Query = strawberry_django.queries(types.User)
    schema = strawberry.Schema(Query, mutation=mutation_type)
    def mutation(mutation, variable_values=None):
        if not mutation.startswith('mutation'):
            mutation = 'mutation ' + mutation
        return schema.execute_sync(mutation, variable_values=variable_values)
    return mutation

def test_save_hooks(db):
    def hook(info, instance):
        hook.data.append(instance.id)
    hook.data = []

    @strawberry.type
    class Mutation:
        create_user = strawberry_django.mutations.create(models.User, types.User, types.UserInput, pre_save=hook)
        create_user.post_save(hook)
    mutation = generate_mutation(Mutation)

    result = mutation('{ user: createUser(data: { name: "user" }) { id } }')
    assert not result.errors
    assert result.data['user'] == { 'id': '1' }
    assert hook.data == [ None, 1 ]
