import strawberry

import strawberry_django

from .. import models, types


def generate_query(query_type):
    schema = strawberry.Schema(query=query_type)

    def query(query):
        return schema.execute_sync(query)

    return query


def test_queryset(users):
    def users_queryset_hook(info, qs):
        return qs.filter(id__lt=3)

    @strawberry.type
    class Query:
        users = strawberry_django.queries.list(
            models.User, types.User, queryset=users_queryset_hook
        )

        @users.queryset
        def users_queryset(info, qs):
            return qs.filter(id__gt=1)

    query = generate_query(Query)

    result = query("{ users { name } }")
    assert not result.errors
    assert result.data["users"] == [
        {"name": "user2"},
    ]
