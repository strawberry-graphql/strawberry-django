from __future__ import annotations

import dataclasses
import functools
import itertools
import weakref
from collections.abc import Iterable
from typing import (
    TYPE_CHECKING,
    Any,
    cast,
)

from django.db.models.query import Prefetch, QuerySet
from django.db.models.sql.where import WhereNode
from strawberry import Schema
from strawberry.types import has_object_definition
from strawberry.types.base import (
    StrawberryContainer,
    StrawberryObjectDefinition,
    StrawberryType,
    StrawberryTypeVar,
)
from strawberry.types.lazy_type import LazyType
from strawberry.types.union import StrawberryUnion
from strawberry.utils.str_converters import to_camel_case
from typing_extensions import TypeIs, assert_never

from strawberry_django.fields.types import resolve_model_field_name

from .pyutils import DictTree, dicttree_insersection_differs, dicttree_merge
from .typing import get_django_definition

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable

    from django.db import models
    from django.db.models.expressions import Expression
    from django.db.models.fields import Field
    from django.db.models.fields.reverse_related import ForeignObjectRel
    from django.db.models.sql.query import Query
    from model_utils.managers import (
        InheritanceManagerMixin,
        InheritanceQuerySetMixin,
    )
    from polymorphic.models import PolymorphicModel


@functools.lru_cache
def get_model_fields(
    model: type[models.Model],
    *,
    camel_case: bool = False,
    is_input: bool = False,
    is_filter: bool = False,
) -> dict[str, Field | ForeignObjectRel]:
    """Get a list of model fields from the model."""
    fields = {}
    for f in model._meta.get_fields():
        name = cast(
            "str",
            resolve_model_field_name(f, is_input=is_input, is_filter=is_filter),
        )
        if camel_case:
            name = to_camel_case(name)
        fields[name] = f
    return fields


def get_model_field(
    model: type[models.Model],
    field_name: str,
    *,
    camel_case: bool = False,
    is_input: bool = False,
    is_filter: bool = False,
) -> Field | ForeignObjectRel | None:
    """Get a model fields from the model given its name."""
    return get_model_fields(
        model,
        camel_case=camel_case,
        is_input=is_input,
        is_filter=is_filter,
    ).get(field_name)


def get_possible_types(
    gql_type: StrawberryObjectDefinition | StrawberryType | type,
    *,
    object_definition: StrawberryObjectDefinition | None = None,
) -> Generator[type]:
    """Resolve all possible types for gql_type.

    Args:
    ----
        gql_type:
            The type to retrieve possibilities from.
        type_def:
            Optional type definition to use to resolve type vars.
            This is used internally.

    Yields:
    ------
        All possibilities for the type

    """
    if isinstance(gql_type, StrawberryObjectDefinition):
        yield from get_possible_types(gql_type.origin, object_definition=gql_type)
    elif isinstance(gql_type, LazyType):
        yield from get_possible_types(gql_type.resolve_type())
    elif isinstance(gql_type, StrawberryTypeVar) and object_definition is not None:
        resolved = object_definition.type_var_map.get(gql_type.type_var.__name__, None)
        if resolved is not None:
            yield from get_possible_types(resolved)
    elif isinstance(gql_type, StrawberryContainer):
        yield from get_possible_types(gql_type.of_type)
    elif isinstance(gql_type, StrawberryUnion):
        yield from itertools.chain.from_iterable(
            (get_possible_types(t) for t in gql_type.types),
        )
    elif isinstance(gql_type, StrawberryType):
        # Nothing to return here
        pass
    elif isinstance(gql_type, type):
        yield gql_type
    else:
        assert_never(gql_type)


def get_possible_type_definitions(
    gql_type: StrawberryObjectDefinition | StrawberryType | type,
) -> Generator[StrawberryObjectDefinition]:
    """Resolve all possible type definitions for gql_type.

    Args:
    ----
        gql_type:
            The type to retrieve possibilities from.

    Yields:
    ------
        All possibilities for the type

    """
    if isinstance(gql_type, StrawberryObjectDefinition):
        yield gql_type
        return

    for t in get_possible_types(gql_type):
        if isinstance(t, StrawberryObjectDefinition):
            yield t
        elif has_object_definition(t):
            yield t.__strawberry_definition__


try:
    # Can't import PolymorphicModel, because it requires Django Apps to be ready
    # Import polymorphic instead to check for its existence
    import polymorphic  # noqa: F401

    def is_polymorphic_model(v: type) -> TypeIs[type[PolymorphicModel]]:
        return getattr(v, "polymorphic_model_marker", False) is True

except ImportError:

    def is_polymorphic_model(v: type) -> TypeIs[type[PolymorphicModel]]:
        return False


try:
    from model_utils.managers import InheritanceManagerMixin, InheritanceQuerySetMixin

    def is_inheritance_manager(
        v: Any,
    ) -> TypeIs[InheritanceManagerMixin]:
        return isinstance(v, InheritanceManagerMixin)

    def is_inheritance_qs(
        v: Any,
    ) -> TypeIs[InheritanceQuerySetMixin]:
        return isinstance(v, InheritanceQuerySetMixin)

except ImportError:

    def is_inheritance_manager(
        v: Any,
    ) -> TypeIs[InheritanceManagerMixin]:
        return False

    def is_inheritance_qs(
        v: Any,
    ) -> TypeIs[InheritanceQuerySetMixin]:
        return False


def _can_optimize_subtypes(model: type[models.Model]) -> bool:
    return is_polymorphic_model(model) or is_inheritance_manager(model._default_manager)


_interfaces: weakref.WeakKeyDictionary[
    Schema,
    dict[StrawberryObjectDefinition, list[StrawberryObjectDefinition]],
] = weakref.WeakKeyDictionary()


def get_possible_concrete_types(
    model: type[models.Model],
    schema: Schema,
    strawberry_type: StrawberryObjectDefinition | StrawberryType,
) -> Iterable[StrawberryObjectDefinition]:
    """Return the object definitions the optimizer should look at when optimizing a model.

    Returns any object definitions attached to either the model or one of its supertypes.

    If the model is one that supports polymorphism, by returning subtypes from its queryset, subtypes are also
    looked at. Currently, this is supported for django-polymorphic and django-model-utils InheritanceManager.
    """
    for object_definition in get_possible_type_definitions(strawberry_type):
        if not object_definition.is_interface:
            yield object_definition
            continue

        schema_interfaces = _interfaces.setdefault(schema, {})
        interface_definitions = schema_interfaces.get(object_definition)
        if interface_definitions is None:
            interface_definitions = []
            for t in schema.schema_converter.type_map.values():
                t_definition = t.definition
                if isinstance(t_definition, StrawberryObjectDefinition) and issubclass(
                    t_definition.origin, object_definition.origin
                ):
                    interface_definitions.append(t_definition)

            schema_interfaces[object_definition] = interface_definitions

        for interface_definition in interface_definitions:
            dj_definition = get_django_definition(interface_definition.origin)
            if dj_definition and (
                issubclass(model, dj_definition.model)
                or (
                    _can_optimize_subtypes(model)
                    and issubclass(dj_definition.model, model)
                )
            ):
                yield interface_definition


@dataclasses.dataclass(eq=True)
class PrefetchInspector:
    """Prefetch hints."""

    prefetch: Prefetch
    qs: QuerySet = dataclasses.field(init=False, compare=False)
    query: Query = dataclasses.field(init=False, compare=False)

    def __post_init__(self):
        self.qs = cast("QuerySet", self.prefetch.queryset)  # type: ignore
        self.query = self.qs.query

    @property
    def only(self) -> frozenset[str] | None:
        if self.query.deferred_loading[1]:
            return None
        return frozenset(self.query.deferred_loading[0])

    @only.setter
    def only(self, value: Iterable[str | None] | None):
        value = frozenset(v for v in (value or []) if v is not None)
        self.query.deferred_loading = (value, len(value) == 0)

    @property
    def defer(self) -> frozenset[str] | None:
        if not self.query.deferred_loading[1]:
            return None
        return frozenset(self.query.deferred_loading[0])

    @defer.setter
    def defer(self, value: Iterable[str | None] | None):
        value = frozenset(v for v in (value or []) if v is not None)
        self.query.deferred_loading = (value, True)

    @property
    def select_related(self) -> DictTree | None:
        if not isinstance(self.query.select_related, dict):
            return None
        return self.query.select_related

    @select_related.setter
    def select_related(self, value: DictTree | None):
        self.query.select_related = value or {}

    @property
    def prefetch_related(self) -> list[Prefetch | str]:
        return list(self.qs._prefetch_related_lookups)  # type: ignore

    @prefetch_related.setter
    def prefetch_related(self, value: Iterable[Prefetch | str] | None):
        self.qs._prefetch_related_lookups = tuple(value or [])  # type: ignore

    @property
    def annotations(self) -> dict[str, Expression]:
        return self.query.annotations

    @annotations.setter
    def annotations(self, value: dict[str, Expression] | None):
        self.query.annotations = value or {}  # type: ignore

    @property
    def extra(self) -> DictTree:
        return self.query.extra

    @extra.setter
    def extra(self, value: DictTree | None):
        self.query.extra = value or {}  # type: ignore

    @property
    def where(self) -> WhereNode:
        return self.query.where

    @where.setter
    def where(self, value: WhereNode | None):
        self.query.where = value or WhereNode()

    def merge(self, other: PrefetchInspector, *, allow_unsafe_ops: bool = False):
        if not allow_unsafe_ops and self.where != other.where:
            raise ValueError(
                "Tried to prefetch 2 queries with different filters to the "
                "same attribute. Use `to_attr` in this case...",
            )

        # Merge select_related
        self.select_related = dicttree_merge(
            self.select_related or {},
            other.select_related or {},
        )

        # Merge only/deferred
        if not allow_unsafe_ops and (self.defer is None) != (other.defer is None):
            raise ValueError(
                "Tried to prefetch 2 queries with different deferred "
                "operations. Use only `only` or `deferred`, not both...",
            )
        if self.only is not None and other.only is not None:
            self.only |= other.only
        elif self.defer is not None and other.defer is not None:
            self.defer |= other.defer
        else:
            # One has defer, the other only. In this case, defer nothing
            self.defer = frozenset()

        # Merge annotations
        s_annotations = self.annotations
        o_annotations = other.annotations
        if not allow_unsafe_ops:
            for k in set(s_annotations) & set(o_annotations):
                if s_annotations[k] != o_annotations[k]:
                    raise ValueError(
                        "Tried to prefetch 2 queries with overlapping annotations.",
                    )
        self.annotations = {**s_annotations, **o_annotations}

        # Merge extra
        s_extra = self.extra
        o_extra = other.extra
        if not allow_unsafe_ops and dicttree_insersection_differs(s_extra, o_extra):
            raise ValueError("Tried to prefetch 2 queries with overlapping extras.")
        self.extra = {**s_extra, **o_extra}

        prefetch_related: dict[str, str | Prefetch] = {}
        for p in itertools.chain(self.prefetch_related, other.prefetch_related):
            if isinstance(p, str):
                if p not in prefetch_related:
                    prefetch_related[p] = p
                continue

            path = p.prefetch_to
            existing = prefetch_related.get(path)
            if not existing or isinstance(existing, str):
                prefetch_related[path] = p
                continue

            inspector = self.__class__(existing).merge(PrefetchInspector(p))
            prefetch_related[path] = inspector.prefetch

        self.prefetch_related = prefetch_related

        return self
