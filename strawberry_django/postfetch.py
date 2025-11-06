from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any, cast

from django.core.exceptions import FieldError
from django.db import models
from django.db.utils import DatabaseError

if TYPE_CHECKING:
    from collections.abc import Iterable

    from django.db.models.query import QuerySet

    from .queryset import StrawberryDjangoQuerySetConfig

# Number of parts returned by `path.split("__", 1)` when a remainder exists
_SPLIT_WITH_REMAINDER = 2


def _group_prefetch_paths(rel_paths: Iterable[str]) -> dict[str, set[str]]:
    grouped: dict[str, set[str]] = {}
    for path in rel_paths or []:
        if not isinstance(path, str) or not path:
            continue
        root, remainder = [*path.split("__", 1), ""][:2]
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
        obj._prefetched_objects_cache = cache
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
            ro
            for ro in root_model._meta.related_objects
            if ro.get_accessor_name() == rem
        )
    except StopIteration:
        return

    nested_model = nested_rel.related_model
    nested_fk = getattr(nested_rel.field, "attname", None)
    if not nested_fk:
        return

    parent_ids = [it.pk for it in related_instances_all]
    if not parent_ids:
        return

    nested_batch = nested_model._default_manager.filter(**{
        f"{nested_fk}__in": parent_ids
    })

    # Group nested by parent fk
    nested_grouped: dict[int, list] = {}
    for n in nested_batch:
        nested_grouped.setdefault(getattr(n, nested_fk), []).append(n)

    # Inject into each parent cache
    for parent in related_instances_all:
        _inject_prefetch_cache(parent, rem, nested_grouped.get(parent.pk, []))


def __group_by_type(objs: list[Any]) -> dict[type, list[Any]]:
    grouped: dict[type, list[Any]] = {}
    for obj in objs:
        grouped.setdefault(type(obj), []).append(obj)
    return grouped


def __prefetch_child_root(
    instances: list[Any],
    mdl: type[models.Model],
    root: str,
    remainders: set[str],
    id_to_instance: dict[Any, Any],
) -> None:
    """Prefetch a single root for child-level postfetch on given instances.

    Tries `prefetch_related_objects` first; falls back to manual reverse-FK batching
    and optional single-hop nested prefetch when required.
    """
    try:
        from django.db.models import prefetch_related_objects
    except ImportError:  # pragma: no cover
        return

    nested = [f"{root}__{r}" for r in sorted(remainders)] if remainders else []
    try:
        prefetch_related_objects(instances, root, *nested)
    except (FieldError, DatabaseError, AttributeError, ValueError):
        pass
    else:
        return

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
        with contextlib.suppress(Exception):
            prefetch_related_objects(related_instances_all, *sorted(deeper))


def __postfetch_child_for_instances(
    instances_by_model: dict[type[models.Model], list[Any]],
    rel_paths_by_model: dict[type[models.Model], set[str]],
) -> None:
    """Prefetch child-level relations for given instances per model.

    Best-effort: ignores failures; no queryset evaluation here.
    """
    try:
        from django.db.models import prefetch_related_objects
    except ImportError:  # pragma: no cover
        return

    for mdl, rel_paths in rel_paths_by_model.items():
        instances = instances_by_model.get(mdl) or []
        if not instances:
            continue
        grouped = _group_prefetch_paths(rel_paths)
        for root, remainders in grouped.items():
            nested = [f"{root}__{r}" for r in sorted(remainders)] if remainders else []
            with contextlib.suppress(Exception):
                prefetch_related_objects(instances, root, *nested)


def __postfetch_parent_for_parents(
    parents_by_model: dict[type[models.Model], list[Any]],
    branches: dict[str, dict[type[models.Model], set[str]]],
) -> None:
    """Batch reverse-FK assignment for page/query parents and prefetch nested remainders.

    This operates only on provided parent instances. Best-effort semantics.
    """
    try:
        from django.db.models import prefetch_related_objects
    except ImportError:  # pragma: no cover
        prefetch_related_objects = None

    for accessor, mapping in list(branches.items()):
        # Union all remainders from mapping values
        remainders_all: set[str] = set()
        for rel_paths in mapping.values():
            for path in rel_paths or []:
                if not isinstance(path, str) or not path:
                    continue
                parts = path.split("__", 1)
                if len(parts) == _SPLIT_WITH_REMAINDER:
                    remainders_all.add(parts[1])

        for parent_model, parents in parents_by_model.items():
            # Find reverse relation on this concrete model by accessor name
            rel = next(
                (
                    ro
                    for ro in parent_model._meta.related_objects
                    if ro.get_accessor_name() == accessor
                ),
                None,
            )
            if rel is None:
                continue

            child_model = rel.related_model
            fk_attname = getattr(rel.field, "attname", None)
            if not fk_attname:
                continue

            parent_ids = [getattr(p, "pk", None) for p in parents]
            parent_ids = [pid for pid in parent_ids if pid is not None]
            if not parent_ids:
                continue

            try:
                children = list(
                    child_model._default_manager.filter(**{
                        f"{fk_attname}__in": parent_ids
                    })
                )
            except (FieldError, DatabaseError):
                children = []

            grouped_children: dict[int, list] = {}
            for ch in children:
                try:
                    key = getattr(ch, fk_attname)
                except AttributeError:
                    continue
                grouped_children.setdefault(key, []).append(ch)

            # Inject into each parent's prefetched cache
            for p in parents:
                pid = getattr(p, "pk", None)
                if not isinstance(pid, int):
                    continue
                items = grouped_children.get(pid, [])
                cache = getattr(p, "_prefetched_objects_cache", None)
                if not isinstance(cache, dict):
                    cache = {}
                    p._prefetched_objects_cache = cache
                cache[accessor] = items

            # If nested remainders exist, prefetch them on the children collection
            if children and remainders_all and prefetch_related_objects:
                single_hop = [r for r in remainders_all if "__" not in r]
                deeper = [r for r in remainders_all if "__" in r]
                with contextlib.suppress(Exception):
                    if single_hop:
                        prefetch_related_objects(children, *sorted(single_hop))
                    if deeper:
                        prefetch_related_objects(children, *sorted(deeper))


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
    except ImportError:  # pragma: no cover
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
                    tmp: list[Any] = []
                    with contextlib.suppress(Exception):
                        for parent in result_list:
                            mgr = getattr(parent, accessor, None)
                            if mgr is None:
                                continue
                            items: list[Any] = []
                            with contextlib.suppress(Exception):
                                items = list(getattr(mgr, "all", list)())
                            if items:
                                tmp.extend(items)
                    if tmp:
                        children_all = tmp
                    else:
                        continue
                # Batch prefetch per subclass
                for mdl, rel_paths in mapping.items():
                    id_to_original = {obj.pk: obj for obj in children_all}
                    instances = [obj for obj in children_all if isinstance(obj, mdl)]
                    instances_for_query = instances
                    if not instances_for_query:
                        # Try downcasting copies for querying (best-effort)
                        with contextlib.suppress(Exception):
                            manager = getattr(type(children_all[0]), "objects", None)
                            get_real = getattr(manager, "get_real_instances", None)
                            if callable(get_real):
                                down = list(cast("Iterable[Any]", get_real(children_all)))
                                instances_for_query = [
                                    obj for obj in down if isinstance(obj, mdl)
                                ]
                    if not instances_for_query:
                        continue
                    grouped_paths = _group_prefetch_paths(rel_paths)
                    if not grouped_paths:
                        continue
                    for root, remainders in grouped_paths.items():
                        related_instances_all, root_model = (
                            _manual_batch_reverse_fk_assign(
                                mdl, root, instances_for_query, id_to_original
                            )
                        )
                        if related_instances_all and remainders:
                            for rem in sorted(remainders):
                                _manual_nested_batch_single_hop(
                                    related_instances_all, root_model, rem
                                )
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
                    __prefetch_child_root(instances, mdl, root, remainders, id_to_instance)
        cfg.postfetch_prefetch.clear()


def apply_page_postfetch(
    edge_nodes: list[Any],
    cfg: StrawberryDjangoQuerySetConfig,
    *,
    clear_parent_branches: bool = True,
    clear_child_prefetch: bool = False,
) -> None:
    """Apply post-fetch optimizations on a page (list of nodes).

    This is a page-aware counterpart of `apply_postfetch(qs)` that operates only on
    the current page's nodes. It never evaluates the original QuerySet; callers
    must pass the already materialized edge nodes (connection page).

    Behavior parity with the inlined logic previously placed in
    DjangoListConnection.resolve_connection:
    - Executes child-level `postfetch_prefetch` using `prefetch_related_objects` on
      the subset of instances of each model present in the page.
    - Executes parent-level `parent_postfetch_branches` by batching reverse-FK
      assignments to fill parent caches and optionally prefetch nested remainders.
    - Clears `parent_postfetch_branches` by default to avoid repeated work.
      Does NOT clear `postfetch_prefetch` by default.
    """
    if not edge_nodes:
        return

    # Parent-level first (consistent ordering), then child-level
    if getattr(cfg, "parent_postfetch_branches", None):
        with contextlib.suppress(Exception):
            parents_by_model = __group_by_type(edge_nodes)
            __postfetch_parent_for_parents(
                parents_by_model, cfg.parent_postfetch_branches
            )
            if clear_parent_branches:
                cfg.parent_postfetch_branches.clear()

    if getattr(cfg, "postfetch_prefetch", None):
        # Build instances_by_model only for models that have rel paths in cfg (best-effort)
        with contextlib.suppress(Exception):
            instances_by_model: dict[type[models.Model], list[Any]] = {}
            for mdl in cfg.postfetch_prefetch:
                with contextlib.suppress(Exception):
                    instances_by_model[mdl] = [n for n in edge_nodes if isinstance(n, mdl)]
                if mdl not in instances_by_model:
                    instances_by_model[mdl] = []
            __postfetch_child_for_instances(instances_by_model, cfg.postfetch_prefetch)
            if clear_child_prefetch:
                cfg.postfetch_prefetch.clear()
