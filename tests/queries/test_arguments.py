import pytest
from strawberry_django.legacy.queries.arguments import resolve_type_args
from ..import models, types

def test_types():
    assert resolve_type_args([types.User, types.Group]) == [
        (models.User, types.User),
        (models.Group, types.Group),
    ]

def test_input_types():
    assert resolve_type_args([types.User, types.UserInput], is_input=True) == [
        (models.User, types.User, types.UserInput)
    ]

def test_models_with_type_register():
    assert resolve_type_args([models.User, models.Tag], types=types.types, is_input=True) == [
        (models.User, types.User, types.UserInput),
        (models.Tag, types.Tag, types.TagInput),
    ]

def test_mixed_args_with_type_register():
    assert resolve_type_args([models.User, types.Group, types.TagInput], types=types.types) == [
        (models.User, types.User),
        (models.Group, types.Group),
        (models.Tag, types.Tag),
    ]

def test_no_type():
    with pytest.raises(TypeError, match="No type for model 'User'"):
        resolve_type_args([types.User], is_input=True)
