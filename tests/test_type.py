import pytest
import strawberry
from strawberry_django import ModelResolver
from strawberry_django.types import generate_model_type
from .app.models import DataModel, User, UnknownFieldModel

def generate_and_get_fields(resolver_or_model, **kwargs):
    if issubclass(resolver_or_model, ModelResolver):
        Resolver = resolver_or_model
    else:
        class Resolver(ModelResolver):
            model = resolver_or_model
    model_type = generate_model_type(Resolver, **kwargs)
    return { field.name: field for field in model_type._type_definition.fields }


def test_field_types(db):
    fields = generate_and_get_fields(DataModel)

    assert fields['id'].type == strawberry.ID
    assert fields['char'].type == str
    assert fields['integer'].type == int
    assert fields['text'].type == str


def test_optional_field(db):
    fields = generate_and_get_fields(DataModel, is_input=True)

    assert fields['mandatory'].is_optional == False
    assert fields['optional'].is_optional == True
    assert fields['nullable'].is_optional == True
    assert fields['hasdefault'].is_optional == True


def test_relation_field(db):
    fields = generate_and_get_fields(DataModel)

    assert fields['relation'].child != None


def test_include_fields(db):
    class Resolver(ModelResolver):
        model = DataModel
        fields = ['id', 'char']

    fields = generate_and_get_fields(Resolver)

    assert list(fields.keys()) == ['id', 'char']


def test_exclude_fields(db):
    class Resolver(ModelResolver):
        model = DataModel
        exclude = ['id']

    fields = generate_and_get_fields(Resolver)

    assert 'id' not in fields
    assert 'char' in fields


def test_read_only_fields(db):
    class Resolver(ModelResolver):
        model = DataModel
        readonly_fields = ['text']

    fields = generate_and_get_fields(Resolver, is_input=True)
    assert 'text' not in list(fields.keys())


def test_unknown_field_type(db):
    with pytest.raises(TypeError):
        generate_and_get_fields(UnknownFieldModel)


def test_input_foreign_key_field(db):
    fields = generate_and_get_fields(DataModel, is_input=True)

    assert fields['foreignKey'].type == strawberry.ID
    assert fields['foreignKey'].is_optional == True
