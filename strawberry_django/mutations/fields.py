from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, Mapping, TypeVar

from django.db import models, transaction
from strawberry import UNSET

from strawberry_django import utils
from strawberry_django.arguments import argument
from strawberry_django.fields.field import (
    StrawberryDjangoFieldBase,
    StrawberryDjangoFieldFilters,
)
from strawberry_django.fields.types import (
    ManyToManyInput,
    ManyToOneInput,
    OneToManyInput,
)
from strawberry_django.resolvers import django_resolver

if TYPE_CHECKING:
    from strawberry.arguments import StrawberryArgument
    from strawberry.type import StrawberryType
    from strawberry.types import Info
    from typing_extensions import Self

    from strawberry_django.utils import (
        WithStrawberryDjangoObjectDefinition,
    )


class DjangoMutationBase(StrawberryDjangoFieldBase):
    def __init__(self, input_type: type | None = None, **kwargs):
        if input_type is not None and not utils.has_django_definition(input_type):
            raise TypeError("input_type needs to be a strawberry django input")

        self.input_type = input_type
        super().__init__(**kwargs)

    @property
    def arguments(self):
        if (
            self.input_type
            and self.django_model
            != self.input_type.__strawberry_django_definition__.model
        ):
            raise TypeError(
                "Input and output types should be from the same Django model",
            )

        arguments = []
        if self.input_type:
            arguments.append(
                argument(
                    "data",
                    self.input_type,
                    is_list=self.is_list and isinstance(self, DjangoCreateMutation),
                ),
            )

        return arguments + super().arguments

    @arguments.setter
    def arguments(self, value: list[StrawberryArgument]):
        args_prop = super(DjangoMutationBase, self.__class__).arguments
        return args_prop.fset(self, value)  # type: ignore

    def copy_with(
        self,
        type_var_map: Mapping[TypeVar, StrawberryType | type],
    ) -> Self:
        new_field = super().copy_with(type_var_map)
        new_field.input_type = self.input_type
        return new_field


class DjangoCreateMutation(DjangoMutationBase):
    def create(self, data: type):
        assert self.input_type is not None
        input_data = get_input_data(self.input_type, data)
        assert self.django_model
        instance = self.django_model._default_manager.create(**input_data)
        update_m2m([instance], data)
        return instance

    @django_resolver
    @transaction.atomic
    def resolver(
        self,
        source: Any,
        info: Info,
        args: list[Any],
        kwargs: dict[str, Any],
    ) -> Any:
        data: list[Any] | Any = kwargs["data"]

        if self.is_list:
            assert isinstance(data, list)
            return [self.create(d) for d in data]

        assert not isinstance(data, list)
        return self.create(data)


class DjangoUpdateMutation(DjangoMutationBase, StrawberryDjangoFieldFilters):
    @django_resolver
    @transaction.atomic
    def resolver(
        self,
        source: Any,
        info: Info,
        args: list[Any],
        kwargs: dict[str, Any],
    ) -> Any:
        assert self.input_type is not None
        data: Any = kwargs["data"]
        assert self.django_model
        queryset = self.django_model._default_manager.all()
        queryset = self.get_queryset(queryset=queryset, info=info, **kwargs)
        input_data = get_input_data(self.input_type, data)
        queryset.update(**input_data)
        update_m2m(queryset, data)
        return queryset


class DjangoDeleteMutation(DjangoMutationBase, StrawberryDjangoFieldFilters):
    @django_resolver
    @transaction.atomic
    def resolver(
        self,
        source: Any,
        info: Info,
        args: list[Any],
        kwargs: dict[str, Any],
    ) -> Any:
        assert self.django_model
        queryset = self.django_model._default_manager.all()
        queryset = self.get_queryset(queryset=queryset, info=info, **kwargs)
        instances = list(queryset)
        queryset.delete()
        return instances


def get_input_data(input_type: type[WithStrawberryDjangoObjectDefinition], data: Any):
    input_data = {}
    for field in input_type.__strawberry_definition__.fields:
        value = getattr(data, field.name)
        if value is UNSET or isinstance(value, (ManyToOneInput, ManyToManyInput)):
            continue

        if isinstance(value, OneToManyInput):
            value = value.set

        fname = getattr(field, "django_name", None) or field.python_name or field.name
        input_data[fname] = value

    return input_data


def update_m2m(queryset: Iterable[models.Model], data: Any):
    for field_name, field_value in vars(data).items():
        if not isinstance(field_value, (ManyToOneInput, ManyToManyInput)):
            continue

        for instance in queryset:
            f = getattr(instance, field_name)
            if field_value.set is not UNSET:
                if field_value.add:
                    raise ValueError("'add' cannot be used together with 'set'")
                if field_value.remove:
                    raise ValueError("'remove' cannot be used together with 'set'")

                values = field_value.set
                if values and isinstance(field_value, ManyToOneInput):
                    values = [f.model._default_manager.get(pk=pk) for pk in values]
                if values:
                    f.set(values)
                else:
                    f.clear()
            else:
                if field_value.add:
                    values = field_value.add
                    if isinstance(field_value, ManyToOneInput):
                        values = [f.model.objects.get(pk=pk) for pk in values]
                    f.add(*values)
                if field_value.remove:
                    values = field_value.remove
                    if isinstance(field_value, ManyToOneInput):
                        values = [f.model.objects.get(pk=pk) for pk in values]
                    f.remove(*values)
