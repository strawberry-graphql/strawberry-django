from __future__ import annotations

import dataclasses
import inspect
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    Mapping,
    Sequence,
    TypeVar,
    cast,
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
from strawberry import UNSET, relay
from strawberry.annotation import StrawberryAnnotation
from strawberry.types.fields.resolver import StrawberryResolver
from strawberry.utils.cached_property import cached_property

from strawberry_django.arguments import argument
from strawberry_django.descriptors import ModelProperty
from strawberry_django.fields.base import StrawberryDjangoFieldBase
from strawberry_django.filters import StrawberryDjangoFieldFilters
from strawberry_django.ordering import StrawberryDjangoFieldOrdering
from strawberry_django.pagination import StrawberryDjangoPagination
from strawberry_django.relay import resolve_model_nodes
from strawberry_django.resolvers import (
    default_qs_hook,
    django_getattr,
    django_resolver,
)

if TYPE_CHECKING:
    from graphql.pyutils import AwaitableOrValue
    from strawberry import BasePermission
    from strawberry.arguments import StrawberryArgument
    from strawberry.extensions.field_extension import (
        FieldExtension,
        SyncExtensionResolver,
    )
    from strawberry.field import _RESOLVER_TYPE
    from strawberry.relay.types import NodeIterableType
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

    @cached_property
    def _need_remove_filters_argument(self):
        if not self.base_resolver or not self.is_connection:
            return False

        return not any(
            p.name == "filters" or p.kind == p.VAR_KEYWORD
            for p in self.base_resolver.signature.parameters.values()
        )

    @cached_property
    def _need_remove_order_argument(self):
        if not self.base_resolver or not self.is_connection:
            return False

        return not any(
            p.name == "order" or p.kind == p.VAR_KEYWORD
            for p in self.base_resolver.signature.parameters.values()
        )

    def get_result(
        self,
        source: models.Model | None,
        info: Info,
        args: list[Any],
        kwargs: dict[str, Any],
        *,
        _skip_base_resolver: bool = False,
    ) -> AwaitableOrValue[Any]:
        if self.base_resolver is not None and not _skip_base_resolver:
            resolver_kwargs = kwargs.copy()
            if self._need_remove_order_argument:
                resolver_kwargs.pop("order", None)
            if self._need_remove_filters_argument:
                resolver_kwargs.pop("filters", None)

            result = self.resolver(source, info, args, resolver_kwargs)
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
                if isinstance(attr, ModelProperty):
                    result = source.__dict__[attr.name]
                elif isinstance(attr, DeferredAttribute):
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
                if "info" not in kwargs:
                    kwargs["info"] = info

                return django_getattr(
                    source,
                    attname,
                    qs_hook=self.get_queryset_hook(**kwargs),
                )

        if isinstance(result, BaseManager):
            result = result.all()

        if isinstance(result, models.QuerySet):
            if "info" not in kwargs:
                kwargs["info"] = info

            result = django_resolver(
                lambda obj: obj,
                qs_hook=self.get_queryset_hook(**kwargs),
            )(result)

        return result

    def get_queryset_hook(self, info: Info, **kwargs):
        if self.is_connection:
            # We don't want to fetch results yet, those will be done by the connection
            def qs_hook(qs: models.QuerySet):
                return self.get_queryset(qs, info, **kwargs)

        elif self.is_list:

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
        type_ = self.django_type

        get_queryset = getattr(type_, "get_queryset", None)
        if get_queryset:
            queryset = get_queryset(queryset, info, **kwargs)

        return super().get_queryset(queryset, info, **kwargs)


class StrawberryDjangoConnectionExtension(relay.ConnectionExtension):
    def apply(self, field: StrawberryDjangoField) -> None:
        # NOTE: Because we have a base_resolver defined, our parents will not add
        # order/filters resolvers in here, so we need to add them by hand (unless they
        # are somewhat in there). We are not adding pagination because it doesn't make
        # sense together with a Connection
        args: dict[str, StrawberryArgument] = {
            a.python_name: a for a in field.arguments
        }

        if "filters" not in args:
            filters = field.get_filters()
            if filters not in (None, UNSET):
                args["filters"] = argument("filters", filters, is_optional=True)
        if "order" not in args:
            order = field.get_order()
            if order not in (None, UNSET):
                args["order"] = argument("order", order, is_optional=True)

        field.arguments = list(args.values())

        if field.base_resolver is None:

            @django_resolver
            def default_resolver(
                root: models.Model | None,
                info: Info,
                **kwargs: Any,
            ) -> Iterable[Any]:
                django_type = field.django_type

                if root is not None:
                    # If this is a nested field, call get_result instead because we want
                    # to retrieve the queryset from its RelatedManager
                    retval = field.get_result(
                        root,
                        info,
                        [],
                        kwargs,
                        _skip_base_resolver=True,
                    )
                else:
                    if django_type is None:
                        raise TypeError(
                            (
                                "Django connection without a resolver needs to define a"
                                " connection for one and only one django type. To use"
                                " it in a union, define your own resolver that handles"
                                " each of those"
                            ),
                        )

                    retval = resolve_model_nodes(
                        django_type,
                        info=info,
                        required=True,
                    )

                # If the type defines a custom get_queryset, use it on top
                # of the returned queryset
                get_queryset = getattr(django_type, "get_queryset", None)
                if get_queryset is not None:
                    retval = get_queryset(retval)

                return cast(Iterable[Any], retval)

            field.base_resolver = StrawberryResolver(default_resolver)

        return super().apply(field)

    def resolve(
        self,
        next_: SyncExtensionResolver,
        source: Any,
        info: Info,
        *,
        before: str | None = None,
        after: str | None = None,
        first: int | None = None,
        last: int | None = None,
        **kwargs: Any,
    ) -> Any:
        assert self.connection_type is not None
        nodes = cast(Iterable[relay.Node], next_(source, info, **kwargs))

        # We have a single resolver for both sync and async, so we need to check if
        # nodes is awaitable or not and resolve it accordingly
        if inspect.isawaitable(nodes):

            async def async_resolver():
                resolved = self.connection_type.resolve_connection(
                    await nodes,
                    info=info,
                    before=before,
                    after=after,
                    first=first,
                    last=last,
                )
                if inspect.isawaitable(resolved):
                    resolved = await resolved

                return resolved

            return async_resolver()

        return self.connection_type.resolve_connection(
            nodes,
            info=info,
            before=before,
            after=after,
            first=first,
            last=last,
        )


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


def node(
    *,
    name: str | None = None,
    is_subscription: bool = False,
    description: str | None = None,
    permission_classes: list[type[BasePermission]] | None = None,
    deprecation_reason: str | None = None,
    default: Any = dataclasses.MISSING,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: Mapping[Any, Any] | None = None,
    directives: Sequence[object] | None = (),
    graphql_type: Any | None = None,
    extensions: list[FieldExtension] = (),  # type: ignore
    # This init parameter is used by pyright to determine whether this field
    # is added in the constructor or not. It is not used to change
    # any behavior at the moment.
    init: Literal[True, False, None] = None,
) -> Any:
    """Annotate a property to create a relay query field.

    Examples
    --------
        Annotating something like this:

        >>> @strawberry.type
        >>> class X:
        ...     some_node: SomeType = relay.node(description="ABC")

        Will produce a query like this that returns `SomeType` given its id.

        ```
        query {
          someNode (id: ID) {
            id
            ...
          }
        }
        ```

    """
    extensions = [*list(extensions), relay.NodeExtension()]
    return StrawberryDjangoField(
        python_name=None,
        graphql_name=name,
        type_annotation=StrawberryAnnotation.from_annotation(graphql_type),
        description=description,
        is_subscription=is_subscription,
        permission_classes=permission_classes or [],
        deprecation_reason=deprecation_reason,
        default=default,
        default_factory=default_factory,
        metadata=metadata,
        directives=directives or (),
        extensions=extensions,
    )


@overload
def connection(
    graphql_type: type[relay.Connection[relay.NodeType]] | None = None,
    *,
    name: str | None = None,
    is_subscription: bool = False,
    description: str | None = None,
    permission_classes: list[type[BasePermission]] | None = None,
    deprecation_reason: str | None = None,
    default: Any = dataclasses.MISSING,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: Mapping[Any, Any] | None = None,
    directives: Sequence[object] | None = (),
    extensions: list[FieldExtension] = (),  # type: ignore
    filters: type | None = UNSET,
    order: type | None = UNSET,
) -> Any:
    ...


@overload
def connection(
    graphql_type: type[relay.Connection[relay.NodeType]] | None = None,
    *,
    resolver: _RESOLVER_TYPE[NodeIterableType[Any]] | None = None,
    name: str | None = None,
    is_subscription: bool = False,
    description: str | None = None,
    init: Literal[True] = True,
    permission_classes: list[type[BasePermission]] | None = None,
    deprecation_reason: str | None = None,
    default: Any = dataclasses.MISSING,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: Mapping[Any, Any] | None = None,
    directives: Sequence[object] | None = (),
    extensions: list[FieldExtension] = (),  # type: ignore
    filters: type | None = UNSET,
    order: type | None = UNSET,
) -> Any:
    ...


def connection(
    graphql_type: type[relay.Connection[relay.NodeType]] | None = None,
    *,
    resolver: _RESOLVER_TYPE[NodeIterableType[Any]] | None = None,
    name: str | None = None,
    is_subscription: bool = False,
    description: str | None = None,
    permission_classes: list[type[BasePermission]] | None = None,
    deprecation_reason: str | None = None,
    default: Any = dataclasses.MISSING,
    default_factory: Callable[..., object] | object = dataclasses.MISSING,
    metadata: Mapping[Any, Any] | None = None,
    directives: Sequence[object] | None = (),
    extensions: list[FieldExtension] = (),  # type: ignore
    filters: type | None = UNSET,
    order: type | None = UNSET,
    # This init parameter is used by pyright to determine whether this field
    # is added in the constructor or not. It is not used to change
    # any behavior at the moment.
    init: Literal[True, False, None] = None,
) -> Any:
    """Annotate a property or a method to create a relay connection field.

    Relay connections_ are mostly used for pagination purposes. This decorator
    helps creating a complete relay endpoint that provides default arguments
    and has a default implementation for the connection slicing.

    Note that when setting a resolver to this field, it is expected for this
    resolver to return an iterable of the expected node type, not the connection
    itself. That iterable will then be paginated accordingly. So, the main use
    case for this is to provide a filtered iterable of nodes by using some custom
    filter arguments.

    Examples
    --------
        Annotating something like this:

        >>> @strawberry.type
        >>> class X:
        ...     some_node: relay.Connection[SomeType] = relay.connection(
        ...         description="ABC",
        ...     )
        ...
        ...     @relay.connection(description="ABC")
        ...     def get_some_nodes(self, age: int) -> Iterable[SomeType]:
        ...         ...

        Will produce a query like this:

        ```
        query {
          someNode (
            before: String
            after: String
            first: String
            after: String
            age: Int
          ) {
            totalCount
            pageInfo {
              hasNextPage
              hasPreviousPage
              startCursor
              endCursor
            }
            edges {
              cursor
              node {
                  id
                  ...
              }
            }
          }
        }
        ```

    .. _Relay connections:
        https://relay.dev/graphql/connections.htm

    """
    extensions = [*list(extensions), StrawberryDjangoConnectionExtension()]
    f = StrawberryDjangoField(
        python_name=None,
        graphql_name=name,
        type_annotation=StrawberryAnnotation.from_annotation(graphql_type),
        description=description,
        is_subscription=is_subscription,
        permission_classes=permission_classes or [],
        deprecation_reason=deprecation_reason,
        default=default,
        default_factory=default_factory,
        metadata=metadata,
        directives=directives or (),
        filters=filters,
        order=order,
        extensions=extensions,
    )

    if resolver:
        f = f(resolver)

    return f
