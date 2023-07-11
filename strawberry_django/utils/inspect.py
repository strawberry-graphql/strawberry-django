import dataclasses
import functools
import itertools
from typing import (
    Dict,
    FrozenSet,
    Generator,
    Iterable,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

from django.db import models
from django.db.models.expressions import Expression
from django.db.models.fields import Field
from django.db.models.fields.reverse_related import ForeignObjectRel
from django.db.models.query import Prefetch, QuerySet
from django.db.models.sql.query import Query
from django.db.models.sql.where import WhereNode
from strawberry.lazy_type import LazyType
from strawberry.type import (
    StrawberryContainer,
    StrawberryType,
    StrawberryTypeVar,
    has_object_definition,
)
from strawberry.types.nodes import (
    FragmentSpread,
    InlineFragment,
    SelectedField,
    Selection,
)
from strawberry.types.types import StrawberryObjectDefinition
from strawberry.union import StrawberryUnion
from strawberry.utils.str_converters import to_camel_case
from typing_extensions import Self, assert_never

from strawberry_django.fields.types import resolve_model_field_name

from .pyutils import DictTree, dicttree_insersection_differs, dicttree_merge

_T = TypeVar("_T")
_O = TypeVar("_O", bound=type)
_M = TypeVar("_M", bound=models.Model)
_R = TypeVar("_R")


@functools.lru_cache()
def get_model_fields(
    model: Type[models.Model],
    *,
    camel_case: bool = False,
    is_input: bool = False,
    is_filter: bool = False,
) -> Dict[str, Union[Field, ForeignObjectRel]]:
    """Get a list of model fields."""
    fields = {}
    for f in model._meta.get_fields():
        name = cast(
            str,
            resolve_model_field_name(f, is_input=is_input, is_filter=is_filter),
        )
        if camel_case:
            name = to_camel_case(name)
        fields[name] = f
    return fields


def get_possible_types(
    gql_type: Union[StrawberryObjectDefinition, StrawberryType, type],
    *,
    object_definition: Optional[StrawberryObjectDefinition] = None,
) -> Generator[type, None, None]:
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
        resolved = object_definition.type_var_map.get(gql_type.type_var, None)
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
    gql_type: Union[StrawberryObjectDefinition, StrawberryType, type],
) -> Generator[StrawberryObjectDefinition, None, None]:
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


def get_selections(
    selection: Selection,
    *,
    typename: Optional[str] = None,
) -> Dict[str, SelectedField]:
    """Resolve subselections considering fragments.

    Args:
    ----
        selection:
            The selection to retrieve subselections from
        typename:
            Only resolve fragments for that typename

    Yields:
    ------
        All possibilities for the type

    """
    # Because of the way graphql spreads fragments,
    # later selections should replace previous ones
    ret: Dict[str, SelectedField] = {}

    def merge_selections(f1: SelectedField, f2: SelectedField) -> SelectedField:
        if not f1.selections:
            return f2
        if not f2.selections:
            return f1

        f1_selections = {
            s.name: s for s in f1.selections if isinstance(s, SelectedField)
        }
        f2_selections = {
            s.name: s for s in f2.selections if isinstance(s, SelectedField)
        }

        selections: dict[str, SelectedField] = {}
        for f_name in set(f1_selections) - set(f2_selections):
            selections[f_name] = f1_selections[f_name]
        for f_name in set(f2_selections) - set(f1_selections):
            selections[f_name] = f2_selections[f_name]
        for f_name in set(f2_selections) & set(f1_selections):
            selections[f_name] = f1_selections[f_name]
            selections[f_name] = merge_selections(
                f1_selections[f_name],
                f2_selections[f_name],
            )

        f1.selections = list(selections.values()) + [
            s
            for s in (f1.selections + f2.selections)
            if isinstance(s, (FragmentSpread, InlineFragment))
        ]
        return f1

    for s in selection.selections:
        if isinstance(s, SelectedField):
            # @include(if: <bool>)
            include = s.directives.get("include")
            if include and not include["if"]:
                continue

            # @skip(if: <bool>)
            skip = s.directives.get("skip")
            if skip and skip["if"]:
                continue

            f_name = s.alias or s.name
            existing = ret.get(f_name)
            if existing is not None:
                ret[f_name] = merge_selections(existing, s)
            else:
                ret[f_name] = s
        elif isinstance(s, (FragmentSpread, InlineFragment)):
            if typename is not None and s.type_condition != typename:
                continue

            for f_name, f in get_selections(s, typename=typename).items():
                existing = ret.get(f_name)
                if existing is not None:
                    ret[f_name] = merge_selections(existing, f)
                else:
                    ret[f_name] = f
        else:  # pragma:nocover
            assert_never(s)

    return ret


@dataclasses.dataclass(eq=True)
class PrefetchInspector:
    """Prefetch hints."""

    prefetch: Prefetch
    qs: QuerySet = dataclasses.field(init=False, compare=False)
    query: Query = dataclasses.field(init=False, compare=False)

    def __post_init__(self):
        self.qs = cast(QuerySet, self.prefetch.queryset)  # type: ignore
        self.query = self.qs.query

    @property
    def only(self) -> Optional[FrozenSet[str]]:
        if self.query.deferred_loading[1]:
            return None
        return frozenset(self.query.deferred_loading[0])

    @only.setter
    def only(self, value: Optional[Iterable[Optional[str]]]):
        value = frozenset(v for v in (value or []) if v is not None)
        self.query.deferred_loading = (value, len(value) == 0)

    @property
    def defer(self) -> Optional[FrozenSet[str]]:
        if not self.query.deferred_loading[1]:
            return None
        return frozenset(self.query.deferred_loading[0])

    @defer.setter
    def defer(self, value: Optional[Iterable[Optional[str]]]):
        value = frozenset(v for v in (value or []) if v is not None)
        self.query.deferred_loading = (value, True)

    @property
    def select_related(self) -> Optional[DictTree]:
        if not isinstance(self.query.select_related, dict):
            return None
        return self.query.select_related

    @select_related.setter
    def select_related(self, value: Optional[DictTree]):
        self.query.select_related = value or {}

    @property
    def prefetch_related(self) -> List[Union[Prefetch, str]]:
        return list(self.qs._prefetch_related_lookups)  # type: ignore

    @prefetch_related.setter
    def prefetch_related(self, value: Optional[Iterable[Union[Prefetch, str]]]):
        self.qs._prefetch_related_lookups = tuple(value or [])  # type: ignore

    @property
    def annotations(self) -> Dict[str, Expression]:
        return self.query.annotations

    @annotations.setter
    def annotations(self, value: Optional[Dict[str, Expression]]):
        self.query.annotations = value or {}  # type: ignore

    @property
    def extra(self) -> DictTree:
        return self.query.extra

    @extra.setter
    def extra(self, value: Optional[DictTree]):
        self.query.extra = value or {}  # type: ignore

    @property
    def where(self) -> WhereNode:
        return self.query.where

    @where.setter
    def where(self, value: Optional[WhereNode]):
        self.query.where = value or WhereNode()

    def merge(self, other: Self, *, allow_unsafe_ops: bool = False):
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
            self.only = self.only | other.only
        elif self.defer is not None and other.defer is not None:
            self.defer = self.defer | other.defer
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

        prefetch_related: Dict[str, Union[str, Prefetch]] = {}
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
