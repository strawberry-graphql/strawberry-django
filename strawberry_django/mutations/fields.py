from strawberry.arguments import StrawberryArgument, UNSET, convert_arguments, is_unset
from typing import List
from asgiref.sync import sync_to_async
from ..resolvers import django_resolver
from .. import utils, types
from ..fields.field import StrawberryDjangoFieldBase, StrawberryDjangoFieldFilters, StrawberryField
from ..fields.types import OneToOneInput, OneToManyInput, ManyToOneInput, ManyToManyInput

from django.db import transaction

class DjangoMutationBase:
    def __init__(self, input_type, **kwargs):
        self.input_type = input_type
        self.many = False
        super().__init__(graphql_name=None, python_name=None, type_=None, **kwargs)

    def post_init(self):
        type_ = self.type or self.child.type
        if self.input_type:
            assert self.django_model == utils.get_django_model(self.input_type), (
                'Input and output types should be from the same Django model')

    @property
    def arguments(self):
        arguments = []
        if self.input_type:
            arguments.append(get_argument('data', self.input_type, self.many))
        return arguments + super().arguments

    @django_resolver
    def get_result(self, source, info, kwargs):
        kwargs = convert_arguments(kwargs, self.arguments)
        return self.resolver(info=info, source=source, **kwargs)

    def get_wrapped_resolver(self):
        self.post_init()
        return super().get_wrapped_resolver()


class DjangoCreateMutation(
        DjangoMutationBase,
        StrawberryDjangoFieldBase,
        StrawberryField):

    def post_init(self):
        if self.is_list:
            self.many = True
        super().post_init()

    def create(self, data):
        input_data = get_input_data(self.input_type, data)
        instance = self.django_model.objects.create(**input_data)
        update_m2m([instance], data)
        return instance

    @transaction.atomic
    def resolver(self, info, source, data):
        if self.many:
            return [self.create(d) for d in data]
        else:
            return self.create(data)


class DjangoUpdateMutation(
        DjangoMutationBase,
        StrawberryDjangoFieldFilters,
        StrawberryDjangoFieldBase,
        StrawberryField):

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
        StrawberryField):

    @transaction.atomic
    def resolver(self, info, source, **kwargs):
        queryset = self.django_model.objects.all()
        queryset = self.get_queryset(queryset=queryset, info=info, **kwargs)
        instances = list(queryset)
        queryset.delete()
        return instances


def get_argument(name, type_, is_list=False):
    if is_list:
        return StrawberryArgument(
            python_name = name,
            graphql_name = name,
            type_ = None,
            child = StrawberryArgument(graphql_name=None, python_name=None, type_=type_),
            is_list = True,
        )
    else:
        return StrawberryArgument(
            python_name = name,
            graphql_name = name,
            type_ = type_,
        )


def get_input_data(input_type, data):
    input_data = {}
    m2m_data = {}
    for field in input_type._type_definition.fields:
        value = getattr(data, field.name)
        if isinstance(value, (ManyToOneInput, ManyToManyInput)):
            continue
        if is_unset(value):
            continue
        if isinstance(value, OneToManyInput):
            value = value.set
        input_data[field.django_name] = value
    return input_data


def update_m2m(queryset, data):
    #TODO: optimize
    for field_name, field_value in vars(data).items():
        if not isinstance(field_value, (ManyToOneInput, ManyToManyInput)):
            continue

        for instance in queryset:
            f = getattr(instance, field_name)
            if not is_unset(field_value.set):
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
