import contextlib
import sys

import pytest
import strawberry
from strawberry.relay import Node, to_base64
from strawberry.relay.types import PREFIX

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.relay import DjangoCursorConnection, DjangoListConnection
from tests import models, utils
from tests.projects.faker import (
    FavoriteFactory,
    IssueFactory,
    MilestoneFactory,
    TagFactory,
    UserFactory,
)
from tests.projects.models import Favorite, Issue, Tag


@pytest.mark.django_db(transaction=True)
def test_nested_pagination_first(gql_client: utils.GraphQLTestClient):
    # Nested pagination with the same arguments for the parent and child connections
    query = """
      query testNestedConnectionPagination($first: Int, $after: String) {
        milestoneConn(first: $first, after: $after) {
          totalCount
          edges {
            node {
              id
              issuesWithFilters(first: $first, after: $after) {
                totalCount
                edges {
                  node {
                    id
                  }
                }
              }
            }
          }
        }
      }
    """

    # Create 4 milestones, each with 4 issues
    nested_data = {
        milestone: IssueFactory.create_batch(4, milestone=milestone)
        for milestone in MilestoneFactory.create_batch(4)
    }

    # Run the nested pagination query
    # We expect only 2 database queries if the optimizer is enabled, otherwise 3 (N+1)
    with utils.assert_num_queries(2 if DjangoOptimizerExtension.enabled.get() else 6):
        result = gql_client.query(query, {"first": 2, "after": to_base64(PREFIX, 0)})

    # We expect the 2nd and 3rd milestones each with their 2nd and 3rd issues
    assert not result.errors
    assert result.data == {
        "milestoneConn": {
            "totalCount": 4,
            "edges": [
                {
                    "node": {
                        "id": to_base64("MilestoneType", milestone.id),
                        "issuesWithFilters": {
                            "totalCount": 4,
                            "edges": [
                                {"node": {"id": to_base64("IssueType", issue.id)}}
                                for issue in issues[1:3]
                            ],
                        },
                    }
                }
                for milestone, issues in list(nested_data.items())[1:3]
            ],
        }
    }


@pytest.mark.django_db(transaction=True)
def test_nested_pagination_last_before(gql_client: utils.GraphQLTestClient):
    query = """
      query testNestedConnectionPagination($last: Int, $before: String) {
        milestoneConn(last: $last, before: $before) {
          totalCount
          edges {
            node {
              id
              issuesWithFilters(last: $last, before: $before) {
                totalCount
                edges {
                  node {
                    id
                  }
                }
              }
            }
          }
        }
      }
    """

    nested_data = {
        milestone: IssueFactory.create_batch(4, milestone=milestone)
        for milestone in MilestoneFactory.create_batch(4)
    }

    with utils.assert_num_queries(2 if DjangoOptimizerExtension.enabled.get() else 6):
        result = gql_client.query(query, {"last": 2, "before": to_base64(PREFIX, 3)})

    assert not result.errors
    assert result.data == {
        "milestoneConn": {
            "totalCount": 4,
            "edges": [
                {
                    "node": {
                        "id": to_base64("MilestoneType", milestone.id),
                        "issuesWithFilters": {
                            "totalCount": 4,
                            "edges": [
                                {"node": {"id": to_base64("IssueType", issue.id)}}
                                for issue in issues[1:3]
                            ],
                        },
                    }
                }
                for milestone, issues in list(nested_data.items())[1:3]
            ],
        }
    }


@pytest.mark.django_db(transaction=True)
def test_nested_pagination_last(gql_client: utils.GraphQLTestClient):
    query = """
      query testNestedConnectionPagination($last: Int) {
        milestoneConn(last: $last) {
          totalCount
          edges {
            node {
              id
              issuesWithFilters(last: $last) {
                totalCount
                edges {
                  node {
                    id
                  }
                }
              }
            }
          }
        }
      }
    """

    nested_data = {
        milestone: IssueFactory.create_batch(4, milestone=milestone)
        for milestone in MilestoneFactory.create_batch(4)
    }
    # Expecting 3 queries when optimized due to initial COUNT query used for `before` creation
    with utils.assert_num_queries(
        3 if DjangoOptimizerExtension.enabled.get() else 6
    ) as q_ctx:
        result = gql_client.query(query, {"last": 2})

    if DjangoOptimizerExtension.enabled.get():
        # Validating that the milestoneConn query is actually LIMIT sys.maxsize - limitless
        queries_using_maxsize = [
            q["sql"]
            for q in q_ctx.captured_queries
            if f"LIMIT {sys.maxsize}" in q["sql"]
        ]
        assert not queries_using_maxsize, (
            f"{len(queries_using_maxsize)} queries executed using sys.maxsize"
            " instead of reversed pagination\nCaptured queries were:\n"
            "{}".format("\n".join(queries_using_maxsize))
        )

    assert not result.errors
    assert result.data == {
        "milestoneConn": {
            "totalCount": 4,
            "edges": [
                {
                    "node": {
                        "id": to_base64("MilestoneType", milestone.id),
                        "issuesWithFilters": {
                            "totalCount": 4,
                            "edges": [
                                {"node": {"id": to_base64("IssueType", issue.id)}}
                                for issue in issues[-2:]
                            ],
                        },
                    }
                }
                for milestone, issues in list(nested_data.items())[-2:]
            ],
        }
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("arguments", ["", "(first: 1)", "(last: 1)"])
def test_nested_total_count_without_edges(
    gql_client: utils.GraphQLTestClient, arguments: str
):
    query = f"""
      query testNestedConnectionTotalCount {{
        milestoneConn {{
          edges {{
            node {{
              id
              issuesWithFilters{arguments} {{
                totalCount
              }}
            }}
          }}
        }}
      }}
    """

    milestones = MilestoneFactory.create_batch(3)
    for milestone, issue_count in zip(milestones, [3, 1, 0], strict=True):
        IssueFactory.create_batch(issue_count, milestone=milestone)

    # Selecting only `totalCount` must not fall back to one COUNT per milestone
    with _assert_num_queries_when_optimized(2):
        result = gql_client.query(query)

    assert not result.errors
    assert result.data == {
        "milestoneConn": {
            "edges": [
                {
                    "node": {
                        "id": to_base64("MilestoneType", milestone.id),
                        "issuesWithFilters": {"totalCount": issue_count},
                    }
                }
                for milestone, issue_count in zip(milestones, [3, 1, 0], strict=True)
            ],
        }
    }


@pytest.mark.django_db(transaction=True)
def test_nested_total_count_without_edges_applies_filters(
    gql_client: utils.GraphQLTestClient,
):
    query = """
      query testNestedConnectionTotalCount {
        milestoneConn {
          edges {
            node {
              id
              issuesWithFilters(filters: { search: "Bug" }) {
                totalCount
              }
            }
          }
        }
      }
    """

    milestones = MilestoneFactory.create_batch(2)
    IssueFactory.create(milestone=milestones[0], name="Bug 1")
    IssueFactory.create(milestone=milestones[0], name="Bug 2")
    IssueFactory.create(milestone=milestones[0], name="Feature")
    IssueFactory.create(milestone=milestones[1], name="Feature")

    with _assert_num_queries_when_optimized(2):
        result = gql_client.query(query)

    assert not result.errors
    assert result.data == {
        "milestoneConn": {
            "edges": [
                {
                    "node": {
                        "id": to_base64("MilestoneType", milestone.id),
                        "issuesWithFilters": {"totalCount": total_count},
                    }
                }
                for milestone, total_count in zip(milestones, [2, 0], strict=True)
            ],
        }
    }


@pytest.mark.django_db(transaction=True)
def test_nested_total_count_merged_with_edges_selection(
    gql_client: utils.GraphQLTestClient,
):
    query = """
      query testNestedConnectionTotalCount {
        milestoneConn {
          edges {
            node {
              id
              issuesWithFilters {
                totalCount
              }
              ... on MilestoneType {
                issuesWithFilters {
                  edges {
                    node {
                      id
                    }
                  }
                }
              }
            }
          }
        }
      }
    """

    milestone = MilestoneFactory.create()
    issues = IssueFactory.create_batch(3, milestone=milestone)

    # The merged selection resolves edges, so the prefetch must not be limited to one row
    with _assert_num_queries_when_optimized(2):
        result = gql_client.query(query)

    assert not result.errors
    assert result.data == {
        "milestoneConn": {
            "edges": [
                {
                    "node": {
                        "id": to_base64("MilestoneType", milestone.id),
                        "issuesWithFilters": {
                            "totalCount": 3,
                            "edges": [
                                {"node": {"id": to_base64("IssueType", issue.id)}}
                                for issue in issues
                            ],
                        },
                    }
                }
            ],
        }
    }


def _assert_num_queries_when_optimized(n: int):
    if DjangoOptimizerExtension.enabled.get():
        return utils.assert_num_queries(n)
    return contextlib.nullcontext()


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "connection_class", [DjangoListConnection, DjangoCursorConnection]
)
@pytest.mark.parametrize("arguments", ["", "first: 1", "last: 1", "first: 0"])
@pytest.mark.parametrize("selection", ["totalCount", "totalCount edges { cursor }"])
def test_nested_total_count_distinct(
    connection_class: type[DjangoListConnection | DjangoCursorConnection],
    arguments: str,
    selection: str,
):
    if (
        connection_class is DjangoListConnection
        and arguments == "first: 0"
        and ("edges" in selection)
    ):
        pytest.skip("An empty page carries no total, so it is counted per parent")

    @strawberry_django.filter_type(models.FruitType, lookups=True)
    class FruitTypeFilter:
        name: strawberry.auto

    @strawberry_django.filter_type(models.Fruit, lookups=True)
    class FruitFilter:
        types: FruitTypeFilter | None
        DISTINCT: bool | None

    @strawberry_django.type(models.Fruit, filters=FruitFilter)
    class FruitType(Node):
        name: strawberry.auto

    @strawberry_django.type(models.Color)
    class ColorType(Node):
        fruits: connection_class[FruitType] = strawberry_django.connection()  # type: ignore

    @strawberry.type
    class Query:
        colors: list[ColorType] = strawberry_django.field()

    schema = strawberry.Schema(query=Query, extensions=[DjangoOptimizerExtension])

    tropical = models.FruitType.objects.create(name="tropical")
    citrus = models.FruitType.objects.create(name="citrus")
    colors = [models.Color.objects.create(name=name) for name in ("a", "b", "c")]
    for color, fruit_count in zip(colors, [3, 1, 0], strict=True):
        for _ in range(fruit_count):
            fruit = models.Fruit.objects.create(color=color)
            # Both types match the filter, so each fruit is joined twice
            fruit.types.add(tropical, citrus)

    query = f"""
      query testNestedConnectionTotalCount {{
        colors {{
          fruits({arguments} filters: {{
            types: {{ name: {{ inList: ["tropical", "citrus"] }} }}
            DISTINCT: true
          }}) {{
            {selection}
          }}
        }}
      }}
    """
    # Duplicated rows must not be counted, nor fall back to one COUNT per color
    with utils.assert_num_queries(2):
        result = schema.execute_sync(query)

    assert not result.errors
    assert result.data is not None
    assert [color["fruits"]["totalCount"] for color in result.data["colors"]] == [
        3,
        1,
        0,
    ]


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "connection_class", [DjangoListConnection, DjangoCursorConnection]
)
def test_nested_many_to_many_total_count_without_edges_distinct(
    connection_class: type[DjangoListConnection | DjangoCursorConnection],
):
    @strawberry_django.filter_type(Favorite, lookups=True)
    class FavoriteFilter:
        name: strawberry.auto

    @strawberry_django.filter_type(Issue, lookups=True)
    class IssueFilter:
        favorite_set: FavoriteFilter | None
        DISTINCT: bool | None

    @strawberry_django.type(Issue, filters=IssueFilter)
    class IssueType(Node):
        name: strawberry.auto

    @strawberry_django.type(Tag)
    class TagType(Node):
        issues: connection_class[IssueType] = strawberry_django.connection()  # type: ignore

    @strawberry.type
    class Query:
        tags: list[TagType] = strawberry_django.field()

    schema = strawberry.Schema(query=Query, extensions=[DjangoOptimizerExtension])

    tags = TagFactory.create_batch(3)
    issues = IssueFactory.create_batch(4)
    issues[0].tags.add(tags[0], tags[1])
    issues[1].tags.add(tags[0], tags[1])
    issues[2].tags.add(tags[0])
    issues[3].tags.add(tags[2])
    users = UserFactory.create_batch(2)
    for issue in issues[:3]:
        # Two matching favorites, so each issue is joined twice
        for user in users:
            FavoriteFactory.create(issue=issue, user=user, name="match")
    FavoriteFactory.create(issue=issues[3], user=users[0], name="other")

    query = """
      query testNestedConnectionTotalCount {
        tags {
          issues(filters: {
            favoriteSet: { name: { exact: "match" } }
            DISTINCT: true
          }) {
            totalCount
          }
        }
      }
    """
    with utils.assert_num_queries(2):
        result = schema.execute_sync(query)

    assert not result.errors
    assert result.data == {
        "tags": [{"issues": {"totalCount": total_count}} for total_count in [3, 2, 0]],
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "connection_class", [DjangoListConnection, DjangoCursorConnection]
)
@pytest.mark.parametrize(
    "arguments",
    ["first: -1", "last: -1", "first: 101", "last: 101", 'after: "invalid"'],
)
def test_nested_total_count_without_edges_validates_pagination(
    connection_class: type[DjangoListConnection | DjangoCursorConnection],
    arguments: str,
):
    @strawberry_django.type(models.Fruit)
    class FruitType(Node):
        name: strawberry.auto

    @strawberry_django.type(models.Color)
    class ColorType(Node):
        fruits: connection_class[FruitType] = strawberry_django.connection()  # type: ignore

    @strawberry.type
    class Query:
        colors: list[ColorType] = strawberry_django.field()

    color = models.Color.objects.create(name="red")
    models.Fruit.objects.create(color=color)

    query = f"""
      query testNestedConnectionTotalCount {{
        colors {{
          fruits({arguments}) {{
            totalCount
          }}
        }}
      }}
    """
    optimized = strawberry.Schema(
        query=Query, extensions=[DjangoOptimizerExtension]
    ).execute_sync(query)
    unoptimized = strawberry.Schema(query=Query).execute_sync(query)

    # The optimizer must reject the same arguments as the unoptimized resolver
    assert unoptimized.errors
    assert optimized.errors
    assert [error.message for error in optimized.errors] == [
        error.message for error in unoptimized.errors
    ]
