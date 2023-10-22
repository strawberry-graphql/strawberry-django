import functools
from typing import TYPE_CHECKING, List, Optional, Set, Type, TypeVar, cast

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Exists, F, Model, Q, QuerySet
from django.db.models.functions import Cast
from strawberry.utils.inspect import in_async_context

from .typing import TypeOrIterable, UserType

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser
    from django.contrib.contenttypes.models import ContentType
    from guardian.managers import (
        GroupObjectPermissionManager,
        UserObjectPermissionManager,
    )

_Q = TypeVar("_Q", bound=QuerySet)


def _filter(
    qs: _Q,
    perms: List[str],
    *,
    lookup: str = "",
    model: Type[Model],
    any_perm: bool = True,
    ctype: Optional["ContentType"] = None,
) -> _Q:
    lookup = lookup and f"{lookup}__"
    ctype_attr = f"{lookup}content_type"

    if ctype is not None:
        q = Q(**{ctype_attr: ctype})
    else:
        meta = model._meta
        q = Q(
            **{
                f"{ctype_attr}__app_label": meta.app_label,
                f"{ctype_attr}__model": meta.model_name,
            },
        )

    if len(perms) == 1:
        q &= Q(**{f"{lookup}codename": perms[0]})
    elif any_perm:
        q &= Q(**{f"{lookup}codename__in": perms})
    else:
        q = functools.reduce(
            lambda acu, p: acu & Q(**{f"{lookup}codename": p}),
            perms,
            q,
        )

    return qs.filter(q)


def filter_for_user_q(
    qs: QuerySet,
    user: UserType,
    perms: TypeOrIterable[str],
    *,
    any_perm: bool = True,
    with_groups: bool = True,
    with_superuser: bool = False,
):
    if with_superuser and user.is_active and getattr(user, "is_superuser", False):
        return qs

    if user.is_anonymous:
        return qs.none()

    groups_field = None
    try:
        groups_field = cast("AbstractUser", user)._meta.get_field("groups")
    except FieldDoesNotExist:
        with_groups = False

    if isinstance(perms, str):
        perms = [perms]

    model = cast(Type[Model], qs.model)
    if model._meta.concrete_model:
        model = model._meta.concrete_model

    try:
        from django.contrib.contenttypes.models import ContentType
    except (ImportError, RuntimeError):  # pragma: no cover
        ctype = None
    else:
        try:
            # We don't want to query the database here because this might not be async
            # safe. Try to retrieve the ContentType from cache. If it is not there, we
            # will query it through the queryset
            meta = model._meta
            ctype = cast(
                ContentType,
                ContentType.objects._get_from_cache(meta),  # type: ignore
            )
        except KeyError:  # pragma:nocover
            # If we are not running async, retrieve it
            ctype = (
                ContentType.objects.get_for_model(model, for_concrete_model=False)
                if not in_async_context()
                else None
            )

    app_labels = set()
    perms_list = []
    for p in perms:
        parts = p.split(".")
        if len(parts) > 1:
            app_labels.add(parts[0])
        perms_list.append(parts[-1])

    if len(app_labels) == 1 and ctype is not None:
        app_label = app_labels.pop()
        if app_label != ctype.app_label:  # pragma:nocover
            raise ValueError(
                f"Given perms must have same app label ({app_label!r} !="
                f" {ctype.app_label!r})",
            )
    elif len(app_labels) > 1:  # pragma:nocover
        raise ValueError(f"Cannot mix app_labels ({app_labels!r})")

    # Small optimization if the user's permissions are cached
    perm_cache = getattr(user, "_perm_cache", None)
    if perm_cache is not None:  # pragma:nocover
        f = any if any_perm else all
        user_perms: Set[str] = {p.codename for p in perm_cache}
        if f(p in user_perms for p in perms_list):
            return qs

    q = Q()
    if hasattr(user, "user_permissions"):
        q |= Q(
            Exists(
                _filter(
                    cast("AbstractUser", user).user_permissions,
                    perms_list,
                    model=model,
                    ctype=ctype,
                ),
            ),
        )
    if with_groups:
        q |= Q(
            Exists(
                _filter(
                    cast("AbstractUser", user).groups,
                    perms_list,
                    lookup="permissions",
                    model=model,
                    ctype=ctype,
                ),
            ),
        )

    try:
        from strawberry_django.integrations.guardian import (
            get_object_permission_models,
        )
    except (ImportError, RuntimeError):  # pragma: no cover
        pass
    else:
        perm_models = get_object_permission_models(qs.model)

        user_model = perm_models.user
        user_qs = _filter(
            user_model.objects.filter(user=user),
            perms_list,
            lookup="permission",
            model=model,
            ctype=ctype,
        )
        if cast("UserObjectPermissionManager", user_model.objects).is_generic():
            user_qs = user_qs.filter(content_type=F("permission__content_type"))
        else:
            user_qs = user_qs.annotate(object_pk=F("content_object"))

        obj_qs = user_qs.values_list(
            Cast("object_pk", cast(str, model._meta.pk)),
            flat=True,
        ).distinct()

        if with_groups:
            assert groups_field is not None
            group_model = perm_models.group
            user_key = f"group__{groups_field.related_query_name()}"  # type: ignore
            group_qs = _filter(
                group_model.objects.filter(**{user_key: user}),
                perms_list,
                lookup="permission",
                model=model,
                ctype=ctype,
            )
            if cast("GroupObjectPermissionManager", group_model.objects).is_generic():
                group_qs = group_qs.filter(content_type=F("permission__content_type"))
            else:
                group_qs = group_qs.annotate(object_pk=F("content_object"))

            obj_qs = obj_qs.union(
                group_qs.values_list(
                    Cast("object_pk", cast(str, model._meta.pk)),
                    flat=True,
                ).distinct(),
            )

        q |= Q(pk__in=obj_qs)

    return q


def filter_for_user(
    qs: QuerySet,
    user: UserType,
    perms: TypeOrIterable[str],
    *,
    any_perm: bool = True,
    with_groups: bool = True,
    with_superuser: bool = False,
):
    return qs & qs.filter(
        filter_for_user_q(
            qs,
            user,
            perms,
            any_perm=any_perm,
            with_groups=with_groups,
            with_superuser=with_superuser,
        ),
    )
