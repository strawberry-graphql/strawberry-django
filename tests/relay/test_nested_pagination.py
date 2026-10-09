import contextlib
import sys

import pytest
from strawberry.relay import to_base64
from strawberry.relay.types import PREFIX

from strawberry_django.optimizer import DjangoOptimizerExtension
from tests import utils
from tests.projects.faker import IssueFactory, MilestoneFactory


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
