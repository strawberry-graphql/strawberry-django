import pytest


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
                    }
                ],
            },
        }
    ]
