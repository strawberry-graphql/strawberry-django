from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

import strawberry
from django.core.exceptions import (
    NON_FIELD_ERRORS,
    ObjectDoesNotExist,
    PermissionDenied,
    ValidationError,
)
from strawberry.utils.str_converters import to_camel_case

from strawberry_django.fields.types import OperationInfo, OperationMessage

if TYPE_CHECKING:
    from collections.abc import Iterator

    from strawberry.types import Info
    from strawberry.types.field import StrawberryField

DjangoError: TypeAlias = ValidationError | PermissionDenied | ObjectDoesNotExist


def _get_validation_error_message(error: ValidationError) -> str:
    if not error.message:
        return "Unknown error"

    return error.message % error.params if error.params else error.message


def _get_validation_errors(error: DjangoError) -> Iterator[OperationMessage]:
    if isinstance(error, PermissionDenied):
        kind = OperationMessage.Kind.PERMISSION
    elif isinstance(error, ValidationError):
        kind = OperationMessage.Kind.VALIDATION
    else:
        kind = OperationMessage.Kind.ERROR

    if isinstance(error, ValidationError) and hasattr(error, "error_dict"):
        for field, field_errors in (error.error_dict or {}).items():
            for field_error in field_errors:
                yield OperationMessage(
                    kind=kind,
                    field=(to_camel_case(field) if field != NON_FIELD_ERRORS else None),
                    message=_get_validation_error_message(field_error),
                    code=getattr(field_error, "code", None),
                )
    elif isinstance(error, ValidationError) and hasattr(error, "error_list"):
        for list_error in error.error_list or []:
            yield OperationMessage(
                kind=kind,
                message=_get_validation_error_message(list_error),
                code=getattr(error, "code", None),
            )
    else:
        message = getattr(error, "msg", None)
        if message is None:
            message = str(error)

        yield OperationMessage(
            kind=kind,
            message=message,
            code=getattr(error, "code", None),
        )


def _operation_info_from_exception(error: DjangoError) -> OperationInfo:
    return OperationInfo(messages=list(_get_validation_errors(error)))


class DjangoExceptionHandler(
    strawberry.ExceptionHandler[DjangoError, OperationInfo],
):
    """Convert expected Django exceptions into ``OperationInfo`` results."""

    def handle(
        self,
        exception: DjangoError,
        *,
        field: StrawberryField,
        info: Info,
    ) -> OperationInfo:
        return _operation_info_from_exception(exception)
