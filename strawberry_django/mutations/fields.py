from typing import List

from django.db import transaction
from strawberry import UNSET
from strawberry.annotation import StrawberryAnnotation
from strawberry.arguments import StrawberryArgument
from strawberry.type import StrawberryList, StrawberryOptional

from strawberry_django import utils
from strawberry_django.fields.field import (
    StrawberryDjangoFieldBase,
    StrawberryDjangoFieldFilters,
    StrawberryField,
)
from strawberry_django.fields.types import (
    ManyToManyInput,
    ManyToOneInput,
    OneToManyInput,
)
from strawberry_django.resolvers import django_resolver


class DjangoMutationBase:
    def __init__(self, input_type, **kwargs):
        self.input_type = input_type
        super().__init__(
            graphql_name=None,
            python_name=None,
            type_annotation=None,
            **kwargs,
        )

    @property
    def is_optional(self):
        return isinstance(self.type, StrawberryOptional)

    @property
    def is_list(self):
        return isinstance(self.type, StrawberryList) or (
            self.is_optional and isinstance(self.type.of_type, StrawberryList)
        )

    @property
    def arguments(self):
        if self.input_type:
            assert self.django_model == utils.get_django_model(
                self.input_type,
            ), "Input and output types should be from the same Django model"

        arguments = []
        if self.input_type:
            is_list = self.is_list and isinstance(self, DjangoCreateMutation)
            arguments.append(get_argument("data", self.input_type, is_list))
        return arguments + super().arguments

    @django_resolver
    def get_result(self, source, info, args, kwargs):
        return self.resolver(info, source, *args, **kwargs)

    @property
    def is_basic_field(self) -> bool:
        """Mark this field as not basic.

        All StrawberryDjango fields define a custom resolver that needs to be
        run, so always return False here.
        """
        return False


class DjangoCreateMutation(
    DjangoMutationBase,
    StrawberryDjangoFieldBase,
    StrawberryField,
):
    def create(self, data):
        input_data = get_input_data(self.input_type, data)
        instance = self.django_model.objects.create(**input_data)
        update_m2m([instance], data)
        return instance

    @transaction.atomic
    def resolver(self, info, source, data):
        if self.is_list:
            return [self.create(d) for d in data]

        return self.create(data)


class DjangoUpdateMutation(
    DjangoMutationBase,
    StrawberryDjangoFieldFilters,
    StrawberryDjangoFieldBase,
    StrawberryField,
):
    @transaction.atomic
    def resolver(self, info, source, data, **kwargs):
        queryset = self.django_model.objects.all()
        queryset = self.get_queryset(queryset=queryset, info=info, data=data, **kwargs)
        input_data = get_input_data(self.input_type, data)
        queryset.update(**input_data)
        update_m2m(queryset, data)
        return queryset


class DjangoDeleteMutation(
    DjangoMutationBase,
    StrawberryDjangoFieldFilters,
    StrawberryDjangoFieldBase,
    StrawberryField,
):
    @transaction.atomic
    def resolver(self, info, source, **kwargs):
        queryset = self.django_model.objects.all()
        queryset = self.get_queryset(queryset=queryset, info=info, **kwargs)
        instances = list(queryset)
        queryset.delete()
        return instances


def get_argument(name, type_, is_list=False):
    annotation = StrawberryAnnotation(List[type_] if is_list else type_)
    return StrawberryArgument(
        python_name=name,
        graphql_name=name,
        type_annotation=annotation,
    )


def get_input_data(input_type, data):
    input_data = {}
    for field in input_type._type_definition.fields:
        value = getattr(data, field.name)
        if isinstance(value, (ManyToOneInput, ManyToManyInput)):
            continue
        if value is UNSET:
            continue
        if isinstance(value, OneToManyInput):
            value = value.set
        input_data[field.django_name] = value
    return input_data


def update_m2m(queryset, data):
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
                if isinstance(field_value, ManyToOneInput):
                    values = [f.model.objects.get(pk=pk) for pk in values]
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
