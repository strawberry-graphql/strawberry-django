import copy
import dataclasses
import functools
import inspect
import sys
import types
from typing import (
    Callable,
    Collection,
    Generic,
    List,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    cast,
)

import strawberry
from django.core.exceptions import FieldDoesNotExist
from django.db.models.base import Model
from django.db.models.fields.reverse_related import ManyToManyRel, ManyToOneRel
from strawberry import UNSET, relay
from strawberry.annotation import StrawberryAnnotation
from strawberry.exceptions import (
    MissingFieldAnnotationError,
)
from strawberry.field import StrawberryField
from strawberry.private import is_private
from strawberry.type import WithStrawberryObjectDefinition, get_object_definition
from strawberry.utils.deprecations import DeprecatedDescriptor
from typing_extensions import Literal, Self, dataclass_transform

from strawberry_django.optimizer import OptimizerStore
from strawberry_django.relay import (
    resolve_model_id,
    resolve_model_id_attr,
    resolve_model_node,
    resolve_model_nodes,
)
from strawberry_django.utils.typing import (
    AnnotateType,
    PrefetchType,
    TypeOrMapping,
    TypeOrSequence,
    WithStrawberryDjangoObjectDefinition,
    get_annotations,
    is_auto,
)

from .descriptors import ModelProperty
from .fields.field import StrawberryDjangoField
from .fields.field import field as _field
from .fields.types import get_model_field, resolve_model_field_name
from .settings import strawberry_django_settings as django_settings

__all = [
    "StrawberryDjangoType",
    "type",
    "interface",
    "input",
    "partial",
]

_T = TypeVar("_T", bound=type)
_O = TypeVar("_O", bound=Type[WithStrawberryObjectDefinition])
_M = TypeVar("_M", bound=Model)


def _process_type(
    cls: _T,
    model: Type[Model],
    *,
    field_cls: Type[StrawberryDjangoField] = StrawberryDjangoField,
    filters: Optional[type] = None,
    order: Optional[type] = None,
    pagination: bool = False,
    partial: bool = False,
    is_filter: Union[Literal["lookups"], bool] = False,
    only: Optional[TypeOrSequence[str]] = None,
    select_related: Optional[TypeOrSequence[str]] = None,
    prefetch_related: Optional[TypeOrSequence[PrefetchType]] = None,
    annotate: Optional[TypeOrMapping[AnnotateType]] = None,
    disable_optimization: bool = False,
    fields: Optional[Union[List[str], Literal["__all__"]]] = None,
    exclude: Optional[List[str]] = None,
    **kwargs,
) -> _T:
    is_input = kwargs.get("is_input", False)

    if fields == "__all__":
        model_fields = list(model._meta.fields)
    elif isinstance(fields, Collection):
        model_fields = [f for f in model._meta.fields if f.name in fields]
    elif isinstance(exclude, Collection) and len(exclude) > 0:
        model_fields = [f for f in model._meta.fields if f.name not in exclude]
    else:
        model_fields = []

    # If MAP_AUTO_ID_AS_GLOBAL_ID is True, we can no longer set the id
    # from fields or it will override the GlobalID and return the default
    # django id instead in the query-result. This adjustment however still
    # does not fix if the id was set to auto manually on the ModelType.
    if django_settings().get("MAP_AUTO_ID_AS_GLOBAL_ID", False):
        model_fields = [f for f in model_fields if f.name != "id"]

    existing_annotations = get_annotations(cls)
    try:
        cls.__annotations__  # noqa: B018
    except AttributeError:
        # Python 3.8 / 3.9 does not lazily create cls.__annotations__ if it
        #   does not exist, so we create it here.
        # Note that Python 3.10+ will lazily create cls.__annotations__,
        #   so this code could be refactored / removed once versions before
        #   3.10 are not supported.
        cls.__annotations__ = {}

    for f in model_fields:
        if existing_annotations.get(f.name):
            continue
        cls.__annotations__[f.name] = strawberry.auto

    if is_filter:
        cls.__annotations__.update(
            {
                "AND": Optional[Self],  # type:ignore
                "OR": Optional[Self],  # type:ignore
                "NOT": Optional[Self],  # type:ignore
            },
        )

    django_type = StrawberryDjangoDefinition(
        origin=cast(Type[WithStrawberryObjectDefinition], cls),
        model=model,
        field_cls=field_cls,
        is_partial=partial,
        is_input=is_input,
        is_filter=is_filter,
        filters=filters,
        order=order,
        pagination=pagination,
        disable_optimization=disable_optimization,
        store=OptimizerStore.with_hints(
            only=only,
            select_related=select_related,
            prefetch_related=prefetch_related,
            annotate=annotate,
        ),
    )

    auto_fields: set[str] = set()
    for field_name, field_annotation in get_annotations(cls).items():
        annotation = field_annotation.annotation
        if is_private(annotation):
            continue

        if is_auto(annotation):
            auto_fields.add(field_name)

        # FIXME: For input types it is imported to set the default value to UNSET
        # Is there a better way of doing this?
        if is_input:
            # First check if the field is defined in the class. If it is,
            # then we just need to set its default value to UNSET in case
            # it is MISSING
            if field_name in cls.__dict__:
                field = cls.__dict__[field_name]
                if (
                    isinstance(field, dataclasses.Field)
                    and field.default is dataclasses.MISSING
                ):
                    field.default = UNSET
                    if isinstance(field, StrawberryField):
                        field.default_value = UNSET

                continue

            if not hasattr(cls, field_name):
                base_field = getattr(cls, "__dataclass_fields__", {}).get(field_name)
                if base_field is not None and isinstance(base_field, StrawberryField):
                    new_field = copy.copy(base_field)
                    for attr in [
                        "_arguments",
                        "permission_classes",
                        "directives",
                        "extensions",
                    ]:
                        old_attr = getattr(base_field, attr)
                        if old_attr is not None:
                            setattr(new_field, attr, old_attr[:])
                else:
                    new_field = _field(default=UNSET)

                new_field.type_annotation = field_annotation
                new_field.default = UNSET
                if isinstance(base_field, StrawberryField):
                    new_field.default_value = UNSET
                setattr(cls, field_name, new_field)

    # Make sure model is also considered a "virtual subclass" of cls
    if "is_type_of" not in cls.__dict__:
        cls.is_type_of = lambda obj, info: isinstance(obj, (cls, model))  # type: ignore

    # Default querying methods for relay
    if issubclass(cls, relay.Node):
        for attr, func in [
            ("resolve_id", resolve_model_id),
            ("resolve_id_attr", resolve_model_id_attr),
            ("resolve_node", resolve_model_node),
            ("resolve_nodes", resolve_model_nodes),
        ]:
            existing_resolver = getattr(cls, attr, None)
            if (
                existing_resolver is None
                or existing_resolver.__func__ is getattr(relay.Node, attr).__func__
            ):
                setattr(cls, attr, types.MethodType(func, cls))

            # Adjust types that inherit from other types/interfaces that implement Node
            # to make sure they pass themselves as the node type
            meth = getattr(cls, attr)
            if isinstance(meth, types.MethodType) and meth.__self__ is not cls:
                setattr(
                    cls,
                    attr,
                    types.MethodType(cast(classmethod, meth).__func__, cls),
                )

    settings = django_settings()
    if (
        kwargs.get("description", None) is None
        and model.__doc__
        and settings["TYPE_DESCRIPTION_FROM_MODEL_DOCSTRING"]
    ):
        kwargs["description"] = inspect.cleandoc(model.__doc__)

    strawberry.type(cls, **kwargs)

    # update annotations and fields
    type_def = get_object_definition(cls, strict=True)
    description_from_doc = settings["FIELD_DESCRIPTION_FROM_HELP_TEXT"]
    new_fields: List[StrawberryField] = []
    for f in type_def.fields:
        django_name: Optional[str] = (
            getattr(f, "django_name", None) or f.python_name or f.name
        )
        assert django_name is not None

        description: Optional[str] = getattr(f, "description", None)
        type_annotation: Optional[StrawberryAnnotation] = getattr(
            f,
            "type_annotation",
            None,
        )
        # We need to reset the `__eval_cache__` to make sure inherited types
        # will be forced to reevaluate the annotation on strawberry 0.192.2+
        if type_annotation is not None and hasattr(type_annotation, "__eval_cache__"):
            type_annotation.__eval_cache__ = None

        if f.name in auto_fields:
            f_is_auto = True
            # Force the field to be auto again for it to be re-evaluated
            if type_annotation:
                type_annotation.annotation = strawberry.auto
        else:
            f_is_auto = type_annotation is not None and is_auto(
                type_annotation.annotation,
            )

        try:
            model_attr = get_model_field(django_type.model, django_name)
        except FieldDoesNotExist as e:
            model_attr = getattr(django_type.model, django_name, None)
            is_relation = False

            if model_attr is not None and isinstance(model_attr, ModelProperty):
                if type_annotation is None or f_is_auto:
                    type_annotation = StrawberryAnnotation(
                        model_attr.type_annotation,
                        namespace=sys.modules[model_attr.func.__module__].__dict__,
                    )

                if description is None and description_from_doc:
                    description = model_attr.description

                f_is_auto = False
            elif model_attr is not None and isinstance(
                model_attr,
                (property, functools.cached_property),
            ):
                func = (
                    model_attr.fget
                    if isinstance(model_attr, property)
                    else model_attr.func
                )

                if type_annotation is None or f_is_auto:
                    return_type = func.__annotations__.get("return")
                    if return_type is None:
                        raise MissingFieldAnnotationError(
                            django_name,
                            type_def.origin,
                        ) from e

                    type_annotation = StrawberryAnnotation(
                        return_type,
                        namespace=sys.modules[func.__module__].__dict__,
                    )

                if description is None and func.__doc__ and description_from_doc:
                    description = inspect.cleandoc(func.__doc__)

                f_is_auto = False

            if type_annotation is None or f_is_auto:
                raise
        else:
            is_relation = model_attr.is_relation
            django_name = getattr(f, "django_name", None) or resolve_model_field_name(
                model_attr,
                is_input=django_type.is_input,
                is_filter=bool(django_type.is_filter),
            )

            if description is None and description_from_doc:
                try:
                    from django.contrib.contenttypes.fields import (
                        GenericForeignKey,
                        GenericRel,
                    )
                except (ImportError, RuntimeError):  # pragma: no cover
                    GenericForeignKey = None  # noqa: N806
                    GenericRel = None  # noqa: N806

                if (
                    GenericForeignKey is not None
                    and GenericRel is not None
                    and isinstance(model_attr, (GenericRel, GenericForeignKey))
                ):
                    f_description = None
                elif isinstance(model_attr, (ManyToOneRel, ManyToManyRel)):
                    f_description = model_attr.field.help_text
                else:
                    f_description = getattr(model_attr, "help_text", None)

                if f_description:
                    description = str(f_description)

        if isinstance(f, StrawberryDjangoField) and not f.origin_django_type:
            # If the field is a StrawberryDjangoField and it is the first time
            # seeing it, just update its annotations/description/etc
            f.type_annotation = type_annotation
            f.description = description
        elif isinstance(f, StrawberryDjangoField):
            f = copy.copy(f)  # noqa: PLW2901
        elif (
            not isinstance(f, StrawberryDjangoField)
            and getattr(f, "base_resolver", None) is not None
        ):
            # If this is not a StrawberryDjangoField, but has a base_resolver, no need
            # avoid forcing it to be a StrawberryDjangoField
            new_fields.append(f)
            continue
        else:
            f = field_cls(  # noqa: PLW2901
                django_name=django_name,
                description=description,
                type_annotation=type_annotation,
                python_name=f.python_name,
                graphql_name=getattr(f, "graphql_name", None),
                origin=getattr(f, "origin", None),
                is_subscription=getattr(f, "is_subscription", False),
                base_resolver=getattr(f, "base_resolver", None),
                permission_classes=getattr(f, "permission_classes", ()),
                default=getattr(f, "default", dataclasses.MISSING),
                default_factory=getattr(f, "default_factory", dataclasses.MISSING),
                deprecation_reason=getattr(f, "deprecation_reason", None),
                directives=getattr(f, "directives", ()),
                pagination=getattr(f, "pagination", UNSET),
                filters=getattr(f, "filters", UNSET),
                order=getattr(f, "order", UNSET),
                extensions=getattr(f, "extensions", ()),
            )

        f.django_name = django_name
        f.is_relation = is_relation
        f.origin_django_type = django_type

        new_fields.append(f)
        if f.base_resolver and f.python_name:
            setattr(cls, f.python_name, f)

    type_def.fields = new_fields
    cls.__strawberry_django_definition__ = django_type  # type: ignore
    # TODO: remove when deprecating _type_definition
    DeprecatedDescriptor(
        "_django_type is deprecated, use __strawberry_django_definition__ instead",
        cast(
            WithStrawberryDjangoObjectDefinition,
            cls,
        ).__strawberry_django_definition__,
        "_django_type",
    ).inject(cls)

    return cast(_T, cls)


@dataclasses.dataclass
class StrawberryDjangoDefinition(Generic[_O, _M]):
    origin: _O
    model: Type[_M]
    store: OptimizerStore
    is_input: bool = False
    is_partial: bool = False
    is_filter: Union[Literal["lookups"], bool] = False
    filters: Optional[type] = None
    order: Optional[type] = None
    pagination: bool = False
    field_cls: Type[StrawberryDjangoField] = StrawberryDjangoField
    disable_optimization: bool = False


@dataclass_transform(
    order_default=True,
    field_specifiers=(
        StrawberryField,
        _field,
    ),
)
def type(  # noqa: A001
    model: Type[Model],
    *,
    name: Optional[str] = None,
    field_cls: Type[StrawberryDjangoField] = StrawberryDjangoField,
    is_input: bool = False,
    is_interface: bool = False,
    is_filter: Union[Literal["lookups"], bool] = False,
    description: Optional[str] = None,
    directives: Optional[Sequence[object]] = (),
    extend: bool = False,
    filters: Optional[type] = None,
    order: Optional[type] = None,
    pagination: bool = False,
    only: Optional[TypeOrSequence[str]] = None,
    select_related: Optional[TypeOrSequence[str]] = None,
    prefetch_related: Optional[TypeOrSequence[PrefetchType]] = None,
    annotate: Optional[TypeOrMapping[AnnotateType]] = None,
    disable_optimization: bool = False,
    fields: Optional[Union[List[str], Literal["__all__"]]] = None,
    exclude: Optional[List[str]] = None,
) -> Callable[[_T], _T]:
    """Annotates a class as a Django GraphQL type.

    Examples
    --------
        It can be used like this:

        >>> @strawberry_django.type(SomeModel)
        ... class X:
        ...     some_field: strawberry.auto
        ...     otherfield: str = strawberry_django.field()

    """

    def wrapper(cls: _T) -> _T:
        return _process_type(
            cls,
            model,
            name=name,
            field_cls=field_cls,
            is_input=is_input,
            is_filter=is_filter,
            is_interface=is_interface,
            description=description,
            directives=directives,
            extend=extend,
            filters=filters,
            pagination=pagination,
            order=order,
            only=only,
            select_related=select_related,
            prefetch_related=prefetch_related,
            annotate=annotate,
            disable_optimization=disable_optimization,
            fields=fields,
            exclude=exclude,
        )

    return wrapper


@dataclass_transform(
    order_default=True,
    field_specifiers=(
        StrawberryField,
        _field,
    ),
)
def interface(
    model: Type[Model],
    *,
    name: Optional[str] = None,
    field_cls: Type[StrawberryDjangoField] = StrawberryDjangoField,
    description: Optional[str] = None,
    directives: Optional[Sequence[object]] = (),
    disable_optimization: bool = False,
) -> Callable[[_T], _T]:
    """Annotates a class as a Django GraphQL interface.

    Examples
    --------
        It can be used like this:

        >>> @strawberry_django.interface(SomeModel)
        ... class X:
        ...     some_field: strawberry.auto
        ...     otherfield: str = strawberry_django.field()

    """

    def wrapper(cls: _T) -> _T:
        return _process_type(
            cls,
            model,
            name=name,
            field_cls=field_cls,
            is_interface=True,
            description=description,
            directives=directives,
            disable_optimization=disable_optimization,
        )

    return wrapper


@dataclass_transform(
    order_default=True,
    field_specifiers=(
        StrawberryField,
        _field,
    ),
)
def input(  # noqa: A001
    model: Type[Model],
    *,
    name: Optional[str] = None,
    field_cls: Type[StrawberryDjangoField] = StrawberryDjangoField,
    description: Optional[str] = None,
    directives: Optional[Sequence[object]] = (),
    is_filter: Union[Literal["lookups"], bool] = False,
    partial: bool = False,
    fields: Optional[Union[List[str], Literal["__all__"]]] = None,
    exclude: Optional[List[str]] = None,
) -> Callable[[_T], _T]:
    """Annotates a class as a Django GraphQL input.

    Examples
    --------
        It can be used like this:

        >>> @strawberry_django.input(SomeModel)
        ... class X:
        ...     some_field: strawberry.auto
        ...     otherfield: str = strawberry_django.field()

    """

    def wrapper(cls: _T) -> _T:
        return _process_type(
            cls,
            model,
            name=name,
            field_cls=field_cls,
            is_input=True,
            is_filter=is_filter,
            description=description,
            directives=directives,
            partial=partial,
            fields=fields,
            exclude=exclude,
        )

    return wrapper


@dataclass_transform(
    order_default=True,
    field_specifiers=(
        StrawberryField,
        _field,
    ),
)
def partial(
    model: Type[Model],
    *,
    name: Optional[str] = None,
    field_cls: Type[StrawberryDjangoField] = StrawberryDjangoField,
    description: Optional[str] = None,
    directives: Optional[Sequence[object]] = (),
    fields: Optional[Union[List[str], Literal["__all__"]]] = None,
    exclude: Optional[List[str]] = None,
) -> Callable[[_T], _T]:
    """Annotates a class as a Django GraphQL partial.

    Examples
    --------
        It can be used like this:

        >>> @strawberry_django.partial(SomeModel)
        ... class X:
        ...     some_field: strawberry.auto
        ...     otherfield: str = strawberry_django.field()

    """

    def wrapper(cls: _T) -> _T:
        return _process_type(
            cls,
            model,
            name=name,
            field_cls=field_cls,
            is_input=True,
            description=description,
            directives=directives,
            partial=True,
            fields=fields,
            exclude=exclude,
        )

    return wrapper
