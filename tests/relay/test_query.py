import pytest
import strawberry
from strawberry import relay

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.relay import DjangoCursorConnection, DjangoListConnection
from tests import models
from tests.projects.models import Project
from tests.utils import assert_num_queries


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


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("connection_class", "arguments", "page", "num_queries"),
    [
        (DjangoListConnection, "", slice(None), 1),
        (DjangoListConnection, "first: 2", slice(2), 1),
        # `last` without `before` counts the rows first to build the cursor
        (DjangoListConnection, "last: 2", slice(-2, None), 2),
        (DjangoCursorConnection, "", slice(None), 2),
        (DjangoCursorConnection, "first: 2", slice(2), 2),
        (DjangoCursorConnection, "last: 2", slice(-2, None), 2),
    ],
)
def test_connection_total_count_distinct(
    connection_class: type[DjangoListConnection | DjangoCursorConnection],
    arguments: str,
    page: slice,
    num_queries: int,
):
    @strawberry_django.filter_type(models.FruitType, lookups=True)
    class FruitTypeFilter:
        name: strawberry.auto

    @strawberry_django.filter_type(models.Fruit, lookups=True)
    class FruitFilter:
        types: FruitTypeFilter | None
        DISTINCT: bool | None

    @strawberry_django.type(models.Fruit, filters=FruitFilter)
    class FruitType(relay.Node):
        name: strawberry.auto

    @strawberry.type
    class Query:
        fruits: connection_class[FruitType] = strawberry_django.connection()  # type: ignore

    schema = strawberry.Schema(query=Query, extensions=[DjangoOptimizerExtension])

    tropical = models.FruitType.objects.create(name="tropical")
    citrus = models.FruitType.objects.create(name="citrus")
    fruits = [models.Fruit.objects.create(name=f"fruit{i}") for i in range(3)]
    for fruit in fruits:
        # Both types match the filter, so each fruit is joined twice
        fruit.types.add(tropical, citrus)

    query = f"""
      query testConnectionTotalCount {{
        fruits({arguments} filters: {{
          types: {{ name: {{ inList: ["tropical", "citrus"] }} }}
          DISTINCT: true
        }}) {{
          totalCount
          edges {{
            node {{
              name
            }}
          }}
        }}
      }}
    """
    with assert_num_queries(num_queries):
        result = schema.execute_sync(query)

    assert not result.errors
    assert result.data == {
        "fruits": {
            "totalCount": 3,
            "edges": [{"node": {"name": fruit.name}} for fruit in fruits[page]],
        }
    }
