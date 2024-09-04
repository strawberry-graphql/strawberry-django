import pytest
from strawberry.relay import to_base64
from strawberry.relay.types import PREFIX

from strawberry_django.optimizer import DjangoOptimizerExtension
from tests import utils
from tests.projects.faker import IssueFactory, MilestoneFactory


@pytest.mark.django_db(transaction=True)
def test_nested_pagination(gql_client: utils.GraphQLTestClient):
    # Nested pagination with the same arguments for the parent and child connections
    query = """
      query testNestedConnectionPagination($first: Int, $after: String) {
        milestoneConn(first: $first, after: $after) {
          edges {
            node {
              id
              issuesWithFilters(first: $first, after: $after) {
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
    with utils.assert_num_queries(2 if DjangoOptimizerExtension.enabled.get() else 3):
        result = gql_client.query(query, {"first": 2, "after": to_base64(PREFIX, 0)})

    # We expect the 2nd and 3rd milestones each with their 2nd and 3rd issues
    assert not result.errors
    assert result.data == {
        "milestoneConn": {
            "edges": [
                {
                    "node": {
                        "id": to_base64("MilestoneType", milestone.id),
                        "issuesWithFilters": {
                            "edges": [
                                {"node": {"id": to_base64("IssueType", issue.id)}}
                                for issue in issues[1:3]
                            ]
                        },
                    }
                }
                for milestone, issues in list(nested_data.items())[1:3]
            ]
        }
    }
