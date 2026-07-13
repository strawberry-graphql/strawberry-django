from __future__ import annotations

import asyncio
from typing import Any

import pytest
import strawberry
from django.core.exceptions import (
    ObjectDoesNotExist,
    PermissionDenied,
    ValidationError,
)
from strawberry.extensions.field_extension import FieldExtension

import strawberry_django
from strawberry_django.fields.types import OperationInfo  # noqa: TC001


@strawberry.type
class Query:
    ok: bool = True


@strawberry.type
class Success:
    value: str


@strawberry.input
class InvalidCreateInput:
    value: str

    def __post_init__(self) -> None:
        raise ValidationError({"value": "invalid input"})


OPERATION = """
    mutation {
        create(value: "test") {
            ... on Success {
                value
            }
            ... on OperationInfo {
                messages {
                    kind
                    message
                    field
                    code
                }
            }
        }
    }
"""


@pytest.mark.parametrize(
    ("exception", "expected_message"),
    [
        (
            ValidationError(
                {"snake_case_field": [ValidationError("invalid", code="invalid")]},
            ),
            {
                "kind": "VALIDATION",
                "message": "invalid",
                "field": "snakeCaseField",
                "code": "invalid",
            },
        ),
        (
            PermissionDenied("denied"),
            {
                "kind": "PERMISSION",
                "message": "denied",
                "field": None,
                "code": None,
            },
        ),
        (
            ObjectDoesNotExist("missing"),
            {
                "kind": "ERROR",
                "message": "missing",
                "field": None,
                "code": None,
            },
        ),
    ],
)
def test_django_exception_handler_converts_supported_exceptions(
    exception: Exception,
    expected_message: dict[str, Any],
) -> None:
    @strawberry.type
    class Mutation:
        @strawberry_django.mutation(handle_django_errors=False)
        def create(self, value: str) -> Success | OperationInfo:
            raise exception

    schema = strawberry.Schema(
        query=Query,
        mutation=Mutation,
        exception_handlers=[strawberry_django.DjangoExceptionHandler()],
    )

    result = schema.execute_sync(OPERATION)

    assert result.errors is None
    assert result.data == {"create": {"messages": [expected_message]}}


def test_django_exception_handler_converts_argument_conversion_error() -> None:
    @strawberry.type
    class Mutation:
        @strawberry_django.mutation(handle_django_errors=True)
        def create(self, data: InvalidCreateInput) -> Success:
            return Success(value=data.value)

    schema = strawberry.Schema(
        query=Query,
        mutation=Mutation,
        exception_handlers=[strawberry_django.DjangoExceptionHandler()],
    )

    result = schema.execute_sync(
        """
        mutation {
            create(data: { value: "test" }) {
                ... on Success {
                    value
                }
                ... on OperationInfo {
                    messages {
                        kind
                        message
                        field
                    }
                }
            }
        }
        """,
    )

    assert result.errors is None
    assert result.data == {
        "create": {
            "messages": [
                {
                    "kind": "VALIDATION",
                    "message": "invalid input",
                    "field": "value",
                },
            ],
        },
    }


def test_django_exception_handler_converts_field_extension_error() -> None:
    class FailingExtension(FieldExtension):
        def resolve(self, next_, source, info, **kwargs):
            raise ValidationError("sync extension failed")

    @strawberry.type
    class Mutation:
        @strawberry_django.mutation(
            handle_django_errors=True,
            extensions=[FailingExtension()],
        )
        def create(self, value: str) -> Success:
            return Success(value=value)

    schema = strawberry.Schema(
        query=Query,
        mutation=Mutation,
        exception_handlers=[strawberry_django.DjangoExceptionHandler()],
    )

    result = schema.execute_sync(OPERATION)

    assert result.errors is None
    assert result.data == {
        "create": {
            "messages": [
                {
                    "kind": "VALIDATION",
                    "message": "sync extension failed",
                    "field": None,
                    "code": None,
                },
            ],
        },
    }


@pytest.mark.asyncio
async def test_django_exception_handler_converts_async_field_extension_error() -> None:
    class FailingExtension(FieldExtension):
        async def resolve_async(
            self,
            next_,
            source,
            info,
            **kwargs,
        ):
            raise ValidationError("async extension failed")

    @strawberry.type
    class Mutation:
        @strawberry_django.mutation(
            handle_django_errors=True,
            extensions=[FailingExtension()],
        )
        async def create(self, value: str) -> Success:
            return Success(value=value)

    schema = strawberry.Schema(
        query=Query,
        mutation=Mutation,
        exception_handlers=[strawberry_django.DjangoExceptionHandler()],
    )

    result = await schema.execute(OPERATION)

    assert result.errors is None
    assert result.data == {
        "create": {
            "messages": [
                {
                    "kind": "VALIDATION",
                    "message": "async extension failed",
                    "field": None,
                    "code": None,
                },
            ],
        },
    }


@pytest.mark.asyncio
async def test_django_exception_handler_is_safe_across_concurrent_executions() -> None:
    @strawberry.type
    class Mutation:
        @strawberry_django.mutation(handle_django_errors=False)
        async def create(self, value: int) -> Success | OperationInfo:
            await asyncio.sleep(0)
            raise ValidationError({"value": f"invalid {value}"})

    schema = strawberry.Schema(
        query=Query,
        mutation=Mutation,
        exception_handlers=[strawberry_django.DjangoExceptionHandler()],
    )
    operation = """
        mutation Create($value: Int!) {
            create(value: $value) {
                ... on OperationInfo {
                    messages {
                        message
                    }
                }
            }
        }
    """

    results = await asyncio.gather(
        *(
            schema.execute(operation, variable_values={"value": value})
            for value in range(100)
        ),
    )

    for value, result in enumerate(results):
        assert result.errors is None
        assert result.data == {
            "create": {"messages": [{"message": f"invalid {value}"}]},
        }


def test_django_exception_handler_only_applies_to_operation_info_unions() -> None:
    @strawberry.type
    class Mutation:
        @strawberry.mutation
        def create(self, value: str) -> Success:
            raise ValidationError("invalid")

    schema = strawberry.Schema(
        query=Query,
        mutation=Mutation,
        exception_handlers=[strawberry_django.DjangoExceptionHandler()],
    )

    result = schema.execute_sync(
        'mutation { create(value: "test") { value } }',
    )

    assert result.data is None
    assert result.errors is not None
    assert result.errors[0].message == "invalid"
