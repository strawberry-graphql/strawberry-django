from __future__ import annotations

import contextvars
import functools
import inspect
from typing import TYPE_CHECKING, Any, TypeVar, overload

from asgiref.sync import sync_to_async
from django.db import models
from django.db.models.fields.files import FileDescriptor
from django.db.models.manager import BaseManager
from strawberry.utils.inspect import in_async_context
from typing_extensions import ParamSpec

if TYPE_CHECKING:
    from collections.abc import Callable

    from graphql.pyutils import AwaitableOrValue

_SENTINEL = object()
_R = TypeVar("_R")
_P = ParamSpec("_P")
_M = TypeVar("_M", bound=models.Model)

resolving_async: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "resolving-async",
    default=False,
)


def default_qs_hook(qs: models.QuerySet[_M]) -> models.QuerySet[_M]:
    if isinstance(qs, list):
        # return sliced queryset as-is
        return qs

    # FIXME: We probably won't need this anymore when we can use graphql-core 3.3.0+
    # as its `complete_list_value` gives a preference to async iteration it if is
    # provided by the object.
    # This is what QuerySet does internally to fetch results.
    # After this, iterating over the queryset should be async safe
    if qs._result_cache is None:  # type: ignore
        qs._fetch_all()  # type: ignore

    # Post-fetch optimization: prefetch subtype-specific reverse relations for
    # django-polymorphic results. We store hints in the queryset config.
    try:
        from strawberry_django.queryset import get_queryset_config
        from django.db.models import prefetch_related_objects
    except Exception:  # pragma: no cover
        return qs

    cfg = get_queryset_config(qs)
    if getattr(cfg, "postfetch_prefetch", None):
        result_list = list(qs)  # type: ignore
        if result_list:
            from collections import defaultdict
            # Perform a manual batch prefetch and cache injection to handle
            # django-polymorphic downcasting creating new instances, which do not
            # share identity with the ones used during prefetch_related_objects.
            for mdl, rels in cfg.postfetch_prefetch.items():
                # Collect only instances of this subclass
                instances = [obj for obj in result_list if isinstance(obj, mdl)]
                if not instances:
                    continue
                id_to_instance = {obj.pk: obj for obj in instances}
                for rel in rels:
                    # Find the related object descriptor on the subclass
                    try:
                        related = next(
                            ro for ro in mdl._meta.related_objects
                            if ro.get_accessor_name() == rel
                        )
                    except StopIteration:
                        # Unknown relation name; skip
                        continue
                    note_model = related.related_model
                    fk_attname = related.field.attname
                    ids = [obj.pk for obj in instances]
                    if not ids:
                        continue
                    # Fetch all related objects in a single query and group by fk
                    batch = note_model._default_manager.filter(**{f"{fk_attname}__in": ids})
                    grouped: dict[int, list] = defaultdict(list)
                    for item in batch:
                        grouped[getattr(item, fk_attname)].append(item)
                    # Assign into each instance's prefetched cache under the accessor name
                    for pk, obj in id_to_instance.items():
                        cache = getattr(obj, "_prefetched_objects_cache", None)
                        if cache is None:
                            cache = {}
                            setattr(obj, "_prefetched_objects_cache", cache)
                        cache[rel] = grouped.get(pk, [])
        # Clear hints to avoid leaking into subsequent, unrelated queries
        cfg.postfetch_prefetch.clear()

    return qs


@overload
def django_resolver(
    f: Callable[_P, _R],
    *,
    qs_hook: Callable[[models.QuerySet[_M]], Any] | None = default_qs_hook,
    except_as_none: tuple[type[Exception], ...] | None = None,
) -> Callable[_P, AwaitableOrValue[_R]]: ...


@overload
def django_resolver(
    *,
    qs_hook: Callable[[models.QuerySet[_M]], Any] | None = default_qs_hook,
    except_as_none: tuple[type[Exception], ...] | None = None,
) -> Callable[[Callable[_P, _R]], Callable[_P, AwaitableOrValue[_R]]]: ...


def django_resolver(
    f=None,
    *,
    qs_hook: Callable[[models.QuerySet[_M]], Any] | None = default_qs_hook,
    except_as_none: tuple[type[Exception], ...] | None = None,
):
    """Django resolver for handling both sync and async.

    This decorator is used to make sure that resolver is always called from
    sync context.  sync_to_async helper in used if function is called from
    async context. This is useful especially with Django ORM, which does not
    support async. Coroutines are not wrapped.
    """

    def wrapper(resolver):
        if inspect.iscoroutinefunction(resolver) or inspect.isasyncgenfunction(
            resolver,
        ):
            return resolver

        def sync_resolver(*args, **kwargs):
            try:
                retval = resolver(*args, **kwargs)

                if callable(retval):
                    retval = retval()

                if isinstance(retval, BaseManager):
                    retval = retval.all()

                if qs_hook is not None and isinstance(retval, models.QuerySet):
                    retval = qs_hook(retval)
            except Exception as e:
                if except_as_none is not None and isinstance(e, except_as_none):
                    return None

                raise

            return retval

        @sync_to_async
        def async_resolver(*args, **kwargs):
            token = resolving_async.set(True)
            try:
                return sync_resolver(*args, **kwargs)
            finally:
                resolving_async.reset(token)

        @functools.wraps(resolver)
        def inner_wrapper(*args, **kwargs):
            f = (
                async_resolver
                if in_async_context() and not resolving_async.get()
                else sync_resolver
            )
            return f(*args, **kwargs)

        return inner_wrapper

    if f is not None:
        return wrapper(f)

    return wrapper


@django_resolver(qs_hook=None)
def django_fetch(qs: models.QuerySet[_M]) -> models.QuerySet[_M]:
    return default_qs_hook(qs)


@overload
def django_getattr(
    obj: Any,
    name: str,
    *,
    qs_hook: Callable[[models.QuerySet[_M]], Any] = default_qs_hook,
    except_as_none: tuple[type[Exception], ...] | None = None,
    empty_file_descriptor_as_null: bool = False,
) -> AwaitableOrValue[Any]: ...


@overload
def django_getattr(
    obj: Any,
    name: str,
    default: Any,
    *,
    qs_hook: Callable[[models.QuerySet[_M]], Any] = default_qs_hook,
    except_as_none: tuple[type[Exception], ...] | None = None,
    empty_file_descriptor_as_null: bool = False,
) -> AwaitableOrValue[Any]: ...


def django_getattr(
    obj: Any,
    name: str,
    default: Any = _SENTINEL,
    *,
    qs_hook: Callable[[models.QuerySet[_M]], Any] = default_qs_hook,
    except_as_none: tuple[type[Exception], ...] | None = None,
    empty_file_descriptor_as_null: bool = False,
):
    return django_resolver(
        _django_getattr,
        qs_hook=qs_hook,
        except_as_none=except_as_none,
    )(
        obj,
        name,
        default,
        empty_file_descriptor_as_null=empty_file_descriptor_as_null,
    )


def _django_getattr(
    obj: Any,
    name: str,
    default: Any = _SENTINEL,
    *,
    empty_file_descriptor_as_null: bool = False,
):
    args = (default,) if default is not _SENTINEL else ()
    result = getattr(obj, name, *args)
    if empty_file_descriptor_as_null and isinstance(result, FileDescriptor):
        result = None
    return result


def resolve_base_manager(manager: BaseManager) -> Any:
    if (result_instance := getattr(manager, "instance", None)) is not None:
        prefetched_cache = getattr(result_instance, "_prefetched_objects_cache", {})
        # Both ManyRelatedManager and RelatedManager are defined inside functions, which
        # prevents us from importing and checking isinstance on them directly.
        try:
            # ManyRelatedManager
            return prefetched_cache[manager.prefetch_cache_name]  # type: ignore
        except (AttributeError, KeyError):
            try:
                # RelatedManager
                result_field = manager.field  # type: ignore
                cache_name = (
                    # 5.1+ uses "cache_name" instead of "get_cache_name()
                    getattr(result_field.remote_field, "cache_name", None)
                    or result_field.remote_field.get_cache_name()
                )
                return prefetched_cache[cache_name]
            except (AttributeError, KeyError):
                pass

    return manager.all()
