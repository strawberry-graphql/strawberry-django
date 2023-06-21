from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping, Optional, TypeVar

from strawberry.annotation import StrawberryAnnotation
from strawberry.auto import StrawberryAuto
from strawberry.field import UNRESOLVED, StrawberryField
from strawberry.type import StrawberryList, StrawberryOptional, StrawberryType
from strawberry.utils.cached_property import cached_property

from strawberry_django import utils
from strawberry_django.resolvers import django_resolver

if TYPE_CHECKING:
    from django.db import models
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

    @property
    def is_basic_field(self) -> bool:
        """Mark this field as not basic.

        All StrawberryDjango fields define a custom resolver that needs to be
        run, so always return False here.
        """
        return False

    @property
    def type(  # noqa: A003
        self,
    ) -> StrawberryType | type | Literal[UNRESOLVED]:  # type: ignore
        resolved = super().type
        if resolved is UNRESOLVED:
            return resolved

        if (
            # FIXME: Why does this come as Any sometimes when using future annotations?
            resolved is Any
            or isinstance(resolved, StrawberryAuto)
        ) and self.origin_django_type:
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

        return resolved

    @type.setter
    def type(self, type_: Any) -> None:  # noqa: A003
        super(StrawberryDjangoFieldBase, self.__class__).type.fset(  # type: ignore
            self,
            type_,
        )

    @cached_property
    def django_model(self) -> type[models.Model] | None:
        type_ = utils.unwrap_type(self.type)
        if utils.has_django_definition(type_):
            return type_.__strawberry_django_definition__.model
        return None

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
    def safe_resolver(self):
        resolver = self.base_resolver
        assert resolver

        if not resolver.is_async:
            resolver = django_resolver(resolver)

        return resolver

    def copy_with(
        self,
        type_var_map: Mapping[TypeVar, StrawberryType | type],
    ) -> Self:
        new_field = super().copy_with(type_var_map)
        new_field.django_name = self.django_name
        new_field.is_relation = self.is_relation
        new_field.origin_django_type = self.origin_django_type
        return new_field

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
