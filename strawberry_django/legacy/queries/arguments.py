from ..registers import TypeRegister
from django.db.models.base import ModelBase

def resolve_type_args(args, types=None, is_input=False, single=False):
    arg_types = TypeRegister()
    models = []
    for arg in args:
        if isinstance(arg, ModelBase):
            models.append(arg)
            continue

        model = arg._django_model
        if model not in models:
            models.append(model)

        arg_types.register(model, arg)

    if not models:
        raise TypeError('No model defined for field generator')

    return_args = []
    for model in models:
        output_type = get_type(model, arg_types, types, is_input=False)
        if is_input:
            input_type = get_type(model, arg_types, types, is_input=True)
            return_args.append((model, output_type, input_type))
        else:
            return_args.append((model, output_type))
        if single:
            return return_args[0]
    return return_args

def get_type(model, arg_types, types, is_input):
    type = arg_types.get(model, is_input=is_input)
    if not type and types:
        type = types.get(model, is_input=is_input)
    if not type:
        raise TypeError(f"No type for model '{model._meta.object_name}'")
    return type
