import pytest
import strawberry
from strawberry import relay

import strawberry_django
from tests.projects.models import Project


@pytest.mark.parametrize("type_name", ["ProjectType", "PublicProjectObject"])
@pytest.mark.django_db(transaction=True)
def test_correct_model_returned(type_name: str):
    @strawberry_django.type(Project)
    class ProjectType(relay.Node):
        name: relay.NodeID[str]
        due_date: strawberry.auto

    @strawberry_django.type(Project)
    class PublicProjectObject(relay.Node):
        name: relay.NodeID[str]
        due_date: strawberry.auto

    @strawberry.type
    class Query:
        node: relay.Node = relay.node()

    schema = strawberry.Schema(query=Query, types=[ProjectType, PublicProjectObject])
    Project.objects.create(name="test")

    node_id = relay.to_base64(type_name, "test")
    result = schema.execute_sync(
        """
        query NodeQuery($id: ID!) {
          node(id: $id) {
            __typename
            id
          }
        }
    """,
        {"id": node_id},
    )
    assert result.errors is None
    assert result.data == {"node": {"__typename": type_name, "id": node_id}}
