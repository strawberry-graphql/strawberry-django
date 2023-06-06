import pytest
import strawberry

from strawberry_django import mutations
from tests import types, utils


def test_type_mismatch():
    @strawberry.type
    class Mutation:
        create_fruit: types.Fruit = mutations.create(types.ColorInput)

    with pytest.raises(
        TypeError,
        match="Input and output types should be from the same Django model",
    ):
        return utils.generate_query(mutation=Mutation)
