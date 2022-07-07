from typing import Any

from django.db import models
from strawberry import UNSET
from strawberry.annotation import StrawberryAnnotation
from strawberry.field import StrawberryField
from strawberry.type import StrawberryList, StrawberryOptional

from .. import utils
from ..filters import StrawberryDjangoFieldFilters
from ..ordering import StrawberryDjangoFieldOrdering
from ..pagination import StrawberryDjangoPagination
from ..resolvers import django_resolver


class StrawberryDjangoFieldBase:
    def get_queryset(self, queryset, info, **kwargs):
        return queryset

    @property
    def django_model(self):
        type_ = utils.unwrap_type(self.type)
        return utils.get_django_model(type_)

    @classmethod
    def from_field(cls, field, django_type):
        raise NotImplementedError


class StrawberryDjangoField(
    StrawberryDjangoPagination,
    StrawberryDjangoFieldOrdering,
    StrawberryDjangoFieldFilters,
    StrawberryDjangoFieldBase,
    StrawberryField,
):
    """Basic field

    StrawberryDjangoField inherits all features from StrawberryField and
    implements Django specific functionalities like ordering, filtering and
    pagination.

    This field takes care of that Django ORM is always accessed from sync
    context. Resolver function is wrapped in sync_to_async decorator in async
    context. See more information about that from Django documentation.
    https://docs.djangoproject.com/en/3.2/topics/async/

    StrawberryDjangoField has following properties
    * django_name - django name which is used to access the field of model instance
    * is_auto - True if original field type was auto
    * is_relation - True if field is resolving django model relationship
    * origin_django_type - pointer to the origin of this field
    * input_type - input_type of this field used by mutations

    kwargs argument is passed to ordering, filtering, pagination and
    StrawberryField super classes.
    """

    def __init__(self, django_name=None, graphql_name=None, python_name=None, **kwargs):
        self.django_name = django_name
        self.is_auto = utils.is_auto(kwargs.get("type_annotation", None))
        self.is_relation = False
        self.origin_django_type = None
        self.input_type = None  # used by mutations
        super().__init__(graphql_name=graphql_name, python_name=python_name, **kwargs)

    @property
    def is_optional(self):
        return isinstance(self.type, StrawberryOptional)

    @property
    def is_list(self):
        return isinstance(self.type, StrawberryList) or (
            self.is_optional and isinstance(self.type.of_type, StrawberryList)
        )

    @classmethod
    def from_field(cls, field, django_type):
        if utils.is_strawberry_django_field(field) and not field.origin_django_type:
            return field

        new_field = StrawberryDjangoField(
            python_name=field.name,
            graphql_name=getattr(field, "graphql_name", None),
            type_annotation=field.type_annotation
            if hasattr(field, "type_annotation")
            else StrawberryAnnotation(field.type),
            description=getattr(field, "description", None),
            base_resolver=getattr(field, "base_resolver", None),
            permission_classes=getattr(field, "permission_classes", []),
            default=getattr(field, "default", UNSET),
            default_factory=field.default_factory,
            deprecation_reason=getattr(field, "deprecation_reason", None),
            directives=getattr(field, "directives", []),
            django_name=getattr(field, "django_name", field.name),
        )
        new_field.is_auto = getattr(field, "is_auto", False)
        new_field.origin_django_type = getattr(field, "origin_django_type", None)
        return new_field

    def get_result(self, source, info, args, kwargs):
        if self.base_resolver:
            return super().get_result(source, info, args, kwargs)
        return self.get_django_result(source, info, args, kwargs)

    @django_resolver
    def get_django_result(
        self,
        source,
        info,
        args,
        kwargs,
    ):
        return self.resolver(info=info, source=source, *args, **kwargs)

    def resolver(self, info, source, **kwargs):
        if source is None:
            # TODO: would there be better and safer way to detect root?
            # root query object
            result = self.django_model.objects.all()

        else:
            # relation model field
            result = getattr(source, self.django_name or self.python_name)

            if isinstance(result, models.manager.Manager):
                result = result.all()
            elif callable(result):
                result = result()

        if isinstance(result, models.QuerySet):
            result = self.get_queryset(queryset=result, info=info, **kwargs)

            if not self.is_list:
                result = result.get()

        return result

    def get_queryset(self, queryset, info, order=UNSET, **kwargs):
        type_ = self.type or self.child.type
        type_ = utils.unwrap_type(type_)
        get_queryset = getattr(type_, "get_queryset", None)
        if get_queryset:
            queryset = get_queryset(self, queryset, info, **kwargs)
        return super().get_queryset(queryset, info, order=order, **kwargs)


def field(
    resolver=None, *, name=None, field_name=None, filters=UNSET, default=UNSET, **kwargs
) -> Any:
    field_ = StrawberryDjangoField(
        python_name=None,
        graphql_name=name,
        type_annotation=None,
        filters=filters,
        django_name=field_name,
        default=default,
        **kwargs,
    )
    if resolver:
        resolver = django_resolver(resolver)
        return field_(resolver)
    return field_
