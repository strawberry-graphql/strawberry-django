import contextlib
import warnings
from typing import TYPE_CHECKING, Any, Optional, cast

from asgiref.sync import sync_to_async
from django.contrib.auth.base_user import AbstractBaseUser
from django.test.client import AsyncClient, Client
from strawberry.test import BaseGraphQLTestClient
from strawberry.test.client import Response
from typing_extensions import override

if TYPE_CHECKING:
    from collections.abc import Awaitable


class TestClient(BaseGraphQLTestClient):
    __test__ = False

    def __init__(self, path: str, client: Optional[Client] = None):
        self.path = path
        super().__init__(client or Client())

    @property
    def client(self) -> Client:
        return self._client

    def request(
        self,
        body: dict[str, object],
        headers: Optional[dict[str, object]] = None,
        files: Optional[dict[str, object]] = None,
    ):
        kwargs: dict[str, object] = {"data": body, "headers": headers}
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
        super().__init__(
            path,
            client or AsyncClient(),  # type: ignore
        )

    @property
    def client(self) -> AsyncClient:  # type: ignore[reportIncompatibleMethodOverride]
        return self._client

    @override
    async def query(
        self,
        query: str,
        variables: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, object]] = None,
        asserts_errors: Optional[bool] = None,
        files: Optional[dict[str, object]] = None,
        assert_no_errors: Optional[bool] = True,
    ) -> Response:
        body = self._build_body(query, variables, files)

        resp = await cast("Awaitable", self.request(body, headers, files))
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

    @contextlib.asynccontextmanager
    async def login(self, user: AbstractBaseUser):  # type: ignore
        await sync_to_async(self.client.force_login)(user)
        yield
        await sync_to_async(self.client.logout)()
