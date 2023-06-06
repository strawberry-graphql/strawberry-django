from typing import Any

from strawberry import UNSET

from .fields import DjangoCreateMutation, DjangoDeleteMutation, DjangoUpdateMutation


# FIXME: This needs proper typing
def create(input_type=UNSET, permission_classes=None, **kwargs) -> Any:
    return DjangoCreateMutation(
        input_type,
        permission_classes=permission_classes or [],
        **kwargs,
    )


def update(input_type=UNSET, filters=UNSET, permission_classes=None, **kwargs) -> Any:
    return DjangoUpdateMutation(
        input_type,
        filters=filters,
        permission_classes=permission_classes or [],
        **kwargs,
    )


def delete(filters=UNSET, permission_classes=None, **kwargs) -> Any:
    return DjangoDeleteMutation(
        input_type=None,
        filters=filters,
        permission_classes=permission_classes or [],
        **kwargs,
    )
