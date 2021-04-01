import strawberry
import typing
from .types import get_model_fields, update_fields

_type = type

def type(model, *, fields=None, types=None, is_update=False, **kwargs):
    def wrapper(cls):
        is_input = kwargs.get('is_input', False)
        model_fields = get_model_fields(cls, model, fields, types, is_input, is_update)
        if not hasattr(cls, '__annotations__'):
            cls.__annotations__ = {}
        for field_name, field_type, field_value in model_fields:
            if field_name not in cls.__annotations__:
                cls.__annotations__[field_name] = field_type
            if not hasattr(cls, field_name):
                setattr(cls, field_name, field_value)
        update_fields(cls, model)
        cls._django_model = model
        cls._is_update = is_update
        return strawberry.type(cls, **kwargs)
    return wrapper


def input(model, *, fields=None, types=None, is_update=False, **kwargs):
    return type(model, fields=fields, types=types, is_update=is_update, is_input=True, **kwargs)


def generate_update_from_input(model, input):
    if input._is_update:
        return input
    cls = _type(f'{input.__name__}Update', (), { '__annotations__': {}})
    for field_name, field_type in input.__annotations__.items():
        field_value = getattr(input, field_name)
        if typing.get_origin(field_type) != typing.Optional:
            field_type = typing.Optional[field_type]
        cls.__annotations__[field_name] = field_type
        setattr(cls, field_name, field_value)
    cls._django_model = model
    return strawberry.type(cls, is_input=True)
