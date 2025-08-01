from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Any, Optional, TypeVar, cast

import django
from django.db.models import ForeignKey
from strawberry import relay
from strawberry.annotation import StrawberryAnnotation
from strawberry.types import get_object_definition
from strawberry.types.auto import StrawberryAuto
from strawberry.types.base import (
    StrawberryContainer,
    StrawberryList,
    StrawberryOptional,
    StrawberryType,
    WithStrawberryObjectDefinition,
)
from strawberry.types.field import UNRESOLVED, StrawberryField
from strawberry.types.union import StrawberryUnion
from strawberry.utils.inspect import get_specialized_type_var_map

from strawberry_django.descriptors import ModelProperty
from strawberry_django.resolvers import django_resolver
from strawberry_django.utils.typing import (
    WithStrawberryDjangoObjectDefinition,
    get_django_definition,
    has_django_definition,
    unwrap_type,
)

if TYPE_CHECKING:
    from django.db import models
    from strawberry.types import Info
    from strawberry.types.object_type import StrawberryObjectDefinition
    from typing_extensions import Literal, Self

    from strawberry_django.type import StrawberryDjangoDefinition

_QS = TypeVar("_QS", bound="models.QuerySet")

if django.VERSION >= (5, 0):
    from django.db.models import GeneratedField  # type: ignore
else:
    GeneratedField = None


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

    @functools.cached_property
    def is_async(self) -> bool:
        # Our default resolver is sync by default but will return a coroutine
        # when running ASGI. If we happen to have an extension that only supports
        # async, make sure we mark the field as async as well to support resolving
        # it properly.
        return super().is_async or any(
            e.supports_async and not e.supports_sync for e in self.extensions
        )

    @functools.cached_property
    def django_type(self) -> type[WithStrawberryDjangoObjectDefinition] | None:
        from strawberry_django.pagination import OffsetPaginated

        origin = unwrap_type(self.type)

        object_definition = get_object_definition(origin)

        if object_definition and issubclass(
            object_definition.origin, (relay.Connection, OffsetPaginated)
        ):
            origin_specialized_type_var_map = (
                get_specialized_type_var_map(cast("type", origin)) or {}
            )
            origin = origin_specialized_type_var_map.get("NodeType")

            if origin is None:
                origin = object_definition.type_var_map.get("NodeType")

            if origin is None:
                specialized_type_var_map = (
                    object_definition.specialized_type_var_map or {}
                )
                origin = specialized_type_var_map["NodeType"]

        origin = unwrap_type(origin)

        if isinstance(origin, StrawberryUnion):
            origin_list: list[type[WithStrawberryDjangoObjectDefinition]] = []
            for t in origin.types:
                while isinstance(t, StrawberryContainer):
                    t = t.of_type  # noqa: PLW2901

                if has_django_definition(t):
                    origin_list.append(t)

            origin = origin_list[0] if len(origin_list) == 1 else None

        return origin if has_django_definition(origin) else None

    @functools.cached_property
    def django_model(self) -> type[models.Model] | None:
        django_type = self.django_type
        return (
            django_type.__strawberry_django_definition__.model
            if django_type is not None
            else None
        )

    @functools.cached_property
    def is_model_property(self) -> bool:
        django_definition = self.origin_django_type
        return django_definition is not None and isinstance(
            getattr(django_definition.model, self.python_name, None), ModelProperty
        )

    @functools.cached_property
    def is_optional(self) -> bool:
        return isinstance(self.type, StrawberryOptional)

    @functools.cached_property
    def is_list(self) -> bool:
        type_ = self.type
        if isinstance(type_, StrawberryOptional):
            type_ = type_.of_type

        return isinstance(type_, StrawberryList)

    @functools.cached_property
    def is_paginated(self) -> bool:
        from strawberry_django.pagination import OffsetPaginated

        type_ = self.type
        if isinstance(type_, StrawberryOptional):
            type_ = type_.of_type

        return isinstance(type_, type) and issubclass(type_, OffsetPaginated)

    @functools.cached_property
    def is_connection(self) -> bool:
        type_ = self.type
        if isinstance(type_, StrawberryOptional):
            type_ = type_.of_type

        return isinstance(type_, type) and issubclass(type_, relay.Connection)

    @functools.cached_property
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
        StrawberryType | type[WithStrawberryObjectDefinition] | Literal[UNRESOLVED]  # type: ignore
    ):
        resolved = super().resolve_type(type_definition=type_definition)
        if resolved is UNRESOLVED:
            return resolved

        try:
            resolved_django_type = get_django_definition(unwrap_type(resolved))
        except (KeyError, ImportError):
            return UNRESOLVED

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
                (
                    model_field.target_field
                    if (
                        self.python_name.endswith("_id")
                        and isinstance(model_field, ForeignKey)
                    )
                    else model_field
                ),
                self.origin_django_type,
            )

            is_generated_field = GeneratedField is not None and isinstance(
                model_field, GeneratedField
            )
            field_to_check = (
                model_field.output_field if is_generated_field else model_field  # type: ignore
            )
            if is_optional(
                field_to_check,
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
        info: Info | None,
        args: list[Any],
        kwargs: dict[str, Any],
    ) -> Any:
        return self.safe_resolver(*args, **kwargs)

    def get_result(self, source, info, args, kwargs):
        return self.resolver(info, source, args, kwargs)

    def get_queryset(self, queryset: _QS, info: Info, **kwargs) -> _QS:
        return queryset
