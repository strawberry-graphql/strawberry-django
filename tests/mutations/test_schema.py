import pytest
import strawberry
from .. import utils, types
from strawberry_django import mutations

def test_type_mismatch():
    @strawberry.type
    class Mutation:
        createFruit: types.Fruit = mutations.create(types.ColorInput)

    with pytest.raises(TypeError, match='Input and'
            ' output types should be from the same Django model'):
        return utils.generate_query(mutation=Mutation)
