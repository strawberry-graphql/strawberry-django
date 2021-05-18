import strawberry
from django.db import models
from strawberry.arguments import UNSET, convert_arguments
from strawberry.field import StrawberryField
from .. import utils
from ..resolvers import django_resolver
from ..filters import StrawberryDjangoFieldFilters
from ..ordering import StrawberryDjangoFieldOrdering
from ..pagination import StrawberryDjangoPagination


class StrawberryDjangoFieldBase:
    def get_queryset(self, queryset, info, **kwargs):
        type_ = self.type or self.child.type
        get_queryset = getattr(type_, 'get_queryset', None)
        if get_queryset:
            queryset = get_queryset(self, queryset, info, **kwargs)
        return queryset

    @property
    def django_model(self):
        type_ = self.type or self.child.type
        return utils.get_django_model(type_)


class StrawberryDjangoField(
        StrawberryDjangoFieldOrdering,
        StrawberryDjangoFieldFilters,
        StrawberryDjangoPagination,
        StrawberryDjangoFieldBase,
        StrawberryField):

    def __init__(self, django_name=None, graphql_name=None, python_name=None, **kwargs):
        self.django_name = django_name
        self.is_auto = utils.is_auto(kwargs.get('type_', None))
        self.is_relation = False
        self.origin_django_type = None
        self.input_type = None # only mutations have input type
        super().__init__(graphql_name=graphql_name, python_name=python_name, **kwargs)

    @classmethod
    def from_field(cls, field, django_type):
        if utils.is_strawberry_django_field(field) and not field.origin_django_type:
            return field

        default_value = getattr(field, 'default_value', getattr(field, 'default', UNSET))
        new_field = StrawberryDjangoField(
            base_resolver=getattr(field, 'base_resolver', None),
            default_factory=field.default_factory,
            default_value=default_value,
            django_name=getattr(field, 'django_name', field.name),
            graphql_name=getattr(field, 'graphql_name', None),
            python_name=field.name,
            type_=field.type,
        )
        new_field.is_auto = getattr(field, 'is_auto', False)
        new_field.origin_django_type = getattr(field, 'origin_django_type', None)
        return new_field

    def get_result(self, source, info, kwargs):
        if self.base_resolver:
            args, kwargs = self._get_arguments(source=source, info=info, kwargs=kwargs)
            return self.base_resolver(*args, **kwargs)
        return self.get_django_result(kwargs, info, source)

    @django_resolver
    def get_django_result(self, kwargs, info, source):
        kwargs = convert_arguments(kwargs, self.arguments)
        return self.resolver(info=info, source=source, **kwargs)

    def resolver(self, info, source, **kwargs):
        if source is None:
            #TODO: would there be better and safer way to detect root?
            # root query object
            result = self.django_model.objects.all()

        else:
            # relation model field
            result = getattr(source, self.django_name or self.python_name)
            if isinstance(result, models.manager.Manager):
                result = result.all()

        if isinstance(result, models.QuerySet):
            result = self.get_queryset(queryset=result, info=info, **kwargs)

            if not self.is_list:
                result = result.get()

        return result


def field(resolver=None, *, name=None, field_name=None, filters=UNSET, default=UNSET, **kwargs):
    field_ = StrawberryDjangoField(
        python_name=None,
        graphql_name=name,
        type_=None,
        filters=filters,
        django_name=field_name,
        default_value=default,
        **kwargs
    )
    if resolver:
        resolver = django_resolver(resolver)
        return field_(resolver)
    return field_
