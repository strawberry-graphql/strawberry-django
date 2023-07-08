from __future__ import annotations

import contextlib
import contextvars
import dataclasses
import itertools
from collections import defaultdict
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ForwardRef,
    Generator,
    Type,
    TypeVar,
    cast,
)

from django.db import models
from django.db.models import Prefetch
from django.db.models.constants import LOOKUP_SEP
from django.db.models.fields.reverse_related import (
    ManyToManyRel,
    ManyToOneRel,
    OneToOneRel,
)
from django.db.models.manager import BaseManager
from django.db.models.query import QuerySet
from graphql.language.ast import OperationType
from graphql.type.definition import GraphQLResolveInfo, get_named_type
from strawberry import relay
from strawberry.extensions import SchemaExtension
from strawberry.lazy_type import LazyType
from strawberry.object_type import StrawberryObjectDefinition
from strawberry.schema.schema import Schema
from strawberry.type import get_object_definition
from strawberry.types.info import Info
from strawberry.types.nodes import InlineFragment, Selection, convert_selections
from strawberry.utils.typing import eval_type
from typing_extensions import assert_never, assert_type, get_args

from strawberry_django.fields.types import resolve_model_field_name
from strawberry_django.resolvers import django_fetch

from .descriptors import ModelProperty
from .utils.inspect import (
    PrefetchInspector,
    get_model_fields,
    get_possible_type_definitions,
    get_selections,
)
from .utils.typing import (
    PrefetchCallable,
    PrefetchType,
    TypeOrSequence,
    get_django_definition,
)

if TYPE_CHECKING:
    from strawberry.types.execution import ExecutionContext
    from strawberry.utils.await_maybe import AwaitableOrValue


__all__ = [
    "OptimizerConfig",
    "DjangoOptimizerExtension",
    "OptimizerStore",
    "PrefetchType",
    "optimize",
]

_T = TypeVar("_T")
_M = TypeVar("_M", bound=models.Model)

_sentinel = object()
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
        prefetch_custom_queryset:
            Use custom instead of _base_manager for prefetch querysets

    """

    enable_only: bool = dataclasses.field(default=True)
    enable_select_related: bool = dataclasses.field(default=True)
    enable_prefetch_related: bool = dataclasses.field(default=True)
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

    """

    only: list[str] = dataclasses.field(default_factory=list)
    select_related: list[str] = dataclasses.field(default_factory=list)
    prefetch_related: list[PrefetchType] = dataclasses.field(default_factory=list)

    def __bool__(self):
        return any([self.only, self.select_related, self.prefetch_related])

    def __ior__(self, other: OptimizerStore):
        self.only.extend(other.only)
        self.select_related.extend(other.select_related)
        self.prefetch_related.extend(other.prefetch_related)
        return self

    def __or__(self, other: OptimizerStore):
        return self.copy().__ior__(other)

    def copy(self):
        return self.__class__(
            only=self.only[:],
            select_related=self.select_related[:],
            prefetch_related=self.prefetch_related[:],
        )

    @classmethod
    def with_hints(
        cls,
        *,
        only: TypeOrSequence[str] | None = None,
        select_related: TypeOrSequence[str] | None = None,
        prefetch_related: TypeOrSequence[PrefetchType] | None = None,
    ):
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
        )

    def with_prefix(self, prefix: str, *, info: GraphQLResolveInfo):
        prefetch_related = []
        for p in self.prefetch_related:
            if isinstance(p, Callable):
                assert_type(p, PrefetchCallable)
                p = p(info)  # noqa: PLW2901

            if isinstance(p, str):
                prefetch_related.append(f"{prefix}{LOOKUP_SEP}{p}")
            elif isinstance(p, Prefetch):
                p.add_prefix(prefix)
                prefetch_related.append(p)
            else:  # pragma:nocover
                assert_never(p)

        return self.__class__(
            only=[f"{prefix}{LOOKUP_SEP}{i}" for i in self.only],
            select_related=[f"{prefix}{LOOKUP_SEP}{i}" for i in self.select_related],
            prefetch_related=prefetch_related,
        )

    def apply(
        self,
        qs: QuerySet[_M],
        *,
        info: GraphQLResolveInfo,
        config: OptimizerConfig | None = None,
    ) -> QuerySet[_M]:
        config = config or OptimizerConfig()

        if config.enable_prefetch_related and self.prefetch_related:
            # Add all str at the same time to make it easier to handle Prefetch below
            to_prefetch: dict[str, str | Prefetch] = {
                p: p for p in self.prefetch_related if isinstance(p, str)
            }

            abort_only = set()
            # Merge already existing prefetches together
            for p in itertools.chain(
                qs._prefetch_related_lookups,  # type: ignore
                self.prefetch_related,
            ):
                # Already added above
                if isinstance(p, str):
                    continue

                if isinstance(p, Callable):
                    assert_type(p, PrefetchCallable)
                    p = p(info)  # noqa: PLW2901

                path = cast(str, p.prefetch_to)  # type: ignore
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

            # First prefetch_related(None) to clear all existing prefetches, and them
            # add ours, which also contains them. This is to avoid the
            # "lookup was already seen with a different queryset" error
            qs = qs.prefetch_related(None).prefetch_related(*to_prefetch.values())

        if config.enable_select_related and self.select_related:
            qs = qs.select_related(*self.select_related)

        if config.enable_only and self.only:
            qs = qs.only(*self.only)

        return qs


def _get_prefetch_queryset(
    remote_model: type[models.Model],
    field,
    config: OptimizerConfig | None,
    info: GraphQLResolveInfo,
) -> QuerySet:
    if not config or not config.prefetch_custom_queryset:
        return remote_model._base_manager.all()  # type: ignore
    remote_type_defs = get_args(field.type_annotation.annotation)
    if len(remote_type_defs) != 1:
        raise TypeError(f"Expected exactly one remote type: {remote_type_defs}")
    if type(remote_type_defs[0]) is ForwardRef:
        remote_type = eval_type(
            remote_type_defs[0],
            field.type_annotation.namespace,
            None,
        )
    else:
        remote_type = remote_type_defs[0]
    return remote_type.get_queryset(remote_model.objects.all(), info)


def _get_model_hints(
    model: type[models.Model],
    schema: Schema,
    object_definition: StrawberryObjectDefinition,
    selection: Selection,
    *,
    info: GraphQLResolveInfo,
    config: OptimizerConfig | None = None,
    prefix: str = "",
    cache: dict[type[models.Model], list[tuple[int, OptimizerStore]]] | None = None,
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

    store = OptimizerStore()
    cache = cache or {}
    t_name = schema.config.name_converter.from_object(object_definition)

    # In case this is a relay field, find the selected edges/nodes, the selected fields
    # are actually inside edges -> node selection...
    if issubclass(
        object_definition.origin,
        relay.Connection,
    ):
        # TODO: Connections are mostly used for pagination so it doesn't make sense for
        # us to optimize those, as our prefetch would be thrown away causing an extra
        # useless query. Is there a way for us to properly optimize this in the future?
        if level > 0:
            return None

        n_type = object_definition.type_var_map.get(cast(TypeVar, relay.NodeType))
        if n_type is None:
            specialized_type_var_map = object_definition.specialized_type_var_map or {}

            n_type = specialized_type_var_map[cast(TypeVar, relay.NodeType)]
        if isinstance(n_type, LazyType):
            n_type = n_type.resolve_type()

        n_definition = get_object_definition(n_type, strict=True)

        for edges in get_selections(selection, typename=t_name).values():
            if edges.name != "edges":
                continue

            e_definition = get_object_definition(relay.Edge, strict=True)
            e_type = e_definition.resolve_generic(
                relay.Edge[cast(Type[relay.Node], n_type)],
            )
            e_name = schema.config.name_converter.from_object(
                get_object_definition(e_type, strict=True),
            )
            for node in get_selections(edges, typename=e_name).values():
                if node.name != "node":
                    continue

                new_store = _get_model_hints(
                    model=model,
                    schema=schema,
                    object_definition=n_definition,
                    selection=node,
                    info=info,
                    config=config,
                    prefix=prefix,
                    cache=cache,
                    level=level,
                )
                if new_store is not None:
                    store |= new_store

        return store

    fields = {
        schema.config.name_converter.get_graphql_name(f): f
        for f in object_definition.fields
    }
    model_fields = get_model_fields(model)

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

    for f_selection in get_selections(selection, typename=t_name).values():
        field = fields.get(f_selection.name, None)
        if not field:
            continue

        # Do not optimize the field if the user asked not to
        if getattr(field, "disable_optimization", False):
            continue

        # Add annotations from the field if they exist
        field_store = getattr(field, "store", None)
        if field_store is not None:
            store |= (
                field_store.with_prefix(prefix, info=info) if prefix else field_store
            )

        # Then from the model property if one is defined
        model_attr = getattr(model, field.python_name, None)
        if model_attr is not None and isinstance(model_attr, ModelProperty):
            attr_store = model_attr.store
            store |= attr_store.with_prefix(prefix, info=info) if prefix else attr_store

        # Lastly, from the django field itself
        model_fieldname: str = getattr(field, "django_name", None) or field.python_name
        model_field = model_fields.get(model_fieldname, None)
        if model_field is not None:
            path = f"{prefix}{model_fieldname}"

            if isinstance(model_field, (models.ForeignKey, OneToOneRel)):
                store.only.append(path)
                store.select_related.append(path)

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
                        f_selection,
                        info=info,
                        config=config,
                        cache=cache,
                        level=level + 1,
                    )
                    if f_store is not None:
                        cache.setdefault(f_model, []).append((level, f_store))
                        store |= f_store.with_prefix(path, info=info)
            elif GenericForeignKey and isinstance(model_field, GenericForeignKey):
                # There's not much we can do to optimize generic foreign keys regarding
                # only/select_related because they can be anything.
                # Just prefetch_related them
                store.prefetch_related.append(model_fieldname)
            elif isinstance(
                model_field,
                _relation_fields,
            ):
                f_types = list(get_possible_type_definitions(field.type))
                if len(f_types) > 1:
                    # This might be a generic foreign key.
                    # In this case, just prefetch it
                    store.prefetch_related.append(model_fieldname)
                elif len(f_types) == 1:
                    remote_field = model_field.remote_field
                    remote_model = remote_field.model
                    f_store = _get_model_hints(
                        remote_model,
                        schema,
                        f_types[0],
                        f_selection,
                        info=info,
                        config=config,
                        cache=cache,
                        level=level + 1,
                    )

                    if f_store is not None:
                        if (
                            (config is None or config.enable_only)
                            and f_store.only
                            and not isinstance(remote_field, ManyToManyRel)
                        ):
                            # If adding a reverse relation, make sure to select its
                            # pointer to us, or else this might causa a refetch from
                            # the database
                            if GenericRelation is not None and isinstance(
                                model_field,
                                GenericRelation,
                            ):
                                f_store.only.append(model_field.object_id_field_name)
                                f_store.only.append(model_field.content_type_field_name)
                            else:
                                f_store.only.append(
                                    remote_field.attname or remote_field.name,
                                )

                        path_lookup = f"{path}{LOOKUP_SEP}"
                        if store.only and f_store.only:
                            extra_only = [
                                o for o in store.only or [] if o.startswith(path_lookup)
                            ]
                            store.only = [o for o in store.only if o not in extra_only]
                            f_store.only.extend(
                                o[len(path_lookup) :] for o in extra_only
                            )

                        if store.select_related and f_store.select_related:
                            extra_sr = [
                                o
                                for o in store.select_related or []
                                if o.startswith(path_lookup)
                            ]
                            store.select_related = [
                                o for o in store.select_related if o not in extra_sr
                            ]
                            f_store.select_related.extend(
                                o[len(path_lookup) :] for o in extra_sr
                            )

                        cache.setdefault(remote_model, []).append((level, f_store))

                        # If prefetch_custom_queryset is false, use _base_manager here
                        # instead of _default_manager because we are getting related
                        # objects, and not querying it directly. Else use the type's
                        # get_queryset and model's custom QuerySet.
                        base_qs = _get_prefetch_queryset(
                            remote_model,
                            field,
                            config,
                            info,
                        )
                        f_qs = f_store.apply(
                            base_qs,
                            info=info,
                            config=config,
                        )
                        f_prefetch = Prefetch(path, queryset=f_qs)
                        f_prefetch._optimizer_sentinel = _sentinel  # type: ignore
                        store.prefetch_related.append(f_prefetch)
            else:
                store.only.append(path)

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


def optimize(
    qs: QuerySet[_M] | BaseManager[_M],
    info: GraphQLResolveInfo | Info,
    *,
    config: OptimizerConfig | None = None,
    store: OptimizerStore | None = None,
) -> QuerySet[_M]:
    """Optimize the given queryset considering the gql info.

    This will look through the gql selections, fields and model hints and apply
    `only`, `select_related` and `prefetch_related` optimizations according those
    on the `QuerySet`_.

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

    # Avoid optimizing twice and also modify an already resolved queryset
    if (
        getattr(qs, "_gql_optimized", False)
        or qs._result_cache is not None  # type: ignore
    ):
        return qs

    if isinstance(info, Info):
        info = info._raw_info

    config = config or OptimizerConfig()
    store = store or OptimizerStore()
    schema = cast(Schema, info.schema._strawberry_schema)  # type: ignore

    field_name = info.field_name
    gql_type = get_named_type(info.return_type)
    strawberry_type = schema.get_type_by_name(gql_type.name)
    if strawberry_type is None:
        return qs

    for object_definition in get_possible_type_definitions(strawberry_type):
        if object_definition.is_interface:
            object_definitions = _interfaces[schema].get(object_definition)
            if object_definitions is None:
                object_definitions = []

                for t in schema.schema_converter.type_map.values():
                    t_definition = t.definition
                    if not isinstance(t_definition, StrawberryObjectDefinition):
                        continue

                    if issubclass(t_definition.origin, object_definition.origin):
                        dj_definition = get_django_definition(t_definition.origin)
                        if dj_definition and issubclass(qs.model, dj_definition.model):
                            object_definitions.append(t_definition)

                _interfaces[schema][object_definition] = object_definitions
        else:
            object_definitions = [object_definition]

        for selection in convert_selections(info, info.field_nodes):
            if isinstance(selection, InlineFragment) or selection.name != field_name:
                continue

            for t_definition in object_definitions:
                new_store = _get_model_hints(
                    qs.model,
                    schema,
                    t_definition,
                    selection,
                    info=info,
                    config=config,
                )
                if new_store is not None:
                    store |= new_store

    if store:
        qs = store.apply(qs, info=info, config=config)
        qs._gql_optimized = True  # type: ignore

    return qs


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
        execution_context: ExecutionContext | None = None,
        prefetch_custom_queryset: bool = False,
    ):
        super().__init__(execution_context=execution_context)  # type: ignore
        self.enable_ony = enable_only_optimization
        self.enable_select_related = enable_select_related_optimization
        self.enable_prefetch_related = enable_prefetch_related_optimization
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
                    self.enable_ony and info.operation.operation == OperationType.QUERY
                ),
                enable_select_related=self.enable_select_related,
                enable_prefetch_related=self.enable_prefetch_related,
                prefetch_custom_queryset=self.prefetch_custom_queryset,
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
            enable_only=self.enable_ony
            and info.operation.operation == OperationType.QUERY,
            enable_select_related=self.enable_select_related,
            enable_prefetch_related=self.enable_prefetch_related,
            prefetch_custom_queryset=self.prefetch_custom_queryset,
        )
        return optimize(qs, info, config=config, store=store)
