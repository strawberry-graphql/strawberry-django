from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Literal, cast, overload

from asgiref.sync import sync_to_async
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
from strawberry.django.context import StrawberryDjangoContext
from strawberry.types import info

if TYPE_CHECKING:
    from app.user.models import User

    from .dataloaders import DataLoaders


Info = info.Info["Context", None]


@dataclasses.dataclass
class Context(StrawberryDjangoContext):
    dataloaders: DataLoaders

    @overload
    def get_user(self, *, required: Literal[True]) -> User: ...

    @overload
    def get_user(self, *, required: None = ...) -> User | None: ...

    def get_user(self, *, required: Literal[True] | None = None) -> User | None:
        user = self.request.user

        if not user or not user.is_authenticated or not user.is_active:
            if required:
                raise PermissionDenied(_("No user logged in"))

            return None

        return cast("User", user)

    @overload
    async def aget_user(self, *, required: Literal[True]) -> User: ...

    @overload
    async def aget_user(self, *, required: None = ...) -> User | None: ...

    async def aget_user(self, *, required: Literal[True] | None = None) -> User | None:
        # Wrap the sync method properly to handle the overload signature
        if required:
            return await sync_to_async(lambda: self.get_user(required=True))()
        return await sync_to_async(self.get_user)()
