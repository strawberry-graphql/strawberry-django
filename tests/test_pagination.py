import sys
from typing import cast

import pytest
import strawberry
from strawberry import auto
from strawberry.types import ExecutionResult

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.pagination import (
    OffsetPaginationInput,
    apply,
    apply_window_pagination,
)
from tests import models, utils
from tests.projects.faker import (
    IssueFactory,
    MilestoneFactory,
    ProjectFactory,
    TagFactory,
)


@strawberry_django.type(models.Fruit, pagination=True)
class Fruit:
    id: auto
    name: auto


@strawberry_django.type(models.Fruit, pagination=True)
class BerryFruit:
    name: auto

    @classmethod
    def get_queryset(cls, queryset, info, **kwargs):
        return queryset.filter(name__contains="berry")


@strawberry.type
class Query:
    fruits: list[Fruit] = strawberry_django.field()
    berries: list[BerryFruit] = strawberry_django.field()


@pytest.fixture
def query():
    return utils.generate_query(Query)


def test_pagination(query, fruits):
    result = query("{ fruits(pagination: { offset: 1, limit:1 }) { name } }")
    assert not result.errors
    assert result.data["fruits"] == [
        {"name": "raspberry"},
    ]


def test_pagination_of_filtered_query(query, fruits):
    result = query("{ berries(pagination: { offset: 1, limit:1 }) { name } }")
    assert not result.errors
    assert result.data["berries"] == [
        {"name": "raspberry"},
    ]


@pytest.mark.django_db(transaction=True)
def test_nested_pagination(fruits, gql_client: utils.GraphQLTestClient):
    # Test nested pagination with optimizer enabled
    # Test query color and nested fruits, paginating the nested fruits
    # Enable optimizer
    query = """
      query testNestedPagination {
        projectList {
          milestones(pagination: { limit: 1 }) {
            name
          }
        }
      }
    """
    p = ProjectFactory.create()
    MilestoneFactory.create_batch(2, project=p)

    result = gql_client.query(query)

    assert not result.errors
    assert isinstance(result.data, dict)
    project_list = result.data["projectList"]
    assert isinstance(project_list, list)
    assert len(project_list) == 1
    assert len(project_list[0]["milestones"]) == 1


def test_resolver_pagination(fruits):
    @strawberry.type
    class Query:
        @strawberry.field
        def fruits(self, pagination: OffsetPaginationInput) -> list[Fruit]:
            queryset = models.Fruit.objects.all()
            return cast("list[Fruit]", apply(pagination, queryset))

    query = utils.generate_query(Query)
    result = query("{ fruits(pagination: { limit: 1 }) { id name } }")
    assert isinstance(result, ExecutionResult)
    assert not result.errors
    assert result.data is not None
    assert result.data["fruits"] == [
        {"id": "1", "name": "strawberry"},
    ]


@pytest.mark.django_db(transaction=True)
def test_apply_window_pagination():
    color = models.Color.objects.create(name="Red")

    for i in range(10):
        models.Fruit.objects.create(name=f"fruit{i}", color=color)

    queryset = apply_window_pagination(
        models.Fruit.objects.all(),
        related_field_id="color_id",
        offset=1,
        limit=1,
    )

    assert queryset.count() == 1
    fruit = queryset.get()
    assert fruit.name == "fruit1"
    assert fruit._strawberry_row_number == 2  # type: ignore
    assert fruit._strawberry_total_count == 10  # type: ignore


@pytest.mark.parametrize("limit", [-1, sys.maxsize])
@pytest.mark.django_db(transaction=True)
def test_apply_window_pagination_with_no_limites(limit):
    color = models.Color.objects.create(name="Red")

    for i in range(10):
        models.Fruit.objects.create(name=f"fruit{i}", color=color)

    queryset = apply_window_pagination(
        models.Fruit.objects.all(),
        related_field_id="color_id",
        offset=2,
        limit=limit,
    )

    assert queryset.count() == 8
    first_fruit = queryset.first()
    assert first_fruit is not None
    assert first_fruit.name == "fruit2"
    assert first_fruit._strawberry_row_number == 3  # type: ignore
    assert first_fruit._strawberry_total_count == 10  # type: ignore


@pytest.mark.django_db(transaction=True)
def test_nested_pagination_m2m(gql_client: utils.GraphQLTestClient):
    # Create 2 tags and 3 issues
    tags = [TagFactory(name=f"Tag {i + 1}") for i in range(2)]
    issues = [IssueFactory(name=f"Issue {i + 1}") for i in range(3)]
    # Assign issues 1 and 2 to the 1st tag
    # Assign issues 2 and 3 to the 2nd tag
    # This means that both tags share the 2nd issue
    tags[0].issues.set(issues[:2])
    tags[1].issues.set(issues[1:])
    with utils.assert_num_queries(2 if DjangoOptimizerExtension.enabled.get() else 6):
        result = gql_client.query(
            """
            query {
              tagConn {
                totalCount
                edges {
                  node {
                    name
                    issues {
                      totalCount
                      edges {
                        node {
                          name
                        }
                      }
                    }
                  }
                }
              }
            }
            """
        )
    # Check the results
    assert not result.errors
    assert result.data == {
        "tagConn": {
            "totalCount": 2,
            "edges": [
                {
                    "node": {
                        "name": "Tag 1",
                        "issues": {
                            "totalCount": 2,
                            "edges": [
                                {"node": {"name": "Issue 1"}},
                                {"node": {"name": "Issue 2"}},
                            ],
                        },
                    }
                },
                {
                    "node": {
                        "name": "Tag 2",
                        "issues": {
                            "totalCount": 2,
                            "edges": [
                                {"node": {"name": "Issue 2"}},
                                {"node": {"name": "Issue 3"}},
                            ],
                        },
                    }
                },
            ],
        }
    }
