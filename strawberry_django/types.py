from . import utils
from .type import type as strawberry_django_type


def from_type(type_, *, is_input=False, partial=False):
    type_name = type_.__name__
    if partial:
        type_name += "Partial"
    if is_input:
        type_name += "Input"
    type_name += "Type"
    model = utils.get_django_model(type_)
    cls = type(type_name, (type_,), {})
    return strawberry_django_type(model, is_input=is_input, partial=partial)(cls)
