import strawberry

def split_filters(filters):
    filter, exclude = {}, {}
    for string in filters:
        try:
            k, v = string.split('=', 1)
        except ValueError:
            raise ValueError(f'Invalid filter "{filter}"')
        if k.startswith('!'):
            k = k.strip('!')
            exclude[k] = v
        else:
            filter[k] = v
    return filter, exclude

def get_data(model, data):
    values = {}
    for field in model._meta.fields:
        value = getattr(data, field.name, strawberry.arguments.UNSET)
        if value is strawberry.arguments.UNSET:
            continue
        values[field.name] = value
    return values

def camel_to_snake(s):
    return ''.join(['_'+c.lower() if c.isupper() else c for c in s]).lstrip('_')
