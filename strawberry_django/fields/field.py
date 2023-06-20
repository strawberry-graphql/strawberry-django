from __future__ import annotations

import dataclasses
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Mapping,
    Sequence,
    TypeVar,
    overload,
)

from django.db import models
from django.db.models.fields.related import (
    ForwardManyToOneDescriptor,
    ReverseManyToOneDescriptor,
    ReverseOneToOneDescriptor,
)
from django.db.models.manager import BaseManager
from django.db.models.query_utils import DeferredAttribute
from strawberry import UNSET
from strawberry.annotation import StrawberryAnnotation

from strawberry_django import utils
from strawberry_django.fields.base import StrawberryDjangoFieldBase
from strawberry_django.filters import StrawberryDjangoFieldFilters
from strawberry_django.ordering import StrawberryDjangoFieldOrdering
from strawberry_django.pagination import StrawberryDjangoPagination
from strawberry_django.resolvers import (
    default_qs_hook,
    django_getattr,
    django_resolver,
)

if TYPE_CHECKING:
    from graphql.pyutils import AwaitableOrValue
    from strawberry import BasePermission
    from strawberry.extensions.field_extension import FieldExtension
    from strawberry.types.fields.resolver import StrawberryResolver
    from strawberry.types.info import Info
    from strawberry.unset import UnsetType
    from typing_extensions import Literal


_T = TypeVar("_T")
_M = TypeVar("_M", bound=models.Model)


class StrawberryDjangoField(
    StrawberryDjangoPagination,
    StrawberryDjangoFieldOrdering,
    StrawberryDjangoFieldFilters,
    StrawberryDjangoFieldBase,
):
    """Basic django field.

    StrawberryDjangoField inherits all features from StrawberryField and
    implements Django specific functionalities like ordering, filtering and
    pagination.

    This field takes care of that Django ORM is always accessed from sync
    context. Resolver function is wrapped in sync_to_async decorator in async
    context. See more information about that from Django documentation.
    https://docs.djangoproject.com/en/3.2/topics/async/

    StrawberryDjangoField has following properties
    * django_name - django name which is used to access the field of model instance
    * is_relation - True if field is resolving django model relationship
    * origin_django_type - pointer to the origin of this field

    kwargs argument is passed to ordering, filtering, pagination and
    StrawberryField super classes.
    """

    def get_result(
        self,
        source: models.Model | None,
        info: Info,
        args: list[Any],
        kwargs: dict[str, Any],
    ) -> AwaitableOrValue[Any]:
        if self.base_resolver is not None:
            result = self.resolver(source, info, args, kwargs)
        elif source is None:
            model = self.django_model
            assert model is not None
            result = model._default_manager.all()
        else:
            # Small optimization to async resolvers avoid having to call it in an
            # sync_to_async context if the value is already cached, since it will not
            # hit the db anymore
            attname = self.django_name or self.python_name
            attr = getattr(source.__class__, attname, None)
            try:
                if isinstance(attr, DeferredAttribute):
                    # If the value is cached, retrieve it with getattr because
                    # some fields wrap values at that time (e.g. FileField).
                    # If this next like fails, it will raise KeyError and get
                    # us out of the loop before we can do getattr
                    source.__dict__[attr.field.attname]
                    result = getattr(source, attr.field.attname)
                elif isinstance(attr, ForwardManyToOneDescriptor):
                    # This will raise KeyError if it is not cached
                    result = attr.field.get_cached_value(source)  # type: ignore
                elif isinstance(attr, ReverseOneToOneDescriptor):
                    # This will raise KeyError if it is not cached
                    result = attr.related.get_cached_value(source)
                elif isinstance(attr, ReverseManyToOneDescriptor):
                    # This returns a queryset, it is async safe
                    result = getattr(source, attname)
                else:
                    raise KeyError  # noqa: TRY301
            except KeyError:
                return django_getattr(
                    source,
                    attname,
                    qs_hook=self.get_queryset_hook(info, **kwargs),
                )

        if isinstance(result, BaseManager):
            result = result.all()

        if isinstance(result, models.QuerySet):
            result = django_resolver(
                lambda obj: obj,
                qs_hook=self.get_queryset_hook(info, **kwargs),
            )(result)

        return result

    def get_queryset_hook(self, info: Info, **kwargs):
        if self.is_list:

            def qs_hook(qs: models.QuerySet):  # type: ignore
                qs = self.get_queryset(qs, info, **kwargs)
                return default_qs_hook(qs)

        elif self.is_optional:

            def qs_hook(qs: models.QuerySet):
                qs = self.get_queryset(qs, info, **kwargs)
                return qs.first()

        else:

            def qs_hook(qs: models.QuerySet):
                qs = self.get_queryset(qs, info, **kwargs)
                return qs.get()

        return qs_hook

    def get_queryset(self, queryset, info, **kwargs):
        type_ = self.type
        type_ = utils.unwrap_type(type_)

        get_queryset = getattr(type_, "get_queryset", None)
        if get_queryset:
            queryset = get_queryset(queryset, info, **kwargs)

        return super().get_queryset(queryset, info, **kwargs)


@overload
def field(
    *,
    field_cls: type[StrawberryDjangoField] = StrawberryDjangoField,
    resolver: Callable[[], _T],
    name: str | None = None,
    field_name: str | None = None,
    is_subscription: bool = False,
    description: str | None = None,
    init: Literal[False] = False,
    permission_classes: list[type[BasePermission]] | None = None,
    deprecation_reason: str | None = None,
    default: Any = dataclasses.MISSING,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: Mapping[Any, Any] | None = None,
    directives: Sequence[object] | None = (),
    graphql_type: Any | None = None,
    pagination: bool | UnsetType = UNSET,
    filters: type | UnsetType | None = UNSET,
    order: type | UnsetType | None = UNSET,
    extensions: list[FieldExtension] = (),  # type: ignore
) -> _T:
    ...


@overload
def field(
    *,
    field_cls: type[StrawberryDjangoField] = StrawberryDjangoField,
    name: str | None = None,
    field_name: str | None = None,
    is_subscription: bool = False,
    description: str | None = None,
    init: Literal[True] = True,
    permission_classes: list[type[BasePermission]] | None = None,
    deprecation_reason: str | None = None,
    default: Any = dataclasses.MISSING,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: Mapping[Any, Any] | None = None,
    directives: Sequence[object] | None = (),
    graphql_type: Any | None = None,
    pagination: bool | UnsetType = UNSET,
    filters: type | UnsetType | None = UNSET,
    order: type | UnsetType | None = UNSET,
    extensions: list[FieldExtension] = (),  # type: ignore
) -> Any:
    ...


@overload
def field(
    resolver: StrawberryResolver | Callable | staticmethod | classmethod,
    *,
    field_cls: type[StrawberryDjangoField] = StrawberryDjangoField,
    name: str | None = None,
    field_name: str | None = None,
    is_subscription: bool = False,
    description: str | None = None,
    permission_classes: list[type[BasePermission]] | None = None,
    deprecation_reason: str | None = None,
    default: Any = dataclasses.MISSING,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: Mapping[Any, Any] | None = None,
    directives: Sequence[object] | None = (),
    graphql_type: Any | None = None,
    pagination: bool | UnsetType = UNSET,
    filters: type | UnsetType | None = UNSET,
    order: type | UnsetType | None = UNSET,
    extensions: list[FieldExtension] = (),  # type: ignore
) -> StrawberryDjangoField:
    ...


def field(
    resolver=None,
    *,
    field_cls: type[StrawberryDjangoField] = StrawberryDjangoField,
    name: str | None = None,
    field_name: str | None = None,
    is_subscription: bool = False,
    description: str | None = None,
    permission_classes: list[type[BasePermission]] | None = None,
    deprecation_reason: str | None = None,
    default: Any = dataclasses.MISSING,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: Mapping[Any, Any] | None = None,
    directives: Sequence[object] | None = (),
    graphql_type: Any | None = None,
    pagination: bool | UnsetType = UNSET,
    filters: type | UnsetType | None = UNSET,
    order: type | UnsetType | None = UNSET,
    extensions: list[FieldExtension] = (),  # type: ignore
    # This init parameter is used by pyright to determine whether this field
    # is added in the constructor or not. It is not used to change
    # any behavior at the moment.
    init: Literal[True, False, None] = None,
) -> Any:
    """Annotate a method or property as a Django GraphQL field.

    Examples
    --------
        It can be used both as decorator and as a normal function:

        >>> @strawberry.django.type
        >>> class X:
        ...     field_abc: str = strawberry.django.field(description="ABC")
        ...     @strawberry.django.field(description="ABC")
        ...
        ...     def field_with_resolver(self) -> str:
        ...         return "abc"

    """
    f = field_cls(
        python_name=None,
        django_name=field_name,
        graphql_name=name,
        type_annotation=StrawberryAnnotation.from_annotation(graphql_type),
        description=description,
        is_subscription=is_subscription,
        permission_classes=permission_classes or [],
        deprecation_reason=deprecation_reason,
        default=default,
        default_factory=default_factory,
        metadata=metadata,
        directives=directives,
        filters=filters,
        pagination=pagination,
        order=order,
        extensions=extensions,
    )

    if resolver:
        return f(resolver)

    return f
