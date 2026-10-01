import pytest
import strawberry
from asgiref.sync import sync_to_async
from django.db.models import QuerySet

from strawberry_django.resolvers import django_resolver
from tests.models import Fruit

pytestmark = pytest.mark.asyncio


@pytest.fixture
def query(schema):
    async def query(query):
        return await schema.execute(query)

    return query


@pytest.mark.django_db(transaction=True)
async def test_query(query, user, group, tag):
    result = await query("{ users { id name group { id name tags { id name } } } }")
    assert not result.errors
    assert result.data["users"] == [
        {
            "id": str(user.id),
            "name": "user",
            "group": {
                "id": str(group.id),
                "name": "group",
                "tags": [
                    {
                        "id": str(tag.id),
                        "name": "tag",
                    },
                ],
            },
        },
    ]


@pytest.mark.django_db(transaction=True)
async def test_sync_resolver_returns_fetched_queryset():
    @strawberry.type
    class FruitStats:
        @strawberry.field
        def count(self, root: QuerySet[Fruit]) -> int:
            # Runs on the event loop, so the queryset must already be fetched
            return len(root)

    @strawberry.type
    class Query:
        @strawberry.field(graphql_type=FruitStats)
        @django_resolver
        def fruit_stats(self) -> QuerySet[Fruit]:
            return Fruit.objects.all()

    await sync_to_async(Fruit.objects.bulk_create)([
        Fruit(name="strawberry"),
        Fruit(name="banana"),
    ])

    schema = strawberry.Schema(query=Query)
    result = await schema.execute("{ fruitStats { count } }")

    assert result.errors is None
    assert result.data == {"fruitStats": {"count": 2}}
