from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Annotated, Any, TypeVar, Union

import strawberry
from django.core.exceptions import (
    NON_FIELD_ERRORS,
    ObjectDoesNotExist,
    PermissionDenied,
    ValidationError,
)
from django.db import models, transaction
from strawberry import UNSET, relay
from strawberry.annotation import StrawberryAnnotation
from strawberry.types.field import UNRESOLVED
from strawberry.utils.str_converters import capitalize_first, to_camel_case

from strawberry_django.arguments import argument
from strawberry_django.fields.field import (
    StrawberryDjangoFieldBase,
    StrawberryDjangoFieldFilters,
)
from strawberry_django.fields.types import OperationInfo, OperationMessage
from strawberry_django.optimizer import DjangoOptimizerExtension, optimize
from strawberry_django.permissions import filter_with_perms, get_with_perms
from strawberry_django.resolvers import django_resolver
from strawberry_django.settings import strawberry_django_settings
from strawberry_django.utils.inspect import get_possible_types

from . import resolvers

if TYPE_CHECKING:
    from collections.abc import Iterable

    from graphql.pyutils import AwaitableOrValue
    from strawberry.types import Info
    from strawberry.types.arguments import StrawberryArgument
    from strawberry.types.base import (
        StrawberryObjectDefinition,
        StrawberryType,
        WithStrawberryObjectDefinition,
    )
    from typing_extensions import Literal, Self

    from .types import FullCleanOptions

_T = TypeVar("_T", bound="models.Model | list[models.Model]")


def _get_validaton_error_message(error: ValidationError):
    if not error.message:
        return "Unknown error"

    return error.message % error.params if error.params else error.message


def _get_validation_errors(error: Exception):
    if isinstance(error, PermissionDenied):
        kind = OperationMessage.Kind.PERMISSION
    elif isinstance(error, ValidationError):
        kind = OperationMessage.Kind.VALIDATION
    elif isinstance(error, ObjectDoesNotExist):
        kind = OperationMessage.Kind.ERROR
    else:
        kind = OperationMessage.Kind.ERROR

    if isinstance(error, ValidationError) and hasattr(error, "error_dict"):
        # convert field errors
        for field, field_errors in (error.error_dict or {}).items():
            for e in field_errors:
                yield OperationMessage(
                    kind=kind,
                    field=to_camel_case(field) if field != NON_FIELD_ERRORS else None,
                    message=_get_validaton_error_message(e),
                    code=getattr(e, "code", None),
                )
    elif isinstance(error, ValidationError) and hasattr(error, "error_list"):
        # convert non-field errors
        for e in error.error_list or []:
            yield OperationMessage(
                kind=kind,
                message=_get_validaton_error_message(e),
                code=getattr(error, "code", None),
            )
    else:
        msg = getattr(error, "msg", None)
        if msg is None:
            msg = str(error)

        yield OperationMessage(
            kind=kind,
            message=msg,
            code=getattr(error, "code", None),
        )


def _handle_exception(error: Exception):
    if isinstance(error, (ValidationError, PermissionDenied, ObjectDoesNotExist)):
        return OperationInfo(
            messages=list(_get_validation_errors(error)),
        )

    raise error


class DjangoMutationBase(StrawberryDjangoFieldBase):
    def __init__(
        self,
        *args,
        handle_django_errors: bool | None = None,
        **kwargs,
    ):
        self._resolved_return_type: bool = False

        if handle_django_errors is None:
            settings = strawberry_django_settings()
            handle_django_errors = settings["MUTATIONS_DEFAULT_HANDLE_ERRORS"]
        self.handle_errors = handle_django_errors

        super().__init__(*args, **kwargs)

    def __copy__(self) -> Self:
        new_field = super().__copy__()
        new_field.handle_errors = self.handle_errors
        return new_field

    def resolve_type(
        self,
        *,
        type_definition: StrawberryObjectDefinition | None = None,
    ) -> (
        StrawberryType | type[WithStrawberryObjectDefinition] | Literal[UNRESOLVED]  # type: ignore
    ):
        resolved = super().resolve_type(type_definition=type_definition)
        if resolved is UNRESOLVED:
            return resolved

        if self.handle_errors and not self._resolved_return_type:
            types_ = tuple(get_possible_types(resolved))
            if OperationInfo not in types_:
                types_ = (*types_, OperationInfo)

                name = capitalize_first(to_camel_case(self.python_name))
                resolved = Annotated[
                    Union[types_],
                    strawberry.union(f"{name}Payload"),
                ]
                self.type_annotation = StrawberryAnnotation(
                    resolved,
                    namespace=getattr(self.type_annotation, "namespace", None),
                )

            self._resolved_return_type = True

        return resolved

    def get_result(
        self,
        source: Any,
        info: Info | None,
        args: list[Any],
        kwargs: dict[str, Any],
    ) -> AwaitableOrValue[Any]:
        if not self.handle_errors:
            return self.resolver(source, info, args, kwargs)

        # TODO: Any other exception types that we should capture here?
        try:
            resolved = self.resolver(source, info, args, kwargs)
        except Exception as e:  # noqa: BLE001
            return _handle_exception(e)

        if inspect.isawaitable(resolved):

            async def async_resolver():
                try:
                    return await resolved
                except Exception as e:  # noqa: BLE001
                    return _handle_exception(e)

            return async_resolver()

        return resolved


class DjangoMutationCUD(DjangoMutationBase):
    def __init__(
        self,
        input_type: type | None = None,
        full_clean: bool | FullCleanOptions = True,
        argument_name: str | None = None,
        key_attr: str | None = None,
        **kwargs,
    ):
        self.full_clean = full_clean
        self.input_type = input_type

        if key_attr is None:
            settings = strawberry_django_settings()
            key_attr = settings["DEFAULT_PK_FIELD_NAME"]

        self.key_attr = key_attr

        if argument_name is None:
            settings = strawberry_django_settings()
            argument_name = settings["MUTATIONS_DEFAULT_ARGUMENT_NAME"]
        self.argument_name = argument_name

        super().__init__(**kwargs)

    def __copy__(self) -> Self:
        new_field = super().__copy__()
        new_field.input_type = self.input_type
        new_field.full_clean = self.full_clean
        return new_field

    @property
    def arguments(self):
        arguments = super().arguments
        if not self.input_type:
            return arguments

        return [
            *arguments,
            argument(
                self.argument_name,
                self.input_type,
            ),
        ]

    @arguments.setter
    def arguments(self, value: list[StrawberryArgument]):
        args_prop = super(DjangoMutationBase, self.__class__).arguments
        return args_prop.fset(self, value)  # type: ignore

    def refetch(self, resolved: _T, *, info: Info | None) -> _T:
        if not DjangoOptimizerExtension.enabled.get() or info is None:
            return resolved

        if isinstance(resolved, list) and resolved:
            model = type(resolved[0])
            if issubclass(model, models.Model):
                original_order = {r.pk: i for i, r in enumerate(resolved)}
                resolved_qs = optimize(
                    model._default_manager.filter(pk__in=[r.pk for r in resolved]),
                    info=info,
                )
                # sort the resolved objects in the order they were given
                resolved = sorted(  # type: ignore
                    resolved_qs,
                    key=lambda r: original_order[r.pk],
                )
        elif isinstance(resolved, models.Model):
            model = type(resolved)
            resolved = optimize(
                model._default_manager.filter(pk=resolved.pk),
                info=info,
            ).get()

        return resolved


class DjangoCreateMutation(DjangoMutationCUD, StrawberryDjangoFieldFilters):
    @django_resolver
    @transaction.atomic
    def resolver(
        self,
        source: Any,
        info: Info | None,
        args: list[Any],
        kwargs: dict[str, Any],
    ) -> Any:
        assert info is not None

        data: list[Any] | Any = kwargs.get(self.argument_name)

        # Do not optimize anything while retrieving the object to create
        with DjangoOptimizerExtension.disabled():
            if self.is_list:
                assert isinstance(data, list)
                resolved = [
                    self.create(
                        resolvers.parse_input(info, vars(d), key_attr=self.key_attr),
                        info=info,
                    )
                    for d in data
                ]
            else:
                assert not isinstance(data, list)
                resolved = self.create(
                    resolvers.parse_input(info, vars(data), key_attr=self.key_attr)
                    if data is not None
                    else {},
                    info=info,
                )

        return self.refetch(resolved, info=info)

    def create(self, data: dict[str, Any], *, info: Info):
        model = self.django_model
        assert model is not None

        return resolvers.create(
            info,
            model,
            data,
            key_attr=self.key_attr,
            full_clean=self.full_clean,
        )


def get_vdata(data: Any) -> dict[str, Any]:
    return vars(data).copy() if data is not None else {}


def get_pk(
    data: dict[str, Any],
    *,
    key_attr: str | None = None,
) -> strawberry.ID | relay.GlobalID | Literal[UNSET] | None:  # type: ignore
    if key_attr is None:
        settings = strawberry_django_settings()
        key_attr = settings["DEFAULT_PK_FIELD_NAME"]

    pk = data.pop(key_attr, UNSET)

    if pk is UNSET:
        pk = data.pop("id", UNSET)
    return pk


class DjangoUpdateMutation(DjangoMutationCUD, StrawberryDjangoFieldFilters):
    @django_resolver
    @transaction.atomic
    def resolver(
        self,
        source: Any,
        info: Info | None,
        args: list[Any],
        kwargs: dict[str, Any],
    ) -> Any:
        assert info is not None

        data: list[Any] | Any = kwargs.get(self.argument_name)

        # Do not optimize anything while retrieving the object to update
        with DjangoOptimizerExtension.disabled():
            if isinstance(data, list):
                resolved = [self.instance_level_update(info, kwargs, d) for d in data]
            else:
                resolved = self.instance_level_update(info, kwargs, data)

        return self.refetch(resolved, info=info)

    def instance_level_update(
        self,
        info: Info,
        kwargs: dict[str, Any],
        data: Any,
    ) -> Any:
        model = self.django_model
        assert model is not None

        vdata = get_vdata(data)
        pk = get_pk(vdata, key_attr=self.key_attr)

        if pk not in (None, UNSET):  # noqa: PLR6201
            instance = get_with_perms(
                pk,
                info,
                required=True,
                model=model,
                key_attr=self.key_attr,
            )
        else:
            instance = filter_with_perms(
                self.get_queryset(
                    queryset=model._default_manager.all(),
                    info=info,
                    **kwargs,
                ),
                info,
            )

        return self.update(
            info, instance, resolvers.parse_input(info, vdata, key_attr=self.key_attr)
        )

    def update(
        self,
        info: Info,
        instance: models.Model | Iterable[models.Model],
        data: dict[str, Any],
    ):
        return resolvers.update(
            info,
            instance,
            data,
            key_attr=self.key_attr,
            full_clean=self.full_clean,
        )


class DjangoDeleteMutation(
    DjangoMutationCUD,
    DjangoMutationBase,
    StrawberryDjangoFieldFilters,
):
    @django_resolver
    @transaction.atomic
    def resolver(
        self,
        source: Any,
        info: Info | None,
        args: list[Any],
        kwargs: dict[str, Any],
    ) -> Any:
        assert info is not None

        model = self.django_model
        assert model is not None

        data: Any = kwargs.get(self.argument_name)
        vdata = get_vdata(data)

        pk = get_pk(vdata, key_attr=self.key_attr)
        if pk not in (None, UNSET):  # noqa: PLR6201
            instance = get_with_perms(
                pk,
                info,
                required=True,
                model=model,
                key_attr=self.key_attr,
            )
        else:
            instance = filter_with_perms(
                self.get_queryset(
                    queryset=model._default_manager.all(),
                    info=info,
                    **kwargs,
                ),
                info,
            )

        return self.delete(
            info,
            instance,
            resolvers.parse_input(info, vdata, key_attr=self.key_attr),
        )

    def delete(
        self,
        info: Info,
        instance: models.Model | Iterable[models.Model],
        data: dict[str, Any] | None = None,
    ):
        return resolvers.delete(
            info,
            instance,
            data=data,
        )
