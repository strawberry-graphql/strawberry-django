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

# Internal helpers to reduce duplication in default_qs_hook
from collections.abc import Iterable

def _group_prefetch_paths(rel_paths: Iterable[str]) -> dict[str, set[str]]:
    grouped: dict[str, set[str]] = {}
    for path in rel_paths or []:
        if not isinstance(path, str) or not path:
            continue
        root, remainder = (path.split("__", 1) + [""])[:2]
        if not root:
            continue
        if remainder:
            grouped.setdefault(root, set()).add(remainder)
        else:
            grouped.setdefault(root, set())
    return grouped


def _ensure_prefetch_cache(obj: Any) -> dict:
    cache = getattr(obj, "_prefetched_objects_cache", None)
    if cache is None or not isinstance(cache, dict):
        cache = {}
        setattr(obj, "_prefetched_objects_cache", cache)
    return cache


def _inject_prefetch_cache(obj: Any, key: str, items: list[Any]) -> None:
    cache = _ensure_prefetch_cache(obj)
    cache[key] = items


def _manual_batch_reverse_fk_assign(
    mdl: type[models.Model],
    root: str,
    instances_for_query: list[Any],
    id_to_original: dict[Any, Any],
) -> tuple[list[Any], type[models.Model]]:
    try:
        related = next(
            ro for ro in mdl._meta.related_objects if ro.get_accessor_name() == root
        )
    except StopIteration:
        return ([], mdl)  # no-op
    root_model = related.related_model
    fk_attname = getattr(related.field, "attname", None)
    if not fk_attname:
        return ([], root_model)
    ids = [obj.pk for obj in instances_for_query]
    if not ids:
        return ([], root_model)
    # Fetch all root related objects and group by foreign key
    root_batch = root_model._default_manager.filter(**{f"{fk_attname}__in": ids})
    grouped_root: dict[int, list] = {}
    for item in root_batch:
        grouped_root.setdefault(getattr(item, fk_attname), []).append(item)
    # Assign first-level cache and aggregate for potential nested batching
    related_instances_all: list = []
    id_set = set(ids)
    for pk in id_set:
        orig = id_to_original.get(pk)
        if orig is None:
            continue
        items = grouped_root.get(pk, [])
        _inject_prefetch_cache(orig, root, items)
        if items:
            related_instances_all.extend(items)
    return (related_instances_all, root_model)


def _manual_nested_batch_single_hop(
    related_instances_all: list[Any],
    root_model: type[models.Model],
    rem: str,
) -> None:
    if not related_instances_all or not rem or "__" in rem:
        return
    try:
        nested_rel = next(
            ro for ro in root_model._meta.related_objects if ro.get_accessor_name() == rem
        )
    except StopIteration:
        return
    nested_model = nested_rel.related_model
    nested_fk = getattr(nested_rel.field, "attname", None)
    if not nested_fk:
        return
    parent_ids = [getattr(it, "pk") for it in related_instances_all]
    if not parent_ids:
        return
    nested_batch = nested_model._default_manager.filter(**{f"{nested_fk}__in": parent_ids})
    # Group nested by parent fk
    nested_grouped: dict[int, list] = {}
    for n in nested_batch:
        nested_grouped.setdefault(getattr(n, nested_fk), []).append(n)
    # Inject into each parent cache
    for parent in related_instances_all:
        _inject_prefetch_cache(parent, rem, nested_grouped.get(parent.pk, []))

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
    # Parent-level postfetch branches: execute once per parent queryset
    if getattr(cfg, "parent_postfetch_branches", None):
        result_list = list(qs)  # type: ignore
        if result_list:
            from collections import defaultdict
            try:
                from django.db.models import prefetch_related_objects
            except Exception:
                prefetch_related_objects = None  # type: ignore
            # For each parent accessor (e.g., 'projects'), ensure it is prefetched across parents
            for accessor, mapping in list(cfg.parent_postfetch_branches.items()):
                # IMPORTANT: Do not trigger a new prefetch here, as the optimizer
                # already attached a Prefetch with a specialized queryset (e.g.,
                # select_subclasses). Re-invoking Django’s generic prefetch would
                # drop those hints and produce base-class instances. Instead, rely
                # on the cache populated by the queryset’s own prefetch.
                # Collect all child instances from parents' prefetched cache
                children_all: list[Any] = []
                for parent in result_list:
                    cache = getattr(parent, "_prefetched_objects_cache", None)
                    if isinstance(cache, dict) and accessor in cache:
                        ch = cache.get(accessor) or []
                        if isinstance(ch, list):
                            children_all.extend(ch)
                if not children_all:
                    # Fallback: touch the accessor managers to populate cache from the
                    # Prefetch attached on the parent queryset (should not add queries
                    # if Django already executed the prefetch during _fetch_all).
                    try:
                        tmp: list[Any] = []
                        for parent in result_list:
                            mgr = getattr(parent, accessor, None)
                            if mgr is None:
                                continue
                            try:
                                items = list(getattr(mgr, "all", lambda: [])())
                            except Exception:
                                items = []
                            if items:
                                tmp.extend(items)
                        if tmp:
                            children_all = tmp
                        else:
                            continue
                    except Exception:
                        continue
                # Do not downcast here to avoid creating new Python instances that
                # would not share identity with those stored in the parent cache.
                # For each subclass model in this branch, batch prefetch requested reverse relations
                for mdl, rel_paths in mapping.items():
                    # Map original child instances by id so we always write caches
                    # on the exact objects held in the parent's prefetched cache.
                    id_to_original = {obj.pk: obj for obj in children_all}
                    # Try to use instances from the parent's cache first
                    instances = [obj for obj in children_all if isinstance(obj, mdl)]
                    instances_for_query = instances
                    if not instances_for_query:
                        # Fallback: some ORMs/managers may have returned base-class
                        # instances. Downcast copies for querying, but keep caches
                        # written on the original instances using id_to_original.
                        try:
                            manager = getattr(type(children_all[0]), "objects", None)
                            get_real = getattr(manager, "get_real_instances", None)
                            if callable(get_real):
                                down = list(get_real(children_all))
                                instances_for_query = [obj for obj in down if isinstance(obj, mdl)]
                        except Exception:
                            pass
                    if not instances_for_query:
                        continue
                    grouped_paths = _group_prefetch_paths(rel_paths)
                    if not grouped_paths:
                        continue
                    # Manual batching to guarantee a single IN(...) query and
                    # avoid subtle behavior differences across managers.
                    for root, remainders in grouped_paths.items():
                        related_instances_all, root_model = _manual_batch_reverse_fk_assign(
                            mdl, root, instances_for_query, id_to_original
                        )
                        if related_instances_all and remainders:
                            for rem in sorted(remainders):
                                _manual_nested_batch_single_hop(related_instances_all, root_model, rem)
            # Clear after executing to avoid leaking
            cfg.parent_postfetch_branches.clear()

    # Child-level postfetch hints (for independent child querysets)
    if getattr(cfg, "postfetch_prefetch", None):
        result_list = list(qs)  # type: ignore
        if result_list:
            from collections import defaultdict
            # Perform a manual batch prefetch and cache injection to handle
            # django-polymorphic downcasting creating new instances, which do not
            # share identity with the ones used during prefetch_related_objects.
            for mdl, rel_paths in cfg.postfetch_prefetch.items():
                # Collect only instances of this subclass
                instances = [obj for obj in result_list if isinstance(obj, mdl)]
                if not instances:
                    continue
                id_to_instance = {obj.pk: obj for obj in instances}
                grouped_paths = _group_prefetch_paths(rel_paths)
                for root, remainders in grouped_paths.items():
                    # Prefer delegating to Django's prefetch machinery from the subclass
                    # instances themselves, as these are already downcasted.
                    try:
                        # Build nested paths starting at the subclass instances
                        nested = [f"{root}__{r}" for r in sorted(remainders)] if remainders else []
                        prefetch_related_objects(instances, root, *nested)
                    except Exception:
                        # Fallback: manual batch for the root only (reverse FK)
                        related_instances_all, root_model = _manual_batch_reverse_fk_assign(
                            mdl, root, instances, id_to_instance
                        )
                        # Manual nested batching for single-segment remainders (e.g., 'details')
                        if related_instances_all and remainders:
                            for rem in sorted(remainders):
                                if "__" in rem:
                                    continue
                                _manual_nested_batch_single_hop(related_instances_all, root_model, rem)
                        # For any remaining deeper paths, try Django prefetch starting at the batched roots
                        deeper = [r for r in remainders if "__" in r]
                        if deeper:
                            try:
                                prefetch_related_objects(related_instances_all, *sorted(deeper))
                            except Exception:
                                pass
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
