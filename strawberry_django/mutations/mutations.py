from strawberry.arguments import UNSET
from ..legacy.mutations.fields import mutations as mutations_legacy
from .fields import DjangoCreateMutation, DjangoUpdateMutation, DjangoDeleteMutation

def mutations(*args, **kwargs):
    return mutations_legacy(*args, **kwargs)

def create(input_type=UNSET, *args, types=None, pre_save=None, post_save=None):
    if args or types:
        args = (input_type,) + args
        return mutations_legacy.create(*args, types=types, pre_save=pre_save, post_save=post_save)
    return DjangoCreateMutation(input_type)

def update(input_type=UNSET, *args, filters=UNSET, types=None):
    if args or types:
        args = (input_type,) + args
        return mutations_legacy.update(*args, types=types)
    return DjangoUpdateMutation(input_type, filters=filters)

def delete(*args, types=None, filters=UNSET):
    if args or types:
        return mutations_legacy.delete(*args, types=types)
    return DjangoDeleteMutation(input_type=None, filters=filters)

mutations.create = create
mutations.update = update
mutations.delete = delete
