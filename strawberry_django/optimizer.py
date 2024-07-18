from __future__ import annotations

import contextlib
import contextvars
import copy
import dataclasses
import itertools
from collections import defaultdict
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generator,
    Type,
    TypeVar,
    cast,
)

from django.db import models
from django.db.models import Prefetch
from django.db.models.constants import LOOKUP_SEP
from django.db.models.expressions import BaseExpression, Combinable
from django.db.models.fields.reverse_related import (
    ManyToManyRel,
    ManyToOneRel,
    OneToOneRel,
)
from django.db.models.manager import BaseManager
from django.db.models.query import QuerySet
from graphql import (
    FieldNode,
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLOutputType,
    GraphQLWrappingType,
    get_argument_values,
)
from graphql.execution.collect_fields import collect_sub_fields
from graphql.language.ast import OperationType
from graphql.type.definition import GraphQLResolveInfo, get_named_type
from strawberry import relay
from strawberry.extensions import SchemaExtension
from strawberry.relay.utils import SliceMetadata
from strawberry.schema.schema import Schema
from strawberry.schema.schema_converter import get_arguments
from strawberry.types import get_object_definition
from strawberry.types.base import StrawberryContainer
from strawberry.types.info import Info
from strawberry.types.lazy_type import LazyType
from strawberry.types.object_type import StrawberryObjectDefinition
from typing_extensions import assert_never, assert_type

from strawberry_django.fields.types import resolve_model_field_name
from strawberry_django.pagination import apply_window_pagination
from strawberry_django.queryset import get_queryset_config, run_type_get_queryset
from strawberry_django.relay import ListConnectionWithTotalCount
from strawberry_django.resolvers import django_fetch

from .descriptors import ModelProperty
from .utils.inspect import (
    PrefetchInspector,
    get_model_field,
    get_possible_type_definitions,
)
from .utils.typing import (
    AnnotateCallable,
    AnnotateType,
    PrefetchCallable,
    PrefetchType,
    TypeOrMapping,
    TypeOrSequence,
    WithStrawberryDjangoObjectDefinition,
    get_django_definition,
    has_django_definition,
)

if TYPE_CHECKING:
    from strawberry.types.field import StrawberryField  # noqa: I001
    from strawberry.types.execution import ExecutionContext
    from strawberry.utils.await_maybe import AwaitableOrValue
    from django.contrib.contenttypes.fields import GenericRelation


__all__ = [
    "DjangoOptimizerExtension",
    "OptimizerConfig",
    "OptimizerStore",
    "PrefetchType",
    "optimize",
]

NESTED_PREFETCH_MARK = "_strawberry_nested_prefetch_optimized"
_M = TypeVar("_M", bound=models.Model)

_sentinel = object()
_annotate_placeholder = "__annotated_placeholder__"
_interfaces: defaultdict[
    Schema,
    dict[StrawberryObjectDefinition, list[StrawberryObjectDefinition]],
] = defaultdict(
    dict,
)


@dataclasses.dataclass
class OptimizerConfig:
    """Django optimization configuration.

    Attributes
    ----------
        enable_only:
            Enable `QuerySet.only` optimizations
        enable_select_related:
            Enable `QuerySet.select_related` optimizations
        enable_prefetch_related:
            Enable `QuerySet.prefetch_related` optimizations
        enable_annotate:
            Enable `QuerySet.annotate` optimizations
        enable_nested_relations_prefetch:
            Enable prefetch of nested relations optimizations.
        prefetch_custom_queryset:
            Use custom instead of _base_manager for prefetch querysets

    """

    enable_only: bool = dataclasses.field(default=True)
    enable_select_related: bool = dataclasses.field(default=True)
    enable_prefetch_related: bool = dataclasses.field(default=True)
    enable_annotate: bool = dataclasses.field(default=True)
    enable_nested_relations_prefetch: bool = dataclasses.field(default=True)
    prefetch_custom_queryset: bool = dataclasses.field(default=False)


@dataclasses.dataclass
class OptimizerStore:
    """Django optimization store.

    Attributes
    ----------
        only:
            Set of values to optimize using `QuerySet.only`
        selected:
            Set of values to optimize using `QuerySet.select_related`
        prefetch_related:
            Set of values to optimize using `QuerySet.prefetch_related`
        annotate:
            Dict of values to use in `QuerySet.annotate`

    """

    only: list[str] = dataclasses.field(default_factory=list)
    select_related: list[str] = dataclasses.field(default_factory=list)
    prefetch_related: list[PrefetchType] = dataclasses.field(default_factory=list)
    annotate: dict[str, AnnotateType] = dataclasses.field(default_factory=dict)

    def __bool__(self):
        return any(
            [self.only, self.select_related, self.prefetch_related, self.annotate],
        )

    def __ior__(self, other: OptimizerStore):
        self.only.extend(other.only)
        self.select_related.extend(other.select_related)
        self.prefetch_related.extend(other.prefetch_related)
        self.annotate.update(other.annotate)
        return self

    def __or__(self, other: OptimizerStore):
        new = self.copy()
        new |= other
        return new

    def copy(self):
        """Create a shallow copy of the store."""
        return self.__class__(
            only=self.only[:],
            select_related=self.select_related[:],
            prefetch_related=self.prefetch_related[:],
            annotate=self.annotate.copy(),
        )

    @classmethod
    def with_hints(
        cls,
        *,
        only: TypeOrSequence[str] | None = None,
        select_related: TypeOrSequence[str] | None = None,
        prefetch_related: TypeOrSequence[PrefetchType] | None = None,
        annotate: TypeOrMapping[AnnotateType] | None = None,
    ):
        """Create a new store with the given hints."""
        return cls(
            only=[only] if isinstance(only, str) else list(only or []),
            select_related=(
                [select_related]
                if isinstance(select_related, str)
                else list(select_related or [])
            ),
            prefetch_related=(
                [prefetch_related]
                if isinstance(prefetch_related, (str, Prefetch, Callable))
                else list(prefetch_related or [])
            ),
            annotate=(
                # placeholder here,
                # because field name is evaluated later on .annotate call:
                {_annotate_placeholder: annotate}
                if isinstance(annotate, (BaseExpression, Combinable, Callable))
                else dict(annotate or {})
            ),
        )

    def with_prefix(self, prefix: str, *, info: GraphQLResolveInfo):
        """Create a copy of this store with the given prefix.

        This is useful when we need to apply the same store to a nested field.
        `prefix` will be prepended to all fields in the store.
        """
        prefetch_related = []
        for p in self.prefetch_related:
            if isinstance(p, Callable):
                assert_type(p, PrefetchCallable)
                p = p(info)  # noqa: PLW2901

            if isinstance(p, str):
                prefetch_related.append(f"{prefix}{LOOKUP_SEP}{p}")
            elif isinstance(p, Prefetch):
                # add_prefix modifies the field's prefetch object, so we copy it before
                p_copy = copy.copy(p)
                p_copy.add_prefix(prefix)
                prefetch_related.append(p_copy)
            else:  # pragma:nocover
                assert_never(p)

        annotate = {}
        for k, v in self.annotate.items():
            if isinstance(v, Callable):
                assert_type(v, AnnotateCallable)
                v = v(info)  # noqa: PLW2901
            annotate[f"{prefix}{LOOKUP_SEP}{k}"] = v

        return self.__class__(
            only=[f"{prefix}{LOOKUP_SEP}{i}" for i in self.only],
            select_related=[f"{prefix}{LOOKUP_SEP}{i}" for i in self.select_related],
            prefetch_related=prefetch_related,
            annotate=annotate,
        )

    def apply(
        self,
        qs: QuerySet[_M],
        *,
        info: GraphQLResolveInfo,
        config: OptimizerConfig | None = None,
    ) -> QuerySet[_M]:
        """Apply this store optimizations to the given queryset."""
        config = config or OptimizerConfig()

        qs = self._apply_prefetch_related(
            qs,
            info=info,
            config=config,
        )
        qs, extra_only_set = self._apply_select_related(
            qs,
            info=info,
            config=config,
        )
        qs = self._apply_only(
            qs,
            info=info,
            config=config,
            extra_only_set=extra_only_set,
        )
        qs = self._apply_annotate(
            qs,
            info=info,
            config=config,
        )

        return qs  # noqa: RET504

    def _apply_prefetch_related(
        self,
        qs: QuerySet[_M],
        *,
        info: GraphQLResolveInfo,
        config: OptimizerConfig,
    ) -> QuerySet[_M]:
        if not config.enable_prefetch_related or not self.prefetch_related:
            return qs

        abort_only = set()
        prefetch_lists = [
            qs._prefetch_related_lookups,  # type: ignore
            self.prefetch_related,
        ]
        # Add all str at the same time to make it easier to handle Prefetch below
        to_prefetch: dict[str, str | Prefetch] = {
            p: p for p in itertools.chain(*prefetch_lists) if isinstance(p, str)
        }

        # Merge already existing prefetches together
        for p in itertools.chain(*prefetch_lists):
            # Already added above
            if isinstance(p, str):
                continue

            if isinstance(p, Callable):
                assert_type(p, PrefetchCallable)
                p = p(info)  # noqa: PLW2901

            path = p.prefetch_to
            existing = to_prefetch.get(path)
            # The simplest case. The prefetch doesn't exist or is a string.
            # In this case, just replace it.
            if not existing or isinstance(existing, str):
                to_prefetch[path] = p
                if isinstance(existing, str):
                    abort_only.add(path)
                continue

            p1 = PrefetchInspector(existing)
            p2 = PrefetchInspector(p)
            if getattr(existing, "_optimizer_sentinel", None) is _sentinel:
                ret = p1.merge(p2, allow_unsafe_ops=True)
            elif getattr(p, "_optimizer_sentinel", None) is _sentinel:
                ret = p2.merge(p1, allow_unsafe_ops=True)
            else:
                # The order here doesn't matter
                ret = p1.merge(p2)

            to_prefetch[path] = ret.prefetch

        # Abort only optimization if one prefetch related was made for everything
        for ao in abort_only:
            to_prefetch[ao].queryset.query.deferred_loading = (  # type: ignore
                [],
                True,
            )

        # First prefetch_related(None) to clear all existing prefetches, and then
        # add ours, which also contains them. This is to avoid the
        # "lookup was already seen with a different queryset" error
        return qs.prefetch_related(None).prefetch_related(*to_prefetch.values())

    def _apply_select_related(
        self,
        qs: QuerySet[_M],
        *,
        info: GraphQLResolveInfo,
        config: OptimizerConfig,
    ) -> tuple[QuerySet[_M], set[str]]:
        only_set = set(self.only)
        extra_only_set = set()
        select_related_set = set(self.select_related)

        # inspect the queryset to find any existing select_related fields
        def get_related_fields_with_prefix(
            queryset_select_related: dict[str, Any],
            prefix: str = "",
        ):
            for parent, nested in queryset_select_related.items():
                current_path = f"{prefix}{parent}"
                yield current_path

                if nested:  # If there are nested relations, dive deeper
                    yield from get_related_fields_with_prefix(
                        nested,
                        prefix=f"{current_path}{LOOKUP_SEP}",
                    )

        if isinstance(qs.query.select_related, dict):
            select_related_set.update(
                get_related_fields_with_prefix(qs.query.select_related)
            )

        if config.enable_select_related and select_related_set:
            qs = qs.select_related(*select_related_set)

            # Update our extra_select_related_only_set with the fields that were
            # selected by select_related to make sure they actually get selected
            for select_related in select_related_set:
                if select_related in only_set:
                    continue

                if not any(only.startswith(select_related) for only in only_set):
                    extra_only_set.add(select_related)

        return qs, extra_only_set

    def _apply_only(
        self,
        qs: QuerySet[_M],
        *,
        info: GraphQLResolveInfo,
        config: OptimizerConfig,
        extra_only_set: set[str],
    ) -> QuerySet[_M]:
        only_set = set(self.only) | extra_only_set

        if config.enable_only and only_set:
            qs = qs.only(*only_set)

        return qs

    def _apply_annotate(
        self,
        qs: QuerySet[_M],
        *,
        info: GraphQLResolveInfo,
        config: OptimizerConfig,
    ) -> QuerySet[_M]:
        if not config.enable_annotate or not self.annotate:
            return qs

        to_annotate = {}
        for k, v in self.annotate.items():
            if isinstance(v, Callable):
                assert_type(v, AnnotateCallable)
                v = v(info)  # noqa: PLW2901
            to_annotate[k] = v

        return qs.annotate(**to_annotate)


def _get_django_type(
    field: StrawberryField,
) -> type[WithStrawberryDjangoObjectDefinition] | None:
    f_type = field.type
    if isinstance(f_type, LazyType):
        f_type = f_type.resolve_type()
    if isinstance(f_type, StrawberryContainer):
        f_type = f_type.of_type
    if isinstance(f_type, LazyType):
        f_type = f_type.resolve_type()

    return f_type if has_django_definition(f_type) else None


def _get_prefetch_queryset(
    remote_model: type[models.Model],
    schema: Schema,
    field: StrawberryField,
    parent_type: GraphQLObjectType | GraphQLInterfaceType,
    field_node: FieldNode,
    *,
    config: OptimizerConfig | None,
    info: GraphQLResolveInfo,
    related_field_id: str | None = None,
) -> QuerySet:
    # We usually want to use the `_base_manager` for prefetching, as it is what django
    # itself states we should be using:
    # https://docs.djangoproject.com/en/5.0/topics/db/managers/#base-managers
    # But in case prefetch_custom_queryset is enabled, we use the custom queryset
    # from _default_manager instead.
    if config and config.prefetch_custom_queryset:
        qs = remote_model._default_manager.all()
    else:
        qs = remote_model._base_manager.all()  # type: ignore

    if f_type := _get_django_type(field):
        qs = run_type_get_queryset(
            qs,
            f_type,
            info=Info(
                _raw_info=info,
                _field=field,
            ),
        )

    return _optimize_prefetch_queryset(
        qs,
        schema,
        field,
        parent_type,
        field_node,
        config=config,
        info=info,
        related_field_id=related_field_id,
    )


def _optimize_prefetch_queryset(
    qs: QuerySet[_M],
    schema: Schema,
    field: StrawberryField,
    parent_type: GraphQLObjectType | GraphQLInterfaceType,
    field_node: FieldNode,
    *,
    config: OptimizerConfig | None,
    info: GraphQLResolveInfo,
    related_field_id: str | None = None,
) -> QuerySet[_M]:
    from strawberry_django.fields.field import (
        StrawberryDjangoConnectionExtension,
        StrawberryDjangoField,
    )

    if (
        not config
        or not config.enable_nested_relations_prefetch
        or related_field_id is None
        or not isinstance(field, StrawberryDjangoField)
        or is_optimized_by_prefetching(qs)
    ):
        return qs

    mark_optimized = True

    strawberry_schema = cast(Schema, info.schema._strawberry_schema)  # type: ignore
    field_name = strawberry_schema.config.name_converter.from_field(field)
    field_info = Info(
        _raw_info=info,
        _field=field,
    )
    _field_args, field_kwargs = get_arguments(
        field=field,
        source=None,
        info=field_info,
        kwargs=get_argument_values(
            parent_type.fields[field_name],
            field_node,
            info.variable_values,
        ),
        config=strawberry_schema.config,
        scalar_registry=strawberry_schema.schema_converter.scalar_registry,
    )
    field_kwargs.pop("info", None)

    # Disable the optimizer to avoid doint double optimization while running get_queryset
    with DjangoOptimizerExtension.disabled():
        qs = field.get_queryset(
            qs,
            field_info,
            _strawberry_related_field_id=related_field_id,
            **field_kwargs,
        )

        connection_extension = next(
            (
                e
                for e in field.extensions
                if isinstance(e, StrawberryDjangoConnectionExtension)
            ),
            None,
        )
        if connection_extension is not None:
            connection_type_def = get_object_definition(
                connection_extension.connection_type,
                strict=True,
            )
            connection_type = (
                connection_type_def.concrete_of
                and connection_type_def.concrete_of.origin
            )
            if (
                connection_type is relay.ListConnection
                or connection_type is ListConnectionWithTotalCount
            ):
                slice_metadata = SliceMetadata.from_arguments(
                    Info(_raw_info=info, _field=field),
                    first=field_kwargs.get("first"),
                    last=field_kwargs.get("last"),
                    before=field_kwargs.get("before"),
                    after=field_kwargs.get("after"),
                )
                qs = apply_window_pagination(
                    qs,
                    related_field_id=related_field_id,
                    offset=slice_metadata.start,
                    limit=slice_metadata.end - slice_metadata.start,
                )
            else:
                mark_optimized = False

    if mark_optimized:
        qs = mark_optimized_by_prefetching(qs)

    return qs


def _get_selections(
    info: GraphQLResolveInfo,
    parent_type: GraphQLObjectType | GraphQLInterfaceType,
) -> dict[str, list[FieldNode]]:
    return collect_sub_fields(
        info.schema,
        info.fragments,
        info.variable_values,
        cast(GraphQLObjectType, parent_type),
        info.field_nodes,
    )


def _generate_selection_resolve_info(
    info: GraphQLResolveInfo,
    field_nodes: list[FieldNode],
    return_type: GraphQLOutputType,
    parent_type: GraphQLObjectType | GraphQLInterfaceType,
):
    field_node = field_nodes[0]
    return GraphQLResolveInfo(
        field_name=field_node.name.value,
        field_nodes=field_nodes,
        return_type=return_type,
        parent_type=cast(GraphQLObjectType, parent_type),
        path=info.path.add_key(0).add_key(field_node.name.value, parent_type.name),
        schema=info.schema,
        fragments=info.fragments,
        root_value=info.root_value,
        operation=info.operation,
        variable_values=info.variable_values,
        context=info.context,
        is_awaitable=info.is_awaitable,
    )


def _get_field_data(
    selections: list[FieldNode],
    object_definition: StrawberryObjectDefinition,
    schema: Schema,
    *,
    parent_type: GraphQLObjectType | GraphQLInterfaceType,
    info: GraphQLResolveInfo,
) -> tuple[StrawberryField, GraphQLObjectType, FieldNode, GraphQLResolveInfo] | None:
    selection = selections[0]
    field_name = selection.name.value
    for field in object_definition.fields:
        if schema.config.name_converter.get_graphql_name(field) == field_name:
            break
    else:
        return None

    # Do not optimize the field if the user asked not to
    if getattr(field, "disable_optimization", False):
        return None

    definition = parent_type.fields[selection.name.value].type
    while isinstance(definition, GraphQLWrappingType):
        definition = definition.of_type

    field_info = _generate_selection_resolve_info(
        info,
        selections,
        definition,
        parent_type,
    )

    return field, definition, selection, field_info


def _get_hints_from_field(
    field: StrawberryField,
    *,
    f_info: GraphQLResolveInfo,
    prefix: str = "",
) -> OptimizerStore | None:
    if not (field_store := getattr(field, "store", None)):
        return None

    if len(field_store.annotate) == 1 and _annotate_placeholder in field_store.annotate:
        # This is a special case where we need to update the field name,
        # because when field_store was created on __init__,
        # the field name wasn't available.
        # This allows for annotate expressions to be declared as:
        #   total: int = gql.django.field(annotate=Sum("price"))  # noqa: ERA001
        # Instead of the more redundant:
        #   total: int = gql.django.field(annotate={"total": Sum("price")})  # noqa: ERA001
        field_store.annotate = {
            field.name: field_store.annotate[_annotate_placeholder],
        }

    return field_store.with_prefix(prefix, info=f_info) if prefix else field_store


def _get_hints_from_model_property(
    field: StrawberryField,
    model: type[models.Model],
    *,
    f_info: GraphQLResolveInfo,
    prefix: str = "",
) -> OptimizerStore | None:
    model_attr = getattr(model, field.python_name, None)
    if (
        model_attr is not None
        and isinstance(model_attr, ModelProperty)
        and model_attr.store
    ):
        attr_store = model_attr.store
        store = attr_store.with_prefix(prefix, info=f_info) if prefix else attr_store
    else:
        store = None

    return store


def _get_hints_from_django_foreign_key(
    field: StrawberryField,
    field_definition: GraphQLObjectType,
    field_selection: FieldNode,
    model_field: models.ForeignKey | OneToOneRel,
    model_fieldname: str,
    schema: Schema,
    *,
    config: OptimizerConfig,
    parent_type: GraphQLObjectType | GraphQLInterfaceType,
    field_info: GraphQLResolveInfo,
    path: str,
    cache: dict[type[models.Model], list[tuple[int, OptimizerStore]]],
    level: int = 0,
) -> OptimizerStore:
    f_type = _get_django_type(field)
    if f_type and hasattr(f_type, "get_queryset"):
        # If the field has a get_queryset method, change strategy to Prefetch
        # so it will be respected
        store = _get_hints_from_django_relation(
            field,
            field_definition=field_definition,
            field_selection=field_selection,
            model_field=model_field,
            model_fieldname=model_fieldname,
            schema=schema,
            config=config,
            parent_type=parent_type,
            field_info=field_info,
            path=path,
            cache=cache,
            level=level,
        )
        store.only.append(path)
        return store

    store = OptimizerStore.with_hints(
        only=[path],
        select_related=[path],
    )

    # If adding a reverse relation, make sure to select its pointer to us,
    # or else this might causa a refetch from the database
    if isinstance(model_field, OneToOneRel):
        remote_field = model_field.remote_field
        store.only.append(
            f"{path}{LOOKUP_SEP}{resolve_model_field_name(remote_field)}",
        )

    for f_type_def in get_possible_type_definitions(field.type):
        f_model = model_field.related_model
        f_store = _get_model_hints(
            f_model,
            schema,
            f_type_def,
            parent_type=field_definition,
            info=field_info,
            config=config,
            cache=cache,
            level=level + 1,
        )
        if f_store is not None:
            cache.setdefault(f_model, []).append((level, f_store))
            store |= f_store.with_prefix(path, info=field_info)

    return store


def _get_hints_from_django_relation(
    field: StrawberryField,
    field_definition: GraphQLObjectType,
    field_selection: FieldNode,
    model_field: (
        models.ManyToManyField
        | ManyToManyRel
        | ManyToOneRel
        | GenericRelation
        | OneToOneRel
        | models.ForeignKey
    ),
    model_fieldname: str,
    schema: Schema,
    *,
    config: OptimizerConfig,
    parent_type: GraphQLObjectType | GraphQLInterfaceType,
    field_info: GraphQLResolveInfo,
    path: str,
    cache: dict[type[models.Model], list[tuple[int, OptimizerStore]]],
    level: int = 0,
) -> OptimizerStore:
    try:
        from django.contrib.contenttypes.fields import GenericRelation
    except (ImportError, RuntimeError):  # pragma: no cover
        GenericRelation = None  # noqa: N806

    store = OptimizerStore()

    f_types = list(get_possible_type_definitions(field.type))
    if len(f_types) > 1:
        # This might be a generic foreign key.
        # In this case, just prefetch it
        store.prefetch_related.append(model_fieldname)
        return store

    field_store = getattr(field, "store", None)
    if field_store and field_store.prefetch_related:
        # Skip optimization if 'prefetch_related' is present in the field's store.
        # This is necessary because 'prefetch_related' likely modifies the queryset
        # with filtering or annotating, making the optimization redundant and
        # potentially causing an extra unused query.
        return store

    remote_field = model_field.remote_field
    remote_model = remote_field.model
    field_store = _get_model_hints(
        remote_model,
        schema,
        f_types[0],
        parent_type=field_definition,
        info=field_info,
        config=config,
        cache=cache,
        level=level + 1,
    )
    if field_store is None:
        return store

    related_field_id = getattr(remote_field, "attname", None) or getattr(
        remote_field, "name", None
    )

    if (
        config.enable_only
        and field_store.only
        and not isinstance(remote_field, ManyToManyRel)
    ):
        # If adding a reverse relation, make sure to select its
        # pointer to us, or else this might causa a refetch from
        # the database
        if GenericRelation is not None and isinstance(
            model_field,
            GenericRelation,
        ):
            field_store.only.append(model_field.object_id_field_name)
            field_store.only.append(model_field.content_type_field_name)
        elif related_field_id is not None:
            field_store.only.append(related_field_id)

    path_lookup = f"{path}{LOOKUP_SEP}"
    if store.only and field_store.only:
        extra_only = [o for o in store.only or [] if o.startswith(path_lookup)]
        store.only = [o for o in store.only if o not in extra_only]
        field_store.only.extend(o[len(path_lookup) :] for o in extra_only)

    if store.select_related and field_store.select_related:
        extra_sr = [o for o in store.select_related or [] if o.startswith(path_lookup)]
        store.select_related = [o for o in store.select_related if o not in extra_sr]
        field_store.select_related.extend(o[len(path_lookup) :] for o in extra_sr)

    cache.setdefault(remote_model, []).append((level, field_store))

    base_qs = _get_prefetch_queryset(
        remote_model,
        schema,
        field,
        parent_type,
        field_selection,
        config=config,
        info=field_info,
        related_field_id=related_field_id,
    )
    field_qs = field_store.apply(base_qs, info=field_info, config=config)
    field_prefetch = Prefetch(path, queryset=field_qs)
    field_prefetch._optimizer_sentinel = _sentinel  # type: ignore
    store.prefetch_related.append(field_prefetch)

    return store


def _get_hints_from_django_field(
    field: StrawberryField,
    field_definition: GraphQLObjectType,
    field_selection: FieldNode,
    model: type[models.Model],
    schema: Schema,
    *,
    config: OptimizerConfig,
    parent_type: GraphQLObjectType | GraphQLInterfaceType,
    field_info: GraphQLResolveInfo,
    prefix: str = "",
    cache: dict[type[models.Model], list[tuple[int, OptimizerStore]]],
    level: int = 0,
) -> OptimizerStore | None:
    try:
        from django.contrib.contenttypes.fields import (
            GenericForeignKey,
            GenericRelation,
        )
    except (ImportError, RuntimeError):  # pragma: no cover
        GenericForeignKey = None  # noqa: N806
        GenericRelation = None  # noqa: N806
        _relation_fields = (models.ManyToManyField, ManyToManyRel, ManyToOneRel)
    else:
        _relation_fields = (
            models.ManyToManyField,
            ManyToManyRel,
            ManyToOneRel,
            GenericRelation,
        )

    # If the field has a base resolver, don't try to optimize it. The user should
    # be defining custom hints in this case, which should already be in the store
    # GlobalID and special cases setting `can_optimize` are ok though, as those resolvers
    # are auto generated by us
    if (
        field.base_resolver is not None
        and field.type != relay.GlobalID
        and not getattr(field.base_resolver.wrapped_func, "can_optimize", False)
    ):
        return None

    model_fieldname: str = getattr(field, "django_name", None) or field.python_name
    if (model_field := get_model_field(model, model_fieldname)) is None:
        return None

    path = f"{prefix}{model_fieldname}"

    if isinstance(model_field, (models.ForeignKey, OneToOneRel)):
        store = _get_hints_from_django_foreign_key(
            field,
            field_definition=field_definition,
            field_selection=field_selection,
            model_field=model_field,
            model_fieldname=model_fieldname,
            schema=schema,
            config=config,
            parent_type=parent_type,
            field_info=field_info,
            path=path,
            cache=cache,
            level=level,
        )
    elif GenericForeignKey and isinstance(model_field, GenericForeignKey):
        # There's not much we can do to optimize generic foreign keys regarding
        # only/select_related because they can be anything.
        # Just prefetch_related them
        store = OptimizerStore.with_hints(prefetch_related=[model_fieldname])
    elif isinstance(model_field, _relation_fields):
        store = _get_hints_from_django_relation(
            field,
            field_definition=field_definition,
            field_selection=field_selection,
            model_field=model_field,
            model_fieldname=model_fieldname,
            schema=schema,
            config=config,
            parent_type=parent_type,
            field_info=field_info,
            path=path,
            cache=cache,
            level=level,
        )
    else:
        store = OptimizerStore.with_hints(only=[path])

    return store


def _get_model_hints(
    model: type[models.Model],
    schema: Schema,
    object_definition: StrawberryObjectDefinition,
    *,
    parent_type: GraphQLObjectType | GraphQLInterfaceType,
    info: GraphQLResolveInfo,
    config: OptimizerConfig | None = None,
    prefix: str = "",
    cache: dict[type[models.Model], list[tuple[int, OptimizerStore]]] | None = None,
    level: int = 0,
) -> OptimizerStore | None:
    cache = cache or {}

    # In case this is a relay field, find the selected edges/nodes, the selected fields
    # are actually inside edges -> node selection...
    if issubclass(object_definition.origin, relay.Connection):
        return _get_model_hints_from_connection(
            model,
            schema,
            object_definition,
            parent_type=parent_type,
            info=info,
            config=config,
            prefix=prefix,
            cache=cache,
            level=level,
        )

    store = OptimizerStore()
    config = config or OptimizerConfig()

    dj_definition = get_django_definition(object_definition.origin)
    if (
        dj_definition is None
        or not issubclass(model, dj_definition.model)
        or dj_definition.disable_optimization
    ):
        return None

    dj_type_store = getattr(dj_definition, "store", None)
    if dj_type_store:
        store |= dj_type_store

    # Make sure that the model's pk is always selected when using only
    pk = model._meta.pk
    if pk is not None:
        store.only.append(pk.attname)

    for f_selections in _get_selections(info, parent_type).values():
        field_data = _get_field_data(
            f_selections,
            object_definition,
            schema,
            parent_type=parent_type,
            info=info,
        )
        if field_data is None:
            continue

        field, f_definition, f_selection, f_info = field_data

        # Add annotations from the field if they exist
        if field_store := _get_hints_from_field(field, f_info=f_info, prefix=prefix):
            store |= field_store

        # Then from the model property if one is defined
        if model_property_store := _get_hints_from_model_property(
            field,
            model,
            f_info=f_info,
            prefix=prefix,
        ):
            store |= model_property_store

        # Lastly, from the django field itself
        if model_field_store := _get_hints_from_django_field(
            field,
            f_definition,
            f_selection,
            model,
            schema,
            config=config,
            parent_type=parent_type,
            field_info=f_info,
            prefix=prefix,
            cache=cache,
            level=level,
        ):
            store |= model_field_store

    # Django keeps track of known fields. That means that if one model select_related or
    # prefetch_related another one, and later another one select_related or
    # prefetch_related the model again, if the used fields there where not optimized in
    # this call django would have to fetch those again. By mergint those with us we are
    # making sure to avoid that
    for inner_level, inner_store in cache.get(model, []):
        if inner_level > level and inner_store:
            # We only want the only/select_related from this. prefetch_related is
            # something else
            store.only.extend(inner_store.only)
            store.select_related.extend(inner_store.select_related)

    return store


def _get_gql_definition(
    schema: Schema,
    definition: StrawberryObjectDefinition,
) -> GraphQLInterfaceType | GraphQLObjectType:
    if definition.is_interface:
        return schema.schema_converter.from_interface(definition)

    return schema.schema_converter.from_object(definition)


def _get_model_hints_from_connection(
    model: type[models.Model],
    schema: Schema,
    object_definition: StrawberryObjectDefinition,
    *,
    parent_type: GraphQLObjectType | GraphQLInterfaceType,
    info: GraphQLResolveInfo,
    config: OptimizerConfig | None = None,
    prefix: str = "",
    cache: dict[type[models.Model], list[tuple[int, OptimizerStore]]] | None = None,
    level: int = 0,
) -> OptimizerStore | None:
    store = None

    n_type = object_definition.type_var_map.get("NodeType")
    if n_type is None:
        specialized_type_var_map = object_definition.specialized_type_var_map or {}

        n_type = specialized_type_var_map["NodeType"]

    if isinstance(n_type, LazyType):
        n_type = n_type.resolve_type()

    n_definition = get_object_definition(n_type, strict=True)

    for edges in _get_selections(info, parent_type).values():
        edge = edges[0]
        if edge.name.value != "edges":
            continue

        e_definition = get_object_definition(relay.Edge, strict=True)
        e_type = e_definition.resolve_generic(
            relay.Edge[cast(Type[relay.Node], n_type)],
        )
        e_gql_definition = _get_gql_definition(
            schema,
            get_object_definition(e_type, strict=True),
        )
        assert isinstance(e_gql_definition, (GraphQLObjectType, GraphQLInterfaceType))
        e_info = _generate_selection_resolve_info(
            info,
            edges,
            e_gql_definition,
            parent_type,
        )
        for nodes in _get_selections(e_info, e_gql_definition).values():
            node = nodes[0]
            if node.name.value != "node":
                continue

            n_gql_definition = _get_gql_definition(schema, n_definition)
            assert isinstance(
                n_gql_definition,
                (GraphQLObjectType, GraphQLInterfaceType),
            )
            n_info = _generate_selection_resolve_info(
                info,
                nodes,
                n_gql_definition,
                e_gql_definition,
            )

            store = _get_model_hints(
                model=model,
                schema=schema,
                object_definition=n_definition,
                parent_type=n_gql_definition,
                info=n_info,
                config=config,
                prefix=prefix,
                cache=cache,
                level=level,
            )

    return store


def optimize(
    qs: QuerySet[_M] | BaseManager[_M],
    info: GraphQLResolveInfo | Info,
    *,
    config: OptimizerConfig | None = None,
    store: OptimizerStore | None = None,
) -> QuerySet[_M]:
    """Optimize the given queryset considering the gql info.

    This will look through the gql selections, fields and model hints and apply
    `only`, `select_related`, `prefetch_related` and `annotate` optimizations
    according those on the `QuerySet`_.

    Note:
    ----
        This do not execute the queryset, it only optimizes it for when it is actually
        executed.

        It will also avoid doing any extra optimization if the queryset already has
        cached results in it, to avoid triggering extra queries later.

    Args:
    ----
        qs:
            The queryset to be optimized
        info:
            The current field execution info
        config:
            Optional config to use when doing the optimization
        store:
            Optional initial store to use for the optimization

    Returns:
    -------
        The optimized queryset

    .. _QuerySet:
        https://docs.djangoproject.com/en/dev/ref/models/querysets/

    """
    if isinstance(qs, BaseManager):
        qs = cast(QuerySet[_M], qs.all())

    if isinstance(qs, list):
        # return sliced queryset as-is
        return qs

    # Avoid optimizing twice and also modify an already resolved queryset
    if is_optimized(qs) or qs._result_cache is not None:  # type: ignore
        return qs

    if isinstance(info, Info):
        info = info._raw_info

    config = config or OptimizerConfig()
    store = store or OptimizerStore()
    schema = cast(Schema, info.schema._strawberry_schema)  # type: ignore

    gql_type = get_named_type(info.return_type)
    strawberry_type = schema.get_type_by_name(gql_type.name)
    if strawberry_type is None:
        return qs

    for object_definition in get_possible_type_definitions(strawberry_type):
        if object_definition.is_interface:
            interface_definitions = _interfaces[schema].get(object_definition)
            if interface_definitions is None:
                interface_definitions = []
                for t in schema.schema_converter.type_map.values():
                    t_definition = t.definition
                    if isinstance(
                        t_definition, StrawberryObjectDefinition
                    ) and issubclass(t_definition.origin, object_definition.origin):
                        interface_definitions.append(t_definition)
                _interfaces[schema][object_definition] = interface_definitions

            object_definitions = []
            for interface_definition in interface_definitions:
                dj_definition = get_django_definition(interface_definition.origin)
                if dj_definition and issubclass(qs.model, dj_definition.model):
                    object_definitions.append(interface_definition)
        else:
            object_definitions = [object_definition]

        for inner_object_definition in object_definitions:
            parent_type = _get_gql_definition(schema, inner_object_definition)
            new_store = _get_model_hints(
                qs.model,
                schema,
                inner_object_definition,
                parent_type=parent_type,
                info=info,
                config=config,
            )
            if new_store is not None:
                store |= new_store

    if store:
        qs = store.apply(qs, info=info, config=config)
        qs_config = get_queryset_config(qs)
        qs_config.optimized = True

    return qs


def is_optimized(qs: QuerySet) -> bool:
    return get_queryset_config(qs).optimized or is_optimized_by_prefetching(qs)


def mark_optimized_by_prefetching(qs: QuerySet[_M]) -> QuerySet[_M]:
    # This is a bit of a hack, but there is no easy way to mark a related manager
    # as optimized at this phase, so we just add a mark to the queryset that
    # we can check leater on using is_optimized_by_prefetching
    return qs.annotate(**{
        NESTED_PREFETCH_MARK: models.Value(True),
    })


def is_optimized_by_prefetching(qs: QuerySet) -> bool:
    return NESTED_PREFETCH_MARK in qs.query.annotations


optimizer: contextvars.ContextVar[DjangoOptimizerExtension | None] = (
    contextvars.ContextVar(
        "optimizer_ctx",
        default=None,
    )
)


class DjangoOptimizerExtension(SchemaExtension):
    """Automatically optimize returned querysets from internal resolvers.

    Attributes
    ----------
        enable_only_optimization:
            Enable `QuerySet.only` optimizations
        enable_select_related_optimization:
            Enable `QuerySet.select_related` optimizations
        enable_prefetch_related_optimization:
            Enable `QuerySet.prefetch_related` optimizations
        enable_nested_relations_prefetch:
            Enable prefetch of nested relations. This will allow for nested
            relations to be prefetched even when using filters/ordering/pagination.
            Note however that for connections, it will only work when for the
            `ListConnection` and `ListConnectionWithTotalCount` types, as this optimization
            is not safe to be applied automatically for custom connections.
        enable_annotate_optimization:
            Enable `QuerySet.annotate` optimizations

    Examples
    --------
        Add the following to your schema configuration.

        >>> import strawberry
        >>> from strawberry_django_plus.optimizer import DjangoOptimizerExtension
        ...
        >>> schema = strawberry.Schema(
        ...     Query,
        ...     extensions=[
        ...         DjangoOptimizerExtension(),
        ...     ]
        ... )

    """

    enabled: contextvars.ContextVar[bool] = contextvars.ContextVar(
        "optimizer_enabled_ctx",
        default=True,
    )

    def __init__(
        self,
        *,
        enable_only_optimization: bool = True,
        enable_select_related_optimization: bool = True,
        enable_prefetch_related_optimization: bool = True,
        enable_annotate_optimization: bool = True,
        enable_nested_relations_prefetch: bool = True,
        execution_context: ExecutionContext | None = None,
        prefetch_custom_queryset: bool = False,
    ):
        super().__init__(execution_context=execution_context)  # type: ignore
        self.enable_only = enable_only_optimization
        self.enable_select_related = enable_select_related_optimization
        self.enable_prefetch_related = enable_prefetch_related_optimization
        self.enable_annotate_optimization = enable_annotate_optimization
        self.enable_nested_relations_prefetch = enable_nested_relations_prefetch
        self.prefetch_custom_queryset = prefetch_custom_queryset

    def on_execute(self) -> Generator[None, None, None]:
        token = optimizer.set(self)
        try:
            yield
        finally:
            optimizer.reset(token)

    def resolve(
        self,
        _next: Callable,
        root: Any,
        info: GraphQLResolveInfo,
        *args,
        **kwargs,
    ) -> AwaitableOrValue[Any]:
        ret = _next(root, info, *args, **kwargs)
        if not self.enabled.get():
            return ret

        if isinstance(ret, BaseManager):
            ret = ret.all()

        if isinstance(ret, QuerySet) and ret._result_cache is None:  # type: ignore
            config = OptimizerConfig(
                enable_only=(
                    self.enable_only and info.operation.operation == OperationType.QUERY
                ),
                enable_select_related=self.enable_select_related,
                enable_prefetch_related=self.enable_prefetch_related,
                enable_annotate=self.enable_annotate_optimization,
                prefetch_custom_queryset=self.prefetch_custom_queryset,
                enable_nested_relations_prefetch=self.enable_nested_relations_prefetch,
            )
            ret = django_fetch(optimize(qs=ret, info=info, config=config))

        return ret

    @classmethod
    @contextlib.contextmanager
    def disabled(cls):
        token = cls.enabled.set(False)
        try:
            yield
        finally:
            cls.enabled.reset(token)

    def optimize(
        self,
        qs: QuerySet[_M] | BaseManager[_M],
        info: GraphQLResolveInfo | Info,
        *,
        store: OptimizerStore | None = None,
    ) -> QuerySet[_M]:
        if not self.enabled.get():
            return qs

        config = OptimizerConfig(
            enable_only=self.enable_only
            and info.operation.operation == OperationType.QUERY,
            enable_select_related=self.enable_select_related,
            enable_prefetch_related=self.enable_prefetch_related,
            enable_annotate=self.enable_annotate_optimization,
            prefetch_custom_queryset=self.prefetch_custom_queryset,
        )
        return optimize(qs, info, config=config, store=store)
