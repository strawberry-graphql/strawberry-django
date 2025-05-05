from __future__ import annotations

import dataclasses
import inspect
import warnings
from collections.abc import (
    AsyncIterable,
    AsyncIterator,
    Callable,
    Iterable,
    Iterator,
    Mapping,
    Sequence,
)
from functools import cached_property
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    Union,
    cast,
    overload,
)

from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.fields.files import FileDescriptor
from django.db.models.fields.related import (
    ForwardManyToOneDescriptor,
    ReverseManyToOneDescriptor,
    ReverseOneToOneDescriptor,
)
from django.db.models.manager import BaseManager
from django.db.models.query import MAX_GET_RESULTS  # type: ignore
from django.db.models.query_utils import DeferredAttribute
from strawberry import UNSET, relay
from strawberry.annotation import StrawberryAnnotation
from strawberry.extensions.field_extension import FieldExtension
from strawberry.types.field import _RESOLVER_TYPE  # noqa: PLC2701
from strawberry.types.fields.resolver import StrawberryResolver
from strawberry.types.info import Info
from strawberry.utils.await_maybe import await_maybe
from typing_extensions import TypeAlias

from strawberry_django import optimizer
from strawberry_django.arguments import argument
from strawberry_django.descriptors import ModelProperty
from strawberry_django.fields.base import StrawberryDjangoFieldBase
from strawberry_django.filters import FILTERS_ARG, StrawberryDjangoFieldFilters
from strawberry_django.optimizer import OptimizerStore, is_optimized_by_prefetching
from strawberry_django.ordering import (
    ORDER_ARG,
    ORDERING_ARG,
    StrawberryDjangoFieldOrdering,
)
from strawberry_django.pagination import (
    PAGINATION_ARG,
    OffsetPaginated,
    OffsetPaginationInput,
    StrawberryDjangoPagination,
)
from strawberry_django.permissions import filter_with_perms
from strawberry_django.queryset import run_type_get_queryset
from strawberry_django.relay import resolve_model_nodes
from strawberry_django.resolvers import (
    default_qs_hook,
    django_getattr,
    django_resolver,
    resolve_base_manager,
)

if TYPE_CHECKING:
    from graphql.pyutils import AwaitableOrValue
    from strawberry import BasePermission
    from strawberry.extensions.field_extension import SyncExtensionResolver
    from strawberry.relay.types import NodeIterableType
    from strawberry.types.arguments import StrawberryArgument
    from strawberry.types.base import WithStrawberryObjectDefinition
    from strawberry.types.field import StrawberryField
    from strawberry.types.unset import UnsetType
    from typing_extensions import Literal, Self

    from strawberry_django.utils.typing import (
        AnnotateType,
        PrefetchType,
        TypeOrMapping,
        TypeOrSequence,
    )


_T = TypeVar("_T")


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

    def __init__(
        self,
        *args,
        only: TypeOrSequence[str] | None = None,
        select_related: TypeOrSequence[str] | None = None,
        prefetch_related: TypeOrSequence[PrefetchType] | None = None,
        annotate: TypeOrMapping[AnnotateType] | None = None,
        disable_optimization: bool = False,
        **kwargs,
    ):
        self.disable_optimization = disable_optimization
        self.store = OptimizerStore.with_hints(
            only=only,
            select_related=select_related,
            prefetch_related=prefetch_related,
            annotate=annotate,
        )
        # FIXME: Probably remove this when depending on graphql-core 3.3.0+
        self.disable_fetch_list_results: bool = False

        super().__init__(*args, **kwargs)

    def __copy__(self) -> Self:
        new_field = super().__copy__()
        new_field.disable_optimization = self.disable_optimization
        new_field.store = self.store.copy()
        return new_field

    @cached_property
    def _need_remove_filters_argument(self):
        if not self.base_resolver or not self.is_connection:
            return False

        return not any(
            p.name == FILTERS_ARG or p.kind == p.VAR_KEYWORD
            for p in self.base_resolver.signature.parameters.values()
        )

    @cached_property
    def _need_remove_order_argument(self):
        if not self.base_resolver or not self.is_connection:
            return False

        return not any(
            p.name == ORDER_ARG or p.kind == p.VAR_KEYWORD
            for p in self.base_resolver.signature.parameters.values()
        )

    @cached_property
    def _need_remove_ordering_argument(self):
        if not self.base_resolver or not self.is_connection:
            return False

        return not any(
            p.name == ORDERING_ARG or p.kind == p.VAR_KEYWORD
            for p in self.base_resolver.signature.parameters.values()
        )

    def get_result(
        self,
        source: models.Model | None,
        info: Info | None,
        args: list[Any],
        kwargs: dict[str, Any],
    ) -> AwaitableOrValue[Any]:
        is_awaitable = False

        if self.base_resolver is not None:
            resolver_kwargs = kwargs.copy()
            if self._need_remove_order_argument:
                resolver_kwargs.pop(ORDER_ARG, None)
            if self._need_remove_ordering_argument:
                resolver_kwargs.pop(ORDERING_ARG, None)
            if self._need_remove_filters_argument:
                resolver_kwargs.pop(FILTERS_ARG, None)

            assert info
            result = self.resolver(source, info, args, resolver_kwargs)
            is_awaitable = inspect.isawaitable(result)
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
                    # Reversed OneToOne will raise ObjectDoesNotExist when
                    # trying to access it if the relation doesn't exist.
                    except_as_none=(ObjectDoesNotExist,) if self.is_optional else None,
                    empty_file_descriptor_as_null=True,
                )
            else:
                # FileField/ImageField will always return a FileDescriptor, even when the
                # field is "null". If it is falsy (i.e. doesn't have a file) we should
                # return `None` instead.
                if isinstance(attr, FileDescriptor) and not result:
                    result = None

        if is_awaitable or self.is_async:

            async def async_resolver():
                resolved = await await_maybe(result)

                if isinstance(resolved, BaseManager):
                    resolved = resolve_base_manager(resolved)

                if isinstance(resolved, models.QuerySet):
                    if "info" not in kwargs:
                        kwargs["info"] = info

                    resolved = await sync_to_async(self.get_queryset_hook(**kwargs))(
                        resolved
                    )

                return resolved

            return async_resolver()

        if isinstance(result, BaseManager):
            result = resolve_base_manager(result)

        if isinstance(result, models.QuerySet):
            if "info" not in kwargs:
                kwargs["info"] = info

            result = django_resolver(
                self.get_queryset_hook(**kwargs),
                qs_hook=lambda qs: qs,
            )(result)

        return result

    def get_queryset_hook(self, info: Info, **kwargs):
        if self.is_connection or self.is_paginated:
            # We don't want to fetch results yet, those will be done by the connection/pagination
            def qs_hook(qs: models.QuerySet):  # type: ignore
                return self.get_queryset(qs, info, **kwargs)

        elif self.is_list:

            def qs_hook(qs: models.QuerySet):  # type: ignore
                qs = self.get_queryset(qs, info, **kwargs)
                if not self.disable_fetch_list_results:
                    qs = default_qs_hook(qs)
                return qs

        elif self.is_optional:

            def qs_hook(qs: models.QuerySet):  # type: ignore
                qs = self.get_queryset(qs, info, **kwargs)
                return qs.first()

        else:

            def qs_hook(qs: models.QuerySet):
                qs = self.get_queryset(qs, info, **kwargs)
                # Don't use qs.get() if the queryset is optimized by prefetching.
                # Calling get in that case would disregard the prefetched results, because get implicitly
                # adds a limit to the query
                if (result_cache := qs._result_cache) is not None:  # type: ignore
                    # mimic behavior of get()
                    # the queryset is already prefetched, no issue with just using len()
                    qs_len = len(result_cache)
                    if qs_len == 0:
                        raise qs.model.DoesNotExist(
                            f"{qs.model._meta.object_name} matching query does not exist."
                        )
                    if qs_len != 1:
                        raise qs.model.MultipleObjectsReturned(
                            f"get() returned more than one {qs.model._meta.object_name} -- it returned "
                            f"{qs_len if qs_len < MAX_GET_RESULTS else f'more than {qs_len - 1}'}!"
                        )
                    return result_cache[0]

                return qs.get()

        return qs_hook

    def get_queryset(self, queryset, info, **kwargs):
        # If the queryset been optimized at prefetch phase, this function has already been
        # called by the optimizer extension, meaning we don't want to call it again
        if is_optimized_by_prefetching(queryset):
            return queryset

        queryset = run_type_get_queryset(queryset, self.django_type, info)
        queryset = super().get_queryset(
            filter_with_perms(queryset, info), info, **kwargs
        )

        # If optimizer extension is enabled, optimize this queryset
        if (
            not self.disable_optimization
            and (ext := optimizer.optimizer.get()) is not None
        ):
            queryset = ext.optimize(queryset, info=info)

        return queryset


def _get_field_arguments_for_extensions(
    field: StrawberryDjangoField,
    *,
    add_filters: bool = True,
    add_order: bool = True,
    add_pagination: bool = True,
) -> list[StrawberryArgument]:
    """Get a list of arguments to be set to fields using extensions.

    Because we have a base_resolver defined in those, our parents will not add
    order/filters/pagination resolvers in here, so we need to add them by hand (unless they
    are somewhat in there). We are not adding pagination because it doesn't make
    sense together with a Connection
    """
    args: dict[str, StrawberryArgument] = {a.python_name: a for a in field.arguments}

    if add_filters and FILTERS_ARG not in args:
        filters = field.get_filters()
        if filters not in (None, UNSET):  # noqa: PLR6201
            args[FILTERS_ARG] = argument(FILTERS_ARG, filters, is_optional=True)

    if add_order and ORDER_ARG not in args:
        order = field.get_order()
        if order not in (None, UNSET):  # noqa: PLR6201
            args[ORDER_ARG] = argument(ORDER_ARG, order, is_optional=True)

    if add_order and ORDERING_ARG not in args:
        ordering = field.get_ordering()
        if ordering not in (None, UNSET):  # noqa: PLR6201
            args[ORDERING_ARG] = argument(
                ORDERING_ARG, ordering, is_list=True, default=[]
            )

    if add_pagination and PAGINATION_ARG not in args:
        pagination = field.get_pagination()
        if pagination not in (None, UNSET):  # noqa: PLR6201
            args[PAGINATION_ARG] = argument(
                PAGINATION_ARG,
                pagination,
                is_optional=True,
            )

    return list(args.values())


class StrawberryDjangoConnectionExtension(relay.ConnectionExtension):
    def apply(self, field: StrawberryField) -> None:
        if not isinstance(field, StrawberryDjangoField):
            raise TypeError(
                "The extension can only be applied to StrawberryDjangoField"
            )

        field.arguments = _get_field_arguments_for_extensions(
            field,
            add_pagination=False,
        )

        if field.base_resolver is None:

            def default_resolver(
                root: models.Model | None,
                info: Info,
                **kwargs: Any,
            ) -> Iterable[Any]:
                assert isinstance(field, StrawberryDjangoField)

                django_type = field.django_type

                if root is not None:
                    # If this is a nested field, call get_result instead because we want
                    # to retrieve the queryset from its RelatedManager
                    retval = cast(
                        "models.QuerySet",
                        getattr(root, field.django_name or field.python_name).all(),
                    )
                else:
                    if django_type is None:
                        raise TypeError(
                            "Django connection without a resolver needs to define a"
                            " connection for one and only one django type. To use"
                            " it in a union, define your own resolver that handles"
                            " each of those",
                        )

                    retval = resolve_model_nodes(
                        django_type,
                        info=info,
                        required=True,
                    )

                return cast("Iterable[Any]", retval)

            default_resolver.can_optimize = True  # type: ignore

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
        nodes = cast("Iterable[relay.Node]", next_(source, info, **kwargs))

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
                    max_results=self.max_results,
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
            max_results=self.max_results,
        )


class StrawberryOffsetPaginatedExtension(FieldExtension):
    paginated_type: type[OffsetPaginated]

    def apply(self, field: StrawberryField) -> None:
        if not isinstance(field, StrawberryDjangoField):
            raise TypeError(
                "The extension can only be applied to StrawberryDjangoField"
            )

        field.arguments = _get_field_arguments_for_extensions(field)
        self.paginated_type = cast("type[OffsetPaginated]", field.type)

    def resolve(
        self,
        next_: SyncExtensionResolver,
        source: Any,
        info: Info,
        *,
        pagination: OffsetPaginationInput | None = None,
        order: WithStrawberryObjectDefinition | None = None,
        filters: WithStrawberryObjectDefinition | None = None,
        **kwargs: Any,
    ) -> Any:
        assert self.paginated_type is not None
        queryset = cast("models.QuerySet", next_(source, info, **kwargs))

        def get_queryset(queryset):
            return cast("StrawberryDjangoField", info._field).get_queryset(
                queryset,
                info,
                pagination=pagination,
                order=order,
                filters=filters,
            )

        # We have a single resolver for both sync and async, so we need to check if
        # nodes is awaitable or not and resolve it accordingly
        if inspect.isawaitable(queryset):

            async def async_resolver(queryset=queryset):
                resolved = self.paginated_type.resolve_paginated(
                    get_queryset(await queryset),
                    info=info,
                    pagination=pagination,
                    **kwargs,
                )
                if inspect.isawaitable(resolved):
                    resolved = await resolved

                return resolved

            return async_resolver()

        return self.paginated_type.resolve_paginated(
            get_queryset(queryset),
            info=info,
            pagination=pagination,
            **kwargs,
        )


@overload
def field(
    *,
    field_cls: type[StrawberryDjangoField] = StrawberryDjangoField,
    resolver: _RESOLVER_TYPE[_T],
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
    extensions: Sequence[FieldExtension] = (),
    pagination: bool | UnsetType = UNSET,
    filters: type | UnsetType | None = UNSET,
    order: type | UnsetType | None = UNSET,
    ordering: type | UnsetType | None = UNSET,
    only: TypeOrSequence[str] | None = None,
    select_related: TypeOrSequence[str] | None = None,
    prefetch_related: TypeOrSequence[PrefetchType] | None = None,
    annotate: TypeOrMapping[AnnotateType] | None = None,
    disable_optimization: bool = False,
) -> _T: ...


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
    extensions: Sequence[FieldExtension] = (),
    pagination: bool | UnsetType = UNSET,
    filters: type | UnsetType | None = UNSET,
    order: type | UnsetType | None = UNSET,
    ordering: type | UnsetType | None = UNSET,
    only: TypeOrSequence[str] | None = None,
    select_related: TypeOrSequence[str] | None = None,
    prefetch_related: TypeOrSequence[PrefetchType] | None = None,
    annotate: TypeOrMapping[AnnotateType] | None = None,
    disable_optimization: bool = False,
) -> Any: ...


@overload
def field(
    resolver: _RESOLVER_TYPE[Any],
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
    extensions: Sequence[FieldExtension] = (),
    pagination: bool | UnsetType = UNSET,
    filters: type | UnsetType | None = UNSET,
    order: type | UnsetType | None = UNSET,
    ordering: type | UnsetType | None = UNSET,
    only: TypeOrSequence[str] | None = None,
    select_related: TypeOrSequence[str] | None = None,
    prefetch_related: TypeOrSequence[PrefetchType] | None = None,
    annotate: TypeOrMapping[AnnotateType] | None = None,
    disable_optimization: bool = False,
) -> StrawberryDjangoField: ...


def field(
    resolver: _RESOLVER_TYPE[Any] | None = None,
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
    extensions: Sequence[FieldExtension] = (),
    pagination: bool | UnsetType = UNSET,
    filters: type | UnsetType | None = UNSET,
    order: type | UnsetType | None = UNSET,
    ordering: type | UnsetType | None = UNSET,
    only: TypeOrSequence[str] | None = None,
    select_related: TypeOrSequence[str] | None = None,
    prefetch_related: TypeOrSequence[PrefetchType] | None = None,
    annotate: TypeOrMapping[AnnotateType] | None = None,
    disable_optimization: bool = False,
    # This init parameter is used by pyright to determine whether this field
    # is added in the constructor or not. It is not used to change
    # any behavior at the moment.
    init: bool | None = None,
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
        ordering=ordering,
        extensions=extensions,
        only=only,
        select_related=select_related,
        prefetch_related=prefetch_related,
        annotate=annotate,
        disable_optimization=disable_optimization,
    )

    if order:
        warnings.warn(
            "strawberry_django.order is deprecated in favor of strawberry_django.ordering.",
            DeprecationWarning,
            stacklevel=2,
        )

    if resolver:
        return f(resolver)

    return f


def node(
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
    extensions: Sequence[FieldExtension] = (),
    only: TypeOrSequence[str] | None = None,
    select_related: TypeOrSequence[str] | None = None,
    prefetch_related: TypeOrSequence[PrefetchType] | None = None,
    annotate: TypeOrMapping[AnnotateType] | None = None,
    disable_optimization: bool = False,
    # This init parameter is used by pyright to determine whether this field
    # is added in the constructor or not. It is not used to change
    # any behavior at the moment.
    init: bool | None = None,
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
    extensions = [*extensions, relay.NodeExtension()]
    return field_cls(
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
        directives=directives or (),
        extensions=extensions,
    )


@overload
def connection(
    graphql_type: type[relay.Connection[relay.NodeType]] | None = None,
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
    extensions: Sequence[FieldExtension] = (),
    max_results: int | None = None,
    filters: type | None = UNSET,
    order: type | None = UNSET,
    ordering: type | None = UNSET,
    only: TypeOrSequence[str] | None = None,
    select_related: TypeOrSequence[str] | None = None,
    prefetch_related: TypeOrSequence[PrefetchType] | None = None,
    annotate: TypeOrMapping[AnnotateType] | None = None,
    disable_optimization: bool = False,
) -> Any: ...


@overload
def connection(
    graphql_type: type[relay.Connection[relay.NodeType]] | None = None,
    *,
    field_cls: type[StrawberryDjangoField] = StrawberryDjangoField,
    resolver: _RESOLVER_TYPE[NodeIterableType[Any]] | None = None,
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
    extensions: Sequence[FieldExtension] = (),
    max_results: int | None = None,
    filters: type | None = UNSET,
    order: type | None = UNSET,
    ordering: type | None = UNSET,
    only: TypeOrSequence[str] | None = None,
    select_related: TypeOrSequence[str] | None = None,
    prefetch_related: TypeOrSequence[PrefetchType] | None = None,
    annotate: TypeOrMapping[AnnotateType] | None = None,
    disable_optimization: bool = False,
) -> Any: ...


def connection(
    graphql_type: type[relay.Connection[relay.NodeType]] | None = None,
    *,
    field_cls: type[StrawberryDjangoField] = StrawberryDjangoField,
    resolver: _RESOLVER_TYPE[NodeIterableType[Any]] | None = None,
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
    extensions: Sequence[FieldExtension] = (),
    max_results: int | None = None,
    filters: type | None = UNSET,
    order: type | None = UNSET,
    ordering: type | None = UNSET,
    only: TypeOrSequence[str] | None = None,
    select_related: TypeOrSequence[str] | None = None,
    prefetch_related: TypeOrSequence[PrefetchType] | None = None,
    annotate: TypeOrMapping[AnnotateType] | None = None,
    disable_optimization: bool = False,
    # This init parameter is used by pyright to determine whether this field
    # is added in the constructor or not. It is not used to change
    # any behavior at the moment.
    init: bool | None = None,
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
    extensions = [
        *extensions,
        StrawberryDjangoConnectionExtension(max_results=max_results),
    ]
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
        directives=directives or (),
        filters=filters,
        order=order,
        ordering=ordering,
        extensions=extensions,
        only=only,
        select_related=select_related,
        prefetch_related=prefetch_related,
        annotate=annotate,
        disable_optimization=disable_optimization,
    )

    if resolver:
        f = f(resolver)

    return f


_OFFSET_PAGINATED_RESOLVER_TYPE: TypeAlias = _RESOLVER_TYPE[
    Union[
        Iterator[models.Model],
        Iterable[models.Model],
        AsyncIterator[models.Model],
        AsyncIterable[models.Model],
    ]
]


@overload
def offset_paginated(
    graphql_type: type[OffsetPaginated] | None = None,
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
    extensions: Sequence[FieldExtension] = (),
    filters: type | None = UNSET,
    order: type | None = UNSET,
    ordering: type | None = UNSET,
    only: TypeOrSequence[str] | None = None,
    select_related: TypeOrSequence[str] | None = None,
    prefetch_related: TypeOrSequence[PrefetchType] | None = None,
    annotate: TypeOrMapping[AnnotateType] | None = None,
    disable_optimization: bool = False,
) -> Any: ...


@overload
def offset_paginated(
    graphql_type: type[OffsetPaginated] | None = None,
    *,
    field_cls: type[StrawberryDjangoField] = StrawberryDjangoField,
    resolver: _OFFSET_PAGINATED_RESOLVER_TYPE | None = None,
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
    extensions: Sequence[FieldExtension] = (),
    filters: type | None = UNSET,
    order: type | None = UNSET,
    ordering: type | None = UNSET,
    only: TypeOrSequence[str] | None = None,
    select_related: TypeOrSequence[str] | None = None,
    prefetch_related: TypeOrSequence[PrefetchType] | None = None,
    annotate: TypeOrMapping[AnnotateType] | None = None,
    disable_optimization: bool = False,
) -> Any: ...


def offset_paginated(
    graphql_type: type[OffsetPaginated] | None = None,
    *,
    field_cls: type[StrawberryDjangoField] = StrawberryDjangoField,
    resolver: _OFFSET_PAGINATED_RESOLVER_TYPE | None = None,
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
    extensions: Sequence[FieldExtension] = (),
    filters: type | None = UNSET,
    order: type | None = UNSET,
    ordering: type | None = UNSET,
    only: TypeOrSequence[str] | None = None,
    select_related: TypeOrSequence[str] | None = None,
    prefetch_related: TypeOrSequence[PrefetchType] | None = None,
    annotate: TypeOrMapping[AnnotateType] | None = None,
    disable_optimization: bool = False,
    # This init parameter is used by pyright to determine whether this field
    # is added in the constructor or not. It is not used to change
    # any behavior at the moment.
    init: bool | None = None,
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
    extensions = [*extensions, StrawberryOffsetPaginatedExtension()]
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
        directives=directives or (),
        filters=filters,
        order=order,
        ordering=ordering,
        extensions=extensions,
        only=only,
        select_related=select_related,
        prefetch_related=prefetch_related,
        annotate=annotate,
        disable_optimization=disable_optimization,
    )

    if resolver:
        f = f(resolver)

    return f
