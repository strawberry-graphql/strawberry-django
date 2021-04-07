import strawberry
from strawberry.arguments import is_unset, UNSET
from django.db.models import fields
import ast
import asyncio
import warnings

def parse_value(value):
    try:
        return ast.literal_eval(value)
    except ValueError:
        raise ValueError('Invalid filter value')

def process_filters(filters):
    filter, exclude = {}, {}
    for string in filters:
        try:
            k, v = string.split('=', 1)
        except ValueError:
            raise ValueError(f'Invalid filter "{filter}"')
        if '!' in k:
            k = k.strip('!')
            exclude[k] = parse_value(v)
        else:
            filter[k] = parse_value(v)
    return filter, exclude

def get_input_data(model, data):
    values = {}
    for field in model._meta.fields:
        field_name = field.attname
        value = getattr(data, field_name, UNSET)
        if is_unset(value):
            continue
        values[field_name] = value
    return values

def get_input_data_m2m(model, data):
    values = {}
    for field in model._meta.many_to_many:
        for action in ('add', 'set', 'remove'):
            field_name = field.attname
            value = getattr(data, f'{field_name}_{action}', UNSET)
            if is_unset(value):
                continue
            actions = values.setdefault(field_name, {})
            actions[action] = value
    return values

def camel_to_snake(s):
    return ''.join(['_'+c.lower() if c.isupper() else c for c in s]).lstrip('_')

def snake_to_camel(s):
    return s.title().replace('_', '')

def is_async():
    # django uses the same method to detect async operation
    # https://github.com/django/django/blob/76c0b32f826469320c59709d31e2f2126dd7c505/django/utils/asyncio.py
    try:
        event_loop = asyncio.get_event_loop()
    except RuntimeError:
        pass
    else:
        if event_loop.is_running():
            return True
    return False


def deprecated(msg, stacklevel=1):
    warnings.warn(msg, DeprecationWarning, stacklevel=stacklevel + 1)
