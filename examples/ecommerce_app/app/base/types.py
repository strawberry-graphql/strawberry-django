"""Custom GraphQL context and type definitions.

Provides type-safe context access and utilities for resolvers.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Literal, TypeAlias, cast, overload

from asgiref.sync import sync_to_async
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
from strawberry.django.context import StrawberryDjangoContext
from strawberry.types import info

if TYPE_CHECKING:
    from app.user.models import User

    from .dataloaders import DataLoaders


# Type alias for GraphQL info with our custom Context.
# Provides type safety and IDE autocompletion for context access.
Info: TypeAlias = info.Info["Context", None]


@dataclasses.dataclass
class Context(StrawberryDjangoContext):
    """Custom GraphQL context with type-safe user access and dataloaders.

    Extends StrawberryDjangoContext to add:
    - dataloaders: Container for all DataLoader instances
    - get_user(): Type-safe user retrieval with authentication checks
    - aget_user(): Async version of get_user()

    Example usage:
        @strawberry_django.field
        def my_resolver(self, info: Info) -> SomeType:
            user = info.context.get_user(required=True)
            brand = await info.context.dataloaders.brand_loader.load(brand_id)
    """

    dataloaders: DataLoaders

    @overload
    def get_user(self, *, required: Literal[True]) -> User: ...

    @overload
    def get_user(self, *, required: None = ...) -> User | None: ...

    def get_user(self, *, required: Literal[True] | None = None) -> User | None:
        """Get the authenticated user from the request.

        Args:
            required: If True, raises PermissionDenied when user is not authenticated.
                     If None/False, returns None for unauthenticated requests.

        Returns:
            User instance if authenticated, None otherwise (unless required=True)

        Raises:
            PermissionDenied: If required=True and user is not authenticated/active

        The overload signatures ensure type safety:
        - get_user(required=True) -> User (never None)
        - get_user() -> User | None

        """
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
        """Async version of get_user().

        Use this in async resolvers to avoid SynchronousOnlyOperation errors.

        Example:
            @strawberry_django.field
            async def my_async_resolver(self, info: Info) -> UserType:
                user = await info.context.aget_user(required=True)
                return cast("UserType", user)

        """
        # Wrap the sync method properly to handle the overload signature
        if required:
            return await sync_to_async(lambda: self.get_user(required=True))()
        return await sync_to_async(self.get_user)()
