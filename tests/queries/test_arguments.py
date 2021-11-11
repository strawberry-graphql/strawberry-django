import pytest

from strawberry_django.legacy.queries.arguments import resolve_type_args
from tests import models, types


def test_types():
    assert resolve_type_args([types.User, types.Group]) == [
        (models.User, types.User),
        (models.Group, types.Group),
    ]


def test_input_types():
    assert resolve_type_args([types.User, types.UserInput], is_input=True) == [
        (models.User, types.User, types.UserInput)
    ]


def test_no_type():
    with pytest.raises(TypeError, match="No type for model 'User'"):
        resolve_type_args([types.User], is_input=True)
