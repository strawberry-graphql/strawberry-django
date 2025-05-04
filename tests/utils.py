import asyncio
import contextlib
import contextvars
import dataclasses
import inspect
import threading
import warnings
from contextlib import AbstractContextManager
from typing import Any, Optional, Union, cast, Protocol, ContextManager, TypeVar, Generic

import strawberry
from asgiref.sync import sync_to_async, async_to_sync
from django.db import DEFAULT_DB_ALIAS, connections
from django.test.client import AsyncClient, Client
from django.test.utils import CaptureQueriesContext
from strawberry.test.client import Response
from strawberry.utils.inspect import in_async_context
from typing_extensions import override, ParamSpec

from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.test.client import TestClient

_client: contextvars.ContextVar["GraphQLTestClient"] = contextvars.ContextVar(
    "_client_ctx",
)


def generate_query(query=None, mutation=None, enable_optimizer=False):
    append_mutation = mutation and not query
    if query is None:

        @strawberry.type
        class Query:
            x: int

        query = Query
    extensions = []

    if enable_optimizer:
        extensions = [DjangoOptimizerExtension()]
    schema = strawberry.Schema(query=query, mutation=mutation, extensions=extensions)

    def process_result(result):
        return result

    async def query_async(query, variable_values, context_value):
        result = await schema.execute(
            query,
            variable_values=variable_values,
            context_value=context_value,
        )
        return process_result(result)

    def query_sync(query, variable_values=None, context_value=None):
        if append_mutation and not query.startswith("mutation"):
            query = f"mutation {query}"
        if in_async_context():
            return query_async(
                query,
                variable_values=variable_values,
                context_value=context_value,
            )
        result = schema.execute_sync(
            query,
            variable_values=variable_values,
            context_value=context_value,
        )
        return process_result(result)

    return query_sync


def dataclass(model):
    def wrapper(cls):
        return dataclasses.dataclass(cls)

    return wrapper


def deep_tuple_to_list(data: tuple) -> list:
    return_list = []
    for elem in data:
        if isinstance(elem, tuple):
            return_list.append(deep_tuple_to_list(elem))

        else:
            return_list.append(elem)

    return return_list


class AsyncCaptureQueriesContext(AbstractContextManager[CaptureQueriesContext]):

    wrapped: CaptureQueriesContext

    def __init__(self, using: str):
        self.using = using

    def wrapped_enter(self):
        self.wrapped = CaptureQueriesContext(connection=connections[self.using])
        return self.wrapped.__enter__()

    def __enter__(self):
        return asyncio.run(sync_to_async(self.wrapped_enter)())

    def __exit__(self, exc_type, exc_value, traceback, /):
        return asyncio.run(sync_to_async(self.wrapped.__exit__)(exc_type, exc_value, traceback))


@contextlib.contextmanager
def assert_num_queries(n: int, *, using=DEFAULT_DB_ALIAS):
    is_async = (gql_client := _client.get(None)) is not None and gql_client.is_async

    if is_async:
        ctx_manager = AsyncCaptureQueriesContext(using)
    else:
        ctx_manager = CaptureQueriesContext(connection=connections[using])

    with ctx_manager as ctx:
        yield ctx

    executed = len(ctx)

    assert executed == n, (
        "{} queries executed, {} expected\nCaptured queries were:\n{}".format(
            executed,
            n,
            "\n".join(
                f"{i}. {q['sql']}" for i, q in enumerate(ctx.captured_queries, start=1)
            ),
        )
    )


class GraphQLTestClient(TestClient):
    def __init__(
        self,
        path: str,
        client: Union[Client, AsyncClient],
    ):
        super().__init__(path, client=cast("Client", client))
        self._token: Optional[contextvars.Token] = None
        self.is_async = isinstance(client, AsyncClient)

    def __enter__(self):
        self._token = _client.set(self)
        return self

    def __exit__(self, *args, **kwargs):
        assert self._token
        _client.reset(self._token)

    def request(
        self,
        body: dict[str, object],
        headers: Optional[dict[str, object]] = None,
        files: Optional[dict[str, object]] = None,
    ):
        kwargs: dict[str, object] = {"data": body}
        if files:  # pragma:nocover
            kwargs["format"] = "multipart"
        else:
            kwargs["content_type"] = "application/json"

        return self.client.post(
            self.path,
            **kwargs,  # type: ignore
        )

    @override
    def query(
        self,
        query: str,
        variables: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, object]] = None,
        asserts_errors: Optional[bool] = None,
        files: Optional[dict[str, object]] = None,
        assert_no_errors: Optional[bool] = True,
    ) -> Response:
        body = self._build_body(query, variables, files)

        resp = self.request(body, headers, files)
        if inspect.iscoroutine(resp):
            resp = asyncio.run(resp)

        data = self._decode(resp, type="multipart" if files else "json")

        response = Response(
            errors=data.get("errors"),
            data=data.get("data"),
            extensions=data.get("extensions"),
        )

        if asserts_errors is not None:
            warnings.warn(
                "The `asserts_errors` argument has been renamed to `assert_no_errors`",
                DeprecationWarning,
                stacklevel=2,
            )

        assert_no_errors = (
            assert_no_errors if asserts_errors is None else asserts_errors
        )
        if assert_no_errors:
            assert response.errors is None

        return response
