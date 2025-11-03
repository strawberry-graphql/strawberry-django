from __future__ import annotations

from collections.abc import Iterable
from typing import Any, TYPE_CHECKING

from django.db import models

if TYPE_CHECKING:
    from django.db.models.query import QuerySet


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


def apply_postfetch(qs: QuerySet[Any]) -> None:
    """Apply post-fetch optimizations on a QuerySet, if hints are present.

    This function materializes the queryset when needed and performs both
    parent-level and child-level postfetch prefetching and cache injection.
    It mutates Django's internal prefetched caches on involved instances and
    clears the consumed hints from the queryset config. It does not return a
    new QuerySet; callers can keep using the original `qs`.
    """
    try:
        from strawberry_django.queryset import get_queryset_config
        from django.db.models import prefetch_related_objects
    except Exception:  # pragma: no cover
        return

    cfg = get_queryset_config(qs)

    # Parent-level postfetch branches
    if getattr(cfg, "parent_postfetch_branches", None):
        result_list = list(qs)  # force evaluation
        if result_list:
            for accessor, mapping in list(cfg.parent_postfetch_branches.items()):
                # Collect children from parents' prefetched cache
                children_all: list[Any] = []
                for parent in result_list:
                    cache = getattr(parent, "_prefetched_objects_cache", None)
                    if isinstance(cache, dict) and accessor in cache:
                        ch = cache.get(accessor) or []
                        if isinstance(ch, list):
                            children_all.extend(ch)
                if not children_all:
                    # Fallback: touch managers to populate cache, leveraging Prefetch attached previously
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
                # Batch prefetch per subclass
                for mdl, rel_paths in mapping.items():
                    id_to_original = {obj.pk: obj for obj in children_all}
                    instances = [obj for obj in children_all if isinstance(obj, mdl)]
                    instances_for_query = instances
                    if not instances_for_query:
                        # Try downcasting copies for querying
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
                    for root, remainders in grouped_paths.items():
                        related_instances_all, root_model = _manual_batch_reverse_fk_assign(
                            mdl, root, instances_for_query, id_to_original
                        )
                        if related_instances_all and remainders:
                            for rem in sorted(remainders):
                                _manual_nested_batch_single_hop(related_instances_all, root_model, rem)
            cfg.parent_postfetch_branches.clear()

    # Child-level postfetch hints
    if getattr(cfg, "postfetch_prefetch", None):
        result_list = list(qs)  # force evaluation
        if result_list:
            for mdl, rel_paths in cfg.postfetch_prefetch.items():
                instances = [obj for obj in result_list if isinstance(obj, mdl)]
                if not instances:
                    continue
                id_to_instance = {obj.pk: obj for obj in instances}
                grouped_paths = _group_prefetch_paths(rel_paths)
                for root, remainders in grouped_paths.items():
                    try:
                        nested = [f"{root}__{r}" for r in sorted(remainders)] if remainders else []
                        prefetch_related_objects(instances, root, *nested)
                    except Exception:
                        related_instances_all, root_model = _manual_batch_reverse_fk_assign(
                            mdl, root, instances, id_to_instance
                        )
                        if related_instances_all and remainders:
                            for rem in sorted(remainders):
                                if "__" in rem:
                                    continue
                                _manual_nested_batch_single_hop(related_instances_all, root_model, rem)
                        deeper = [r for r in remainders if "__" in r]
                        if deeper:
                            try:
                                prefetch_related_objects(related_instances_all, *sorted(deeper))
                            except Exception:
                                pass
        cfg.postfetch_prefetch.clear()
