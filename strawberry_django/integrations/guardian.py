import contextlib
import dataclasses
from typing import Union, cast

from django.contrib.auth import get_user_model
from django.db import models
from guardian.conf import settings as guardian_settings
from guardian.models.models import GroupObjectPermissionBase, UserObjectPermissionBase
from guardian.utils import get_anonymous_user as _get_anonymous_user
from guardian.utils import get_group_obj_perms_model, get_user_obj_perms_model

from strawberry_django.utils.typing import UserType


@dataclasses.dataclass
class ObjectPermissionModels:
    user: UserObjectPermissionBase
    group: GroupObjectPermissionBase


def get_object_permission_models(
    model: Union[models.Model, type[models.Model]],
) -> ObjectPermissionModels:
    return ObjectPermissionModels(
        user=cast("UserObjectPermissionBase", get_user_obj_perms_model(model)),
        group=cast("GroupObjectPermissionBase", get_group_obj_perms_model(model)),
    )


def get_user_or_anonymous(user: UserType) -> UserType:
    username = guardian_settings.ANONYMOUS_USER_NAME or ""
    if user.is_anonymous and user.get_username() != username:
        with contextlib.suppress(get_user_model().DoesNotExist):
            return cast("UserType", _get_anonymous_user())
    return user
