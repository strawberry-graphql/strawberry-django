from __future__ import annotations

import strawberry
from strawberry import relay

import strawberry_django

from .models import Email, User


@strawberry_django.type(Email, name="Email")
class EmailType(relay.Node):
    """GraphQL type for Email model implementing Relay Node interface."""

    email: strawberry.auto
    is_primary: strawberry.auto


@strawberry_django.filter_type(User, lookups=True)
class UserFilter:
    id: strawberry.auto
    first_name: strawberry.auto
    birth_date: strawberry.auto


@strawberry_django.order_type(User)
class UserOrder:
    id: strawberry.auto
    first_name: strawberry.auto
    birth_date: strawberry.auto


@strawberry_django.type(User, name="User")
class UserType(relay.Node):
    """GraphQL type for User model.
    
    Demonstrates:
    - Relay Node interface implementation
    - Field deprecation (first_name, last_name -> name)
    - Custom field resolvers with optimization hints
    - Computed fields from model properties (age)
    """

    emails: list[EmailType]
    birth_date: strawberry.auto
    age: strawberry.auto
    first_name: str = strawberry_django.field(deprecation_reason="Use `name` instead.")
    last_name: str = strawberry_django.field(deprecation_reason="Use `name` instead.")

    @strawberry_django.field(only=["first_name", "last_name"])
    def name(self, root: User) -> str:
        """Return the user's full name.
        
        The only parameter ensures first_name and last_name are fetched
        when this field is requested, preventing deferred attribute errors.
        """
        return f"{root.first_name} {root.last_name}".strip()

    @strawberry_django.field(only=["avatar"])
    def avatar(self, root: User) -> str | None:
        """Return the user's avatar URL if available."""
        return root.avatar.url if root.avatar else None
