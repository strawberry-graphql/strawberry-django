from __future__ import annotations

from typing import cast

import strawberry
from app.base.types import Info

import strawberry_django
from django.contrib import auth
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .types import UserFilter, UserOrder, UserType


@strawberry.type
class Query:
    user: UserType = strawberry_django.field()
    users: list[UserType] = strawberry_django.field(
        filters=UserFilter,
        order=UserOrder,
        pagination=True,
    )

    @strawberry_django.field
    async def me(self, info: Info) -> UserType | None:
        """Get the current logged-in user, or `null` if it is not authenticated."""
        return cast("UserType", await info.context.aget_user())


@strawberry.type
class Mutation:
    @strawberry_django.mutation(handle_django_errors=True)
    def login(
        self,
        info: Info,
        username: str,
        password: str,
    ) -> UserType:
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
        user = info.context.get_user()
        ret = user.is_authenticated if user else False
        auth.logout(info.context.request)
        return ret
