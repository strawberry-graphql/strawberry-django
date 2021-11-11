from strawberry.arguments import UNSET
from ..legacy.mutations.fields import mutations as mutations_legacy
from .fields import DjangoCreateMutation, DjangoUpdateMutation, DjangoDeleteMutation

def mutations(*args, **kwargs):
    return mutations_legacy(*args, **kwargs)

def create(input_type=UNSET, *args, types=None, pre_save=None, post_save=None, permission_classes=[]):
    if args or types:
        args = (input_type,) + args
        return mutations_legacy.create(*args, types=types, pre_save=pre_save, post_save=post_save)
    return DjangoCreateMutation(input_type, permission_classes=permission_classes)

def update(input_type=UNSET, *args, filters=UNSET, types=None, permission_classes=[]):
    if args or types:
        args = (input_type,) + args
        return mutations_legacy.update(*args, types=types)
    return DjangoUpdateMutation(input_type, filters=filters, permission_classes=permission_classes)

def delete(*args, types=None, filters=UNSET, permission_classes=[]):
    if args or types:
        return mutations_legacy.delete(*args, types=types)
    return DjangoDeleteMutation(input_type=None, filters=filters, permission_classes=permission_classes)

mutations.create = create
mutations.update = update
mutations.delete = delete
