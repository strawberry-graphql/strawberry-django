from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, TypeVar, cast

from strawberry import LazyType, relay
from strawberry.annotation import StrawberryAnnotation
from strawberry.auto import StrawberryAuto
from strawberry.field import UNRESOLVED, StrawberryField
from strawberry.type import (
    StrawberryContainer,
    StrawberryList,
    StrawberryOptional,
    StrawberryType,
    WithStrawberryObjectDefinition,
    get_object_definition,
)
from strawberry.union import StrawberryUnion
from strawberry.utils.cached_property import cached_property

from strawberry_django.resolvers import django_resolver
from strawberry_django.utils.typing import (
    WithStrawberryDjangoObjectDefinition,
    get_django_definition,
    has_django_definition,
    unwrap_type,
)

if TYPE_CHECKING:
    from django.db import models
    from strawberry.object_type import StrawberryObjectDefinition
    from strawberry.types import Info
    from typing_extensions import Literal, Self

    from strawberry_django.type import StrawberryDjangoDefinition

_QS = TypeVar("_QS", bound="models.QuerySet")


class StrawberryDjangoFieldBase(StrawberryField):
    def __init__(
        self,
        django_name: str | None = None,
        graphql_name: str | None = None,
        python_name: str | None = None,
        **kwargs,
    ):
        self.is_relation = False
        self.django_name = django_name
        self.origin_django_type: StrawberryDjangoDefinition[Any, Any] | None = None
        super().__init__(graphql_name=graphql_name, python_name=python_name, **kwargs)

    def __copy__(self) -> Self:
        new_field = super().__copy__()
        new_field.django_name = self.django_name
        new_field.is_relation = self.is_relation
        new_field.origin_django_type = self.origin_django_type
        return new_field

    @property
    def is_basic_field(self) -> bool:
        """Mark this field as not basic.

        All StrawberryDjango fields define a custom resolver that needs to be
        run, so always return False here.
        """
        return False

    @cached_property
    def django_type(self) -> type[WithStrawberryDjangoObjectDefinition] | None:
        origin = self.type

        object_definition = get_object_definition(origin)

        if object_definition and issubclass(object_definition.origin, relay.Connection):
            origin = object_definition.type_var_map.get(cast(TypeVar, relay.NodeType))

            if origin is None:
                specialized_type_var_map = (
                    object_definition.specialized_type_var_map or {}
                )

                origin = specialized_type_var_map[cast(TypeVar, relay.NodeType)]

            if isinstance(origin, LazyType):
                origin = origin.resolve_type()

        origin = unwrap_type(origin)
        if isinstance(origin, LazyType):
            origin = origin.resolve_type()

        if isinstance(origin, StrawberryUnion):
            origin_list: list[type[WithStrawberryDjangoObjectDefinition]] = []
            for t in origin.types:
                while isinstance(t, StrawberryContainer):
                    t = t.of_type  # noqa: PLW2901

                if has_django_definition(t):
                    origin_list.append(t)

            origin = origin_list[0] if len(origin_list) == 1 else None

        return origin if has_django_definition(origin) else None

    @cached_property
    def django_model(self) -> type[models.Model] | None:
        django_type = self.django_type
        return (
            django_type.__strawberry_django_definition__.model
            if django_type is not None
            else None
        )

    @cached_property
    def is_optional(self) -> bool:
        return isinstance(self.type, StrawberryOptional)

    @cached_property
    def is_list(self) -> bool:
        type_ = self.type
        if isinstance(type_, StrawberryOptional):
            type_ = type_.of_type

        return isinstance(type_, StrawberryList)

    @cached_property
    def is_connection(self) -> bool:
        type_ = self.type
        if isinstance(type_, StrawberryOptional):
            type_ = type_.of_type

        return isinstance(type_, type) and issubclass(type_, relay.Connection)

    @cached_property
    def safe_resolver(self):
        resolver = self.base_resolver
        assert resolver

        if not resolver.is_async:
            resolver = django_resolver(resolver, qs_hook=None)

        return resolver

    def resolve_type(
        self,
        *,
        type_definition: StrawberryObjectDefinition | None = None,
    ) -> (
        StrawberryType
        | type[WithStrawberryObjectDefinition]
        | Literal[UNRESOLVED]  # type: ignore
    ):
        resolved = super().resolve_type(type_definition=type_definition)
        if resolved is UNRESOLVED:
            return resolved

        resolved_django_type = get_django_definition(unwrap_type(resolved))

        if self.origin_django_type and (
            # FIXME: Why does this come as Any sometimes when using future annotations?
            resolved is Any
            or isinstance(resolved, StrawberryAuto)
            # If the resolved type is an input but the origin is not, or vice versa,
            # resolve this again
            or (
                resolved_django_type
                and resolved_django_type.is_input != self.origin_django_type.is_input
            )
        ):
            from .types import get_model_field, is_optional, resolve_model_field_type

            model_field = get_model_field(
                self.origin_django_type.model,
                self.django_name or self.python_name or self.name,
            )
            resolved_type = resolve_model_field_type(
                model_field,
                self.origin_django_type,
            )
            if is_optional(
                model_field,
                self.origin_django_type.is_input,
                self.origin_django_type.is_partial,
            ):
                resolved_type = Optional[resolved_type]

            self.type_annotation = StrawberryAnnotation(resolved_type)
            resolved = super().type

        if isinstance(resolved, StrawberryAuto):
            resolved = UNRESOLVED

        return resolved

    def resolver(
        self,
        source: Any,
        info: Info,
        args: list[Any],
        kwargs: dict[str, Any],
    ) -> Any:
        return self.safe_resolver(*args, **kwargs)

    def get_result(self, source, info, args, kwargs):
        return self.resolver(info, source, args, kwargs)

    def get_queryset(self, queryset: _QS, info: Info, **kwargs) -> _QS:
        return queryset
