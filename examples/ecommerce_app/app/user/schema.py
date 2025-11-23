from __future__ import annotations

from typing import cast

import strawberry
from app.base.types import Info
from django.contrib import auth
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

import strawberry_django

from .types import UserFilter, UserOrder, UserType


@strawberry.type
class Query:
    """User-related queries."""

    user: UserType = strawberry_django.field()
    users: list[UserType] = strawberry_django.field(
        filters=UserFilter,
        order=UserOrder,
        pagination=True,
    )

    @strawberry_django.field
    async def me(self, info: Info) -> UserType | None:
        """Get the current logged-in user, or null if not authenticated.

        This query demonstrates async resolvers and context usage for
        retrieving the current user from the request.
        """
        return cast("UserType", await info.context.aget_user())


@strawberry.type
class Mutation:
    """User-related mutations for authentication."""

    @strawberry_django.mutation(handle_django_errors=True)
    def login(
        self,
        info: Info,
        username: str,
        password: str,
    ) -> UserType:
        """Authenticate a user and create a session.

        Args:
            username: The user's username
            password: The user's password

        Returns:
            The authenticated user

        Raises:
            ValidationError: If credentials are invalid

        The handle_django_errors=True parameter automatically converts
        Django ValidationErrors into GraphQL errors with proper formatting.

        """
        request = info.context.request

        user = auth.authenticate(request, username=username, password=password)
        if user is None:
            raise ValidationError(_("Wrong credentials provided."))

        auth.login(request, user)
        return cast("UserType", user)

    @strawberry_django.mutation
    def logout(
        self,
        info: Info,
    ) -> bool:
        """Log out the current user and destroy their session.

        Returns:
            True if a user was logged out, False if no user was logged in

        """
        user = info.context.get_user()
        ret = user.is_authenticated if user else False
        auth.logout(info.context.request)
        return ret
