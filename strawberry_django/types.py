from typing import List, Optional, cast
import strawberry
from django.db.models import fields, Model
from . import utils

field_type_map = {
    fields.AutoField: strawberry.ID,
    fields.IntegerField: int,
    fields.CharField: str,
    fields.TextField: str,
    fields.BooleanField: bool,
}

def get_field_type(field):
    db_field_type = type(field)
    return field_type_map.get(db_field_type)


model_type_map = {
}

def set_model_type(model, field_type):
    model_type_map[model] = field_type

def get_model_type(model):
    model_type = model_type_map.get(model)
    if model_type is None:
        model_type = LazyModelType(model)
    return model_type

class LazyModelType(strawberry.LazyType):
    def __init__(self, model):
        super().__init__('', '', '')
        self.model = model
    def resolve_type(self):
        if self.model not in model_type_map:
            raise Exception(f'GraphQL type not defined for "{self.model._meta.object_name}" Django model.')
        return model_type_map[self.model]


def get_field(field, is_input, is_update):
    field_type = field_type_map.get(type(field))

    if is_input and field_type == strawberry.ID:
        return #TODO: is this correct?

    if field_type is None:
        print('Unknown field type', type(field))
        return

    if is_input:
        if field.blank or is_update:
            field_type = Optional[field_type]

    return field.name, field_type, strawberry.arguments.UNSET


def get_relation_field(field):
    if hasattr(field, 'get_accessor_name'):
        field_name = field.get_accessor_name()
    else:
        field_name = field.name
    field_type = get_model_type(field.related_model)
    @strawberry.field
    def resolver(info, root,
            filter: Optional[List[str]] = None,
            exclude: Optional[List[str]] = None) -> List[field_type]:
        qs = getattr(root, field_name).all()
        return utils.filter_qs(qs, filter, exclude)

    return field_name, None, resolver


def get_relation_foreignkey_field(field):
    field_name = field.name
    field_type = get_model_type(field.related_model)

    @strawberry.field
    def resolver(info, root) -> Optional[field_type]:
        obj = getattr(root, field_name)
        return obj

    return field_name, None, resolver


def generate_model_type(resolver, is_input=False, is_update=False):
    model = resolver.model
    annotations = {}
    attributes = { '__annotations__': annotations }
    resolver_fields = getattr(resolver, 'fields', None)
    resolver_exclude = getattr(resolver, 'exclude', None)

    # add fields
    for field in model._meta.get_fields():
        if resolver_fields and field.name not in resolver_fields:
            continue # skip
        if resolver_exclude and field.name in resolver_exclude:
            continue # skip
        if field.is_relation:
            if is_input:
                continue
            if isinstance(field, fields.related.ForeignKey):
                field_params = get_relation_foreignkey_field(field)
            else:
                field_params = get_relation_field(field)
        else:
            field_params = get_field(field, is_input, is_update)
        if not field_params:
            continue
        field_name, field_type, field_value = field_params
        attributes[field_name] = field_value
        if field_type:
            annotations[field_name] = field_type
    if not is_input:
        for field_name in dir(resolver):
            field = getattr(resolver, field_name)
            if hasattr(field, '_field_definition'):
                attributes[field_name] = field

    # generate type
    type_name = model._meta.object_name
    if is_update:
        type_name = f'Update{type_name}'
    elif is_input:
        type_name = f'Create{type_name}'
    model_type = type(type_name, (), attributes)
    model_type = strawberry.type(model_type, is_input=is_input)
    if not is_input:
        set_model_type(model, model_type)
    return model_type
