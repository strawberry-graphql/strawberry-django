import strawberry
import typing
from .types import get_model_fields, update_fields
from .utils import deprecated
from ..fields.types import is_auto

_type = type

def type(model, *, fields=None, types=None, **kwargs):
    stacklevel = kwargs.get('is_input', False) and 4 or 3
    if 'fields' in kwargs:
        utils.deprecated("'fields' parameter is deprecated,"
            " please define all fields in class", stacklevel=stacklevel)
    if 'types' in kwargs:
        utils.deprecated("'types' parameter is deprecated,"
            " please define all types in class", stacklevel=stacklevel)
    def wrapper(cls):
        is_input = kwargs.get('is_input', False)
        partial = kwargs.pop('partial', False)
        model_fields = get_model_fields(cls, model, fields, types, is_input, partial)
        if not hasattr(cls, '__annotations__'):
            cls.__annotations__ = {}
        for field_name, field_type, field_value in model_fields:
            if field_name not in cls.__annotations__:
                cls.__annotations__[field_name] = field_type
            if not hasattr(cls, field_name):
                setattr(cls, field_name, field_value)
        for field_name, field_type in cls.__annotations__.items():
            if is_auto(field_type):
                raise TypeError(f"Field '{field_name}' has invalid type."
                    " Type 'auto' cannot be use together with"
                    " 'fields' parameter."
                )
        update_fields(cls, model)
        cls._django_model = model
        cls._partial = partial
        return strawberry.type(cls, **kwargs)
    return wrapper


def input(model, *, fields=None, types=None, partial=False, **kwargs):
    if 'is_update' in kwargs:
        deprecated("'is_update' argument is deprecated, please use 'partial' instead", stacklevel=2)
        partial = kwargs.pop('is_update')
    return type(model, fields=fields, types=types, partial=partial, is_input=True, **kwargs)


def generate_partial_input(model, input):
    if input._partial:
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
