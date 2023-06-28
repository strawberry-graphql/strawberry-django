import contextlib
from typing import Any, Awaitable, Dict, Optional, cast

from asgiref.sync import sync_to_async
from django.contrib.auth.base_user import AbstractBaseUser
from django.test.client import AsyncClient, Client  # type: ignore
from strawberry.test import BaseGraphQLTestClient
from strawberry.test.client import Response


class TestClient(BaseGraphQLTestClient):
    def __init__(self, path: str, client: Optional[Client] = None):
        self.path = path
        super().__init__(client or Client())

    @property
    def client(self) -> Client:
        return self._client

    def request(
        self,
        body: Dict[str, object],
        headers: Optional[Dict[str, object]] = None,
        files: Optional[Dict[str, object]] = None,
    ):
        kwargs: Dict[str, object] = {"data": body, "headers": headers}
        if files:
            kwargs["format"] = "multipart"
        else:
            kwargs["content_type"] = "application/json"

        return self.client.post(
            self.path,
            **kwargs,  # type: ignore
        )

    @contextlib.contextmanager
    def login(self, user: AbstractBaseUser):
        self.client.force_login(user)
        yield
        self.client.logout()


class AsyncTestClient(TestClient):
    def __init__(self, path: str, client: Optional[AsyncClient] = None):
        super().__init__(path, client or AsyncClient())

    @property
    def client(self) -> AsyncClient:
        return self._client

    async def query(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, object]] = None,
        asserts_errors: bool = True,
        files: Optional[Dict[str, object]] = None,
    ) -> Response:
        body = self._build_body(query, variables, files)

        resp = await cast(Awaitable, self.request(body, headers, files))
        data = self._decode(resp, type="multipart" if files else "json")

        response = Response(
            errors=data.get("errors"),
            data=data.get("data"),
            extensions=data.get("extensions"),
        )
        if asserts_errors:
            assert response.errors is None, response.errors

        return response

    @contextlib.asynccontextmanager
    async def login(self, user: AbstractBaseUser):
        await sync_to_async(self.client.force_login)(user)
        yield
        await sync_to_async(self.client.logout)()
