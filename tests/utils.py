import asyncio
import contextlib
import contextvars
import dataclasses
import inspect
from typing import Any, Dict, Optional, Union

import strawberry
from django.db import DEFAULT_DB_ALIAS, connections
from django.test.client import (
    AsyncClient,  # type: ignore
    Client,
)
from django.test.utils import CaptureQueriesContext
from strawberry.test.client import Response
from strawberry.utils.inspect import in_async_context

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


@contextlib.contextmanager
def assert_num_queries(n: int, *, using=DEFAULT_DB_ALIAS):
    with CaptureQueriesContext(connection=connections[DEFAULT_DB_ALIAS]) as ctx:
        yield

    executed = len(ctx)

    # FIXME: Async will not have access to the correct number of queries without
    # execing CaptureQueriesContext.(__enter__|__exit__) wrapped in sync_to_async
    # How can we fix this?
    with contextlib.suppress(LookupError):
        if _client.get().is_async and executed == 0:
            return

    assert (
        executed == n
    ), "{} queries executed, {} expected\nCaptured queries were:\n{}".format(
        executed,
        n,
        "\n".join(
            f"{i}. {q['sql']}" for i, q in enumerate(ctx.captured_queries, start=1)
        ),
    )


class GraphQLTestClient(TestClient):
    def __init__(
        self,
        path: str,
        client: Union[Client, AsyncClient],
    ):
        super().__init__(path, client=client)
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
        body: Dict[str, object],
        headers: Optional[Dict[str, object]] = None,
        files: Optional[Dict[str, object]] = None,
    ):
        kwargs: Dict[str, object] = {"data": body}
        if files:  # pragma:nocover
            kwargs["format"] = "multipart"
        else:
            kwargs["content_type"] = "application/json"

        return self.client.post(
            self.path,
            **kwargs,  # type: ignore
        )

    def query(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, object]] = None,
        asserts_errors: Optional[bool] = True,
        files: Optional[Dict[str, object]] = None,
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
        if asserts_errors:
            assert response.errors is None, response.errors

        return response
