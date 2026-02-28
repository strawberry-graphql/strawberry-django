import datetime
import operator
from typing import Any, cast

import pytest
import strawberry
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.models import Prefetch
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from graphql import GraphQLResolveInfo
from pytest_mock import MockerFixture
from strawberry.relay import GlobalID, to_base64
from strawberry.types import ExecutionResult, Info, get_object_definition

import strawberry_django
from strawberry_django.optimizer import (
    DjangoOptimizerExtension,
)
from tests.projects.schema import IssueType, MilestoneType, ProjectType, StaffType

from . import utils
from .projects.faker import (
    IssueFactory,
    MilestoneFactory,
    ProjectFactory,
    StaffUserFactory,
    TagFactory,
    UserFactory,
)
from .projects.models import Assignee, Issue, Milestone, Project
from .utils import GraphQLTestClient, assert_num_queries


@pytest.mark.django_db(transaction=True)
def test_user_query(db, gql_client: GraphQLTestClient):
    query = """
      query TestQuery {
        me {
          id
          email
          fullName
        }
      }
    """

    with assert_num_queries(0):
        res = gql_client.query(query)
    assert res.data == {
        "me": None,
    }

    user = UserFactory.create(first_name="John", last_name="Snow")
    with gql_client.login(user):
        with assert_num_queries(2):
            res = gql_client.query(query)
        assert res.data == {
            "me": {
                "id": to_base64("UserType", user.username),
                "email": user.email,
                "fullName": "John Snow",
            },
        }


@pytest.mark.django_db(transaction=True)
def test_staff_query(db, gql_client: GraphQLTestClient, mocker: MockerFixture):
    staff_type_get_queryset = StaffType.get_queryset
    mock_staff_type_get_queryset = mocker.patch(
        "tests.projects.schema.StaffType.get_queryset",
        autospec=True,
        side_effect=staff_type_get_queryset,
    )

    query = """
      query TestQuery {
        staffConn {
          edges {
            node {
              email
            }
          }
        }
      }
    """

    UserFactory.create_batch(5)
    staff1, staff2 = StaffUserFactory.create_batch(2)

    res = gql_client.query(query)
    assert res.data == {
        "staffConn": {
            "edges": [
                {"node": {"email": staff1.email}},
                {"node": {"email": staff2.email}},
            ],
        },
    }
    mock_staff_type_get_queryset.assert_called_once()


@pytest.mark.django_db(transaction=True)
def test_interface_query(db, gql_client: GraphQLTestClient):
    query = """
      query TestQuery ($id: ID!) {
        node (id: $id) {
          __typename
          id
          ... on IssueType {
            name
            milestone {
              id
              name
              project {
                id
                name
              }
            }
            tags {
              id
              name
            }
          }
        }
      }
    """

    issue = IssueFactory.create()
    assert issue.milestone
    tags = TagFactory.create_batch(4)
    issue.tags.set(tags)

    with assert_num_queries(2 if DjangoOptimizerExtension.enabled.get() else 4):
        res = gql_client.query(query, {"id": to_base64("IssueType", issue.pk)})

    assert isinstance(res.data, dict)
    assert isinstance(res.data["node"], dict)
    assert {
        frozenset(d.items()) for d in cast("list", res.data["node"].pop("tags"))
    } == frozenset(
        {
            frozenset(
                {
                    "id": to_base64("TagType", t.pk),
                    "name": t.name,
                }.items(),
            )
            for t in tags
        },
    )
    assert res.data == {
        "node": {
            "__typename": "IssueType",
            "id": to_base64("IssueType", issue.pk),
            "name": issue.name,
            "milestone": {
                "id": to_base64("MilestoneType", issue.milestone.pk),
                "name": issue.milestone.name,
                "project": {
                    "id": to_base64("ProjectType", issue.milestone.project.pk),
                    "name": issue.milestone.project.name,
                },
            },
        },
    }


@pytest.mark.django_db(transaction=True)
def test_query_forward(db, gql_client: GraphQLTestClient):
    query = """
      query TestQuery ($isAsync: Boolean!) {
        issueConn {
          totalCount
          edges {
            node {
              id
              name
              milestone {
                id
                name
                asyncField(value: "foo") @include (if: $isAsync)
                project {
                  id
                  name
                }
              }
            }
          }
        }
      }
    """

    expected = []
    for p in ProjectFactory.create_batch(2):
        for m in MilestoneFactory.create_batch(2, project=p):
            for i in IssueFactory.create_batch(2, milestone=m):
                r: dict[str, Any] = {
                    "id": to_base64("IssueType", i.id),
                    "name": i.name,
                    "milestone": {
                        "id": to_base64("MilestoneType", m.id),
                        "name": m.name,
                        "project": {
                            "id": to_base64("ProjectType", p.id),
                            "name": p.name,
                        },
                    },
                }
                if gql_client.is_async:
                    r["milestone"]["asyncField"] = "value: foo"
                expected.append(r)

    with assert_num_queries(1 if DjangoOptimizerExtension.enabled.get() else 18):
        res = gql_client.query(query, {"isAsync": gql_client.is_async})

    assert res.data == {
        "issueConn": {
            "totalCount": 8,
            "edges": [{"node": r} for r in expected],
        },
    }


@pytest.mark.django_db(transaction=True)
def test_query_forward_with_interfaces(db, gql_client: GraphQLTestClient):
    query = """
      query TestQuery ($isAsync: Boolean!) {
        issueConn {
          totalCount
          edges {
            node {
              id
              ... on Named {
                name
              }
              milestone {
                id
                ... on Named {
                  name
                }
                asyncField(value: "foo") @include (if: $isAsync)
                project {
                  id
                  ... on Named {
                    name
                  }
                }
              }
            }
          }
        }
      }
    """

    expected = []
    for p in ProjectFactory.create_batch(2):
        for m in MilestoneFactory.create_batch(2, project=p):
            for i in IssueFactory.create_batch(2, milestone=m):
                r: dict[str, Any] = {
                    "id": to_base64("IssueType", i.id),
                    "name": i.name,
                    "milestone": {
                        "id": to_base64("MilestoneType", m.id),
                        "name": m.name,
                        "project": {
                            "id": to_base64("ProjectType", p.id),
                            "name": p.name,
                        },
                    },
                }
                if gql_client.is_async:
                    r["milestone"]["asyncField"] = "value: foo"
                expected.append(r)

    with assert_num_queries(1 if DjangoOptimizerExtension.enabled.get() else 18):
        res = gql_client.query(query, {"isAsync": gql_client.is_async})

    assert res.data == {
        "issueConn": {
            "totalCount": 8,
            "edges": [{"node": r} for r in expected],
        },
    }


@pytest.mark.django_db(transaction=True)
def test_query_forward_with_fragments(db, gql_client: GraphQLTestClient):
    query = """
      fragment issueFrag on IssueType {
          nameWithKind
          nameWithPriority
      }

      fragment milestoneFrag on MilestoneType {
        id
        project {
          name
        }
      }

      query TestQuery {
        issueConn {
          totalCount
          edges {
            node {
              id
              name
              ... issueFrag
              milestone {
                name
                project {
                  id
                  name
                }
                ... milestoneFrag
              }
            }
          }
        }
      }
    """

    expected = []
    for p in ProjectFactory.create_batch(3):
        for m in MilestoneFactory.create_batch(3, project=p):
            for i in IssueFactory.create_batch(3, milestone=m):
                m_res = {
                    "id": to_base64("MilestoneType", m.id),
                    "name": m.name,
                    "project": {
                        "id": to_base64("ProjectType", p.id),
                        "name": p.name,
                    },
                }
                expected.append(
                    {
                        "id": to_base64("IssueType", i.id),
                        "name": i.name,
                        "nameWithKind": f"{i.kind}: {i.name}",
                        "nameWithPriority": f"{i.kind}: {i.priority}",
                        "milestone": m_res,
                    },
                )

    with assert_num_queries(1 if DjangoOptimizerExtension.enabled.get() else 56):
        res = gql_client.query(query)

    assert res.data == {
        "issueConn": {
            "totalCount": 27,
            "edges": [{"node": r} for r in expected],
        },
    }


@pytest.mark.django_db(transaction=True)
def test_query_prefetch(db, gql_client: GraphQLTestClient):
    query = """
      query TestQuery ($node_id: ID!) {
        project (id: $node_id) {
          id
          name
          milestones {
            id
            name
            project {
              id
              name
            }
            issues {
              id
              name
              milestone {
                id
                name
              }
            }
          }
        }
      }
    """

    expected = []
    for p in ProjectFactory.create_batch(2):
        p_res: dict[str, Any] = {
            "id": to_base64("ProjectType", p.id),
            "name": p.name,
            "milestones": [],
        }
        expected.append(p_res)
        for m in MilestoneFactory.create_batch(2, project=p):
            m_res: dict[str, Any] = {
                "id": to_base64("MilestoneType", m.id),
                "name": m.name,
                "project": {
                    "id": p_res["id"],
                    "name": p_res["name"],
                },
                "issues": [],
            }
            p_res["milestones"].append(m_res)
            for i in IssueFactory.create_batch(2, milestone=m):
                m_res["issues"].append(
                    {
                        "id": to_base64("IssueType", i.id),
                        "name": i.name,
                        "milestone": {
                            "id": m_res["id"],
                            "name": m_res["name"],
                        },
                    },
                )

    assert len(expected) == 2
    for e in expected:
        with assert_num_queries(3 if DjangoOptimizerExtension.enabled.get() else 4):
            res = gql_client.query(query, {"node_id": e["id"]})

        assert res.data == {"project": e}


@pytest.mark.django_db(transaction=True)
def test_query_prefetch_with_callable(db, gql_client: GraphQLTestClient):
    query = """
      query TestQuery ($node_id: ID!) {
        project (id: $node_id) {
          id
          name
          milestones {
            id
            name
            project {
              id
              name
            }
            myIssues {
              id
              name
              milestone {
                id
                name
              }
            }
          }
        }
      }
    """

    user = UserFactory.create()
    expected = []
    for p in ProjectFactory.create_batch(2):
        p_res: dict[str, Any] = {
            "id": to_base64("ProjectType", p.id),
            "name": p.name,
            "milestones": [],
        }
        expected.append(p_res)
        for m in MilestoneFactory.create_batch(2, project=p):
            m_res: dict[str, Any] = {
                "id": to_base64("MilestoneType", m.id),
                "name": m.name,
                "project": {
                    "id": p_res["id"],
                    "name": p_res["name"],
                },
                "myIssues": [],
            }
            p_res["milestones"].append(m_res)

            # Those issues are not assigned to the user,
            # thus they should not appear in the results
            IssueFactory.create_batch(2, milestone=m)
            for i in IssueFactory.create_batch(2, milestone=m):
                Assignee.objects.create(user=user, issue=i)
                m_res["myIssues"].append(
                    {
                        "id": to_base64("IssueType", i.id),
                        "name": i.name,
                        "milestone": {
                            "id": m_res["id"],
                            "name": m_res["name"],
                        },
                    },
                )

    assert len(expected) == 2
    for e in expected:
        with gql_client.login(user):
            if DjangoOptimizerExtension.enabled.get():
                with assert_num_queries(5):
                    res = gql_client.query(query, {"node_id": e["id"]})
                    assert res.data == {"project": e}
            else:
                # myIssues requires the optimizer to be turned on
                res = gql_client.query(
                    query,
                    {"node_id": e["id"]},
                    assert_no_errors=False,
                )
                assert res.errors


@pytest.mark.django_db(transaction=True)
def test_query_prefetch_with_fragments(db, gql_client: GraphQLTestClient):
    query = """
      fragment issueFrag on IssueType {
          nameWithKind
          nameWithPriority
      }

      fragment milestoneFrag on MilestoneType {
        id
        project {
          id
          name
        }
      }

      query TestQuery ($node_id: ID!) {
        project (id: $node_id) {
          id
          name
          milestones {
            id
            name
            project {
              id
              name
            }
            issues {
              id
              name
              ... issueFrag
              milestone {
                ... milestoneFrag
              }
            }
          }
        }
      }
    """

    expected = []
    for p in ProjectFactory.create_batch(3):
        p_res: dict[str, Any] = {
            "id": to_base64("ProjectType", p.id),
            "name": p.name,
            "milestones": [],
        }
        expected.append(p_res)
        for m in MilestoneFactory.create_batch(3, project=p):
            m_res: dict[str, Any] = {
                "id": to_base64("MilestoneType", m.id),
                "name": m.name,
                "project": {
                    "id": p_res["id"],
                    "name": p_res["name"],
                },
                "issues": [],
            }
            p_res["milestones"].append(m_res)
            for i in IssueFactory.create_batch(3, milestone=m):
                m_res["issues"].append(
                    {
                        "id": to_base64("IssueType", i.id),
                        "name": i.name,
                        "nameWithKind": f"{i.kind}: {i.name}",
                        "nameWithPriority": f"{i.kind}: {i.priority}",
                        "milestone": {
                            "id": m_res["id"],
                            "project": {
                                "id": p_res["id"],
                                "name": p_res["name"],
                            },
                        },
                    },
                )

    assert len(expected) == 3
    for e in expected:
        with assert_num_queries(3 if DjangoOptimizerExtension.enabled.get() else 5):
            res = gql_client.query(query, {"node_id": e["id"]})

        assert res.data == {"project": e}


@pytest.mark.django_db(transaction=True)
def test_query_connection_with_resolver(db, gql_client: GraphQLTestClient):
    query = """
      query TestQuery {
        projectConnWithResolver (name: "Foo") {
          totalCount
          edges {
            node {
              id
              name
              milestones {
                id
              }
            }
          }
        }
      }
    """

    p1 = ProjectFactory.create(name="Foo 1")
    p2 = ProjectFactory.create(name="2 Foo")
    p3 = ProjectFactory.create(name="FooBar")
    for i in range(10):
        ProjectFactory.create(name=f"Project {i}")

    with assert_num_queries(2 if DjangoOptimizerExtension.enabled.get() else 5):
        res = gql_client.query(query)

    assert res.data == {
        "projectConnWithResolver": {
            "totalCount": 3,
            "edges": [
                {
                    "node": {
                        "id": to_base64("ProjectType", p.id),
                        "milestones": [],
                        "name": p.name,
                    },
                }
                for p in [p1, p2, p3]
            ],
        },
    }


@pytest.mark.django_db(transaction=True)
def test_query_connection_nested(db, gql_client: GraphQLTestClient):
    query = """
      query TestQuery {
        tagList {
          id
          name
          issues (first: 2) {
            totalCount
            edges {
              node {
                id
                name
              }
            }
          }
        }
      }
    """

    t1 = TagFactory.create()
    t2 = TagFactory.create()

    t1_issues = IssueFactory.create_batch(10)
    for issue in t1_issues:
        t1.issues.add(issue)
    t2_issues = IssueFactory.create_batch(10)
    for issue in t2_issues:
        t2.issues.add(issue)

    with assert_num_queries(2 if DjangoOptimizerExtension.enabled.get() else 5):
        res = gql_client.query(query)

    assert res.data == {
        "tagList": [
            {
                "id": to_base64("TagType", t1.id),
                "name": t1.name,
                "issues": {
                    "totalCount": 10,
                    "edges": [
                        {"node": {"id": to_base64("IssueType", t.id), "name": t.name}}
                        for t in t1_issues[:2]
                    ],
                },
            },
            {
                "id": to_base64("TagType", t2.id),
                "name": t2.name,
                "issues": {
                    "totalCount": 10,
                    "edges": [
                        {"node": {"id": to_base64("IssueType", t.id), "name": t.name}}
                        for t in t2_issues[:2]
                    ],
                },
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
def test_query_nested_fragments(db, gql_client: GraphQLTestClient):
    query = """
      query TestQuery {
        issueConn {
          ...IssueConnection2
          ...IssueConnection1
        }
      }

      fragment IssueConnection1 on IssueTypeConnection {
        edges {
          node {
            issueAssignees {
              id
            }
          }
        }
      }

      fragment IssueConnection2 on IssueTypeConnection {
        edges {
          node {
            milestone {
              id
              project {
                name
              }
            }
          }
        }
      }
    """

    UserFactory.create()
    expected = {"issueConn": {"edges": []}}
    for i in IssueFactory.create_batch(2):
        assert i.milestone
        assert i.milestone.project

        assignee1 = Assignee.objects.create(user=UserFactory.create(), issue=i)
        assignee2 = Assignee.objects.create(user=UserFactory.create(), issue=i)
        expected["issueConn"]["edges"].append(
            {
                "node": {
                    "issueAssignees": [
                        {"id": to_base64("AssigneeType", assignee1.pk)},
                        {"id": to_base64("AssigneeType", assignee2.pk)},
                    ],
                    "milestone": {
                        "id": to_base64("MilestoneType", i.milestone.pk),
                        "project": {"name": i.milestone.project.name},
                    },
                },
            },
        )

    with assert_num_queries(2 if DjangoOptimizerExtension.enabled.get() else 7):
        res = gql_client.query(query)

    assert res.data == expected


@pytest.mark.django_db(transaction=True)
def test_query_annotate(db, gql_client: GraphQLTestClient):
    query = """
      query TestQuery ($node_id: ID!) {
        project (id: $node_id) {
          id
          name
          isDelayed
          milestonesCount
          isSmall
        }
      }
    """

    expected = []
    today = timezone.now().date()
    for p in ProjectFactory.create_batch(2):
        ms = MilestoneFactory.create_batch(3, project=p)
        assert p.due_date is not None
        p_res: dict[str, Any] = {
            "id": to_base64("ProjectType", p.id),
            "name": p.name,
            "isDelayed": p.due_date < today,
            "milestonesCount": len(ms),
            "isSmall": len(ms) < 3,
        }
        expected.append(p_res)
    for p in ProjectFactory.create_batch(
        2,
        due_date=today - datetime.timedelta(days=1),
    ):
        ms = MilestoneFactory.create_batch(2, project=p)
        assert p.due_date is not None
        p_res: dict[str, Any] = {
            "id": to_base64("ProjectType", p.id),
            "name": p.name,
            "isDelayed": p.due_date < today,
            "milestonesCount": len(ms),
            "isSmall": len(ms) < 3,
        }
        expected.append(p_res)

    assert len(expected) == 4
    for e in expected:
        if DjangoOptimizerExtension.enabled.get():
            with assert_num_queries(1):
                res = gql_client.query(query, {"node_id": e["id"]})
                assert res.data == {"project": e}
        else:
            # isDelayed and milestonesCount requires the optimizer to be turned on
            res = gql_client.query(
                query,
                {"node_id": e["id"]},
                assert_no_errors=False,
            )
            assert res.errors


@pytest.mark.django_db(transaction=True)
def test_query_annotate_with_callable(db, gql_client: GraphQLTestClient):
    query = """
      query TestQuery ($node_id: ID!) {
        project (id: $node_id) {
          id
          name
          milestones {
            id
            name
            myBugsCount
          }
        }
      }
    """

    user = UserFactory.create()
    expected = []
    for p in ProjectFactory.create_batch(2):
        p_res: dict[str, Any] = {
            "id": to_base64("ProjectType", p.id),
            "name": p.name,
            "milestones": [],
        }
        expected.append(p_res)
        for m in MilestoneFactory.create_batch(2, project=p):
            m_res: dict[str, Any] = {
                "id": to_base64("MilestoneType", m.id),
                "name": m.name,
                "myBugsCount": 0,
            }
            p_res["milestones"].append(m_res)

            # Those issues are not assigned to the user,
            # thus they should not be counted
            IssueFactory.create_batch(2, milestone=m, kind=Issue.Kind.BUG)
            # Those issues are not bugs,
            # thus they should not be counted
            IssueFactory.create_batch(3, milestone=m, kind=Issue.Kind.FEATURE)
            # Those issues are bugs assigned to the user,
            # thus they will be counted
            for i in IssueFactory.create_batch(4, milestone=m, kind=Issue.Kind.BUG):
                Assignee.objects.create(user=user, issue=i)
                m_res["myBugsCount"] += 1

    assert len(expected) == 2
    for e in expected:
        with gql_client.login(user):
            if DjangoOptimizerExtension.enabled.get():
                with assert_num_queries(4):
                    res = gql_client.query(query, {"node_id": e["id"]})
                    assert res.data == {"project": e}
            else:
                # myBugsCount requires the optimizer to be turned on
                res = gql_client.query(
                    query,
                    {"node_id": e["id"]},
                    assert_no_errors=False,
                )
                assert res.errors


@pytest.mark.django_db(transaction=True)
def test_user_query_with_prefetch():
    @strawberry_django.type(
        Project,
    )
    class ProjectTypeWithPrefetch:
        @strawberry_django.field(
            prefetch_related=[
                Prefetch(
                    "milestones",
                    queryset=Milestone.objects.all(),
                    to_attr="prefetched_milestones",
                ),
            ],
        )
        def custom_field(self, info: Info) -> str:
            if hasattr(self, "prefetched_milestones"):
                return "prefetched"
            return "not prefetched"

    @strawberry_django.type(
        Milestone,
    )
    class MilestoneTypeWithNestedPrefetch:
        project: ProjectTypeWithPrefetch

    MilestoneFactory.create()

    @strawberry.type
    class Query:
        milestones: list[MilestoneTypeWithNestedPrefetch] = strawberry_django.field()

    query = utils.generate_query(Query, enable_optimizer=True)
    query_str = """
      query TestQuery {
        milestones {
            project {
                customField
            }
        }
      }
    """
    assert DjangoOptimizerExtension.enabled.get()
    result = query(query_str)

    assert isinstance(result, ExecutionResult)
    assert not result.errors
    assert result.data == {
        "milestones": [
            {
                "project": {
                    "customField": "prefetched",
                },
            },
        ],
    }

    result2 = query(query_str)
    assert isinstance(result2, ExecutionResult)
    assert not result2.errors
    assert result2.data == {
        "milestones": [
            {
                "project": {
                    "customField": "prefetched",
                },
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
def test_query_select_related_with_only(db, gql_client: GraphQLTestClient):
    query = """
      query TestQuery ($id: ID!) {
        issue (id: $id) {
          id
          milestoneName
        }
      }
    """

    milestone = MilestoneFactory.create()
    issue = IssueFactory.create(milestone=milestone)

    with assert_num_queries(1 if DjangoOptimizerExtension.enabled.get() else 2):
        res = gql_client.query(query, {"id": to_base64("IssueType", issue.pk)})

    assert res.data == {
        "issue": {
            "id": to_base64("IssueType", issue.id),
            "milestoneName": milestone.name,
        },
    }


@pytest.mark.django_db(transaction=True)
def test_query_select_related_without_only(db, gql_client: GraphQLTestClient):
    query = """
      query TestQuery ($id: ID!) {
        issue (id: $id) {
          id
          milestoneNameWithoutOnlyOptimization
        }
      }
    """

    milestone = MilestoneFactory.create()
    issue = IssueFactory.create(milestone=milestone)

    with assert_num_queries(1 if DjangoOptimizerExtension.enabled.get() else 2):
        res = gql_client.query(query, {"id": to_base64("IssueType", issue.pk)})

    assert res.data == {
        "issue": {
            "id": to_base64("IssueType", issue.id),
            "milestoneNameWithoutOnlyOptimization": milestone.name,
        },
    }


@pytest.mark.django_db(transaction=True)
def test_handles_existing_select_related(db, gql_client: GraphQLTestClient):
    """select_related should not cause errors, even if the field does not get queried."""
    # We're *not* querying the issues' milestones, even though it's
    # prefetched.
    query = """
      query TestQuery {
        tagList {
          issuesWithSelectedRelatedMilestoneAndProject {
            id
            name
          }
        }
      }
    """

    tag = TagFactory.create()

    issues = IssueFactory.create_batch(3)
    for issue in issues:
        tag.issues.add(issue)

    with assert_num_queries(2):
        res = gql_client.query(query)

    assert res.data == {
        "tagList": [
            {
                "issuesWithSelectedRelatedMilestoneAndProject": [
                    {"id": to_base64("IssueType", t.id), "name": t.name}
                    for t in sorted(issues, key=lambda i: i.pk)
                ],
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
def test_query_nested_connection_with_filter(db, gql_client: GraphQLTestClient):
    query = """
      query TestQuery ($id: ID!) {
        milestone(id: $id) {
          id
          issuesWithFilters (filters: {search: "Foo"}) {
            edges {
              node {
                id
              }
            }
          }
        }
      }
    """

    milestone = MilestoneFactory.create()
    issue1 = IssueFactory.create(milestone=milestone, name="Foo")
    issue2 = IssueFactory.create(milestone=milestone, name="Foo Bar")
    issue3 = IssueFactory.create(milestone=milestone, name="Bar Foo")
    IssueFactory.create(milestone=milestone, name="Bar Bin")

    with assert_num_queries(2):
        res = gql_client.query(query, {"id": to_base64("MilestoneType", milestone.pk)})

    assert isinstance(res.data, dict)
    result = res.data["milestone"]
    assert isinstance(result, dict)

    expected = {to_base64("IssueType", i.pk) for i in [issue1, issue2, issue3]}
    assert {
        edge["node"]["id"] for edge in result["issuesWithFilters"]["edges"]
    } == expected


@pytest.mark.django_db(transaction=True)
def test_query_nested_connection_with_filter_and_alias(
    db, gql_client: GraphQLTestClient
):
    query = """
      query TestQuery ($id: ID!) {
        milestone(id: $id) {
          id
          fooIssues: issuesWithFilters (filters: {search: "Foo"}) {
            edges {
              node {
                id
              }
            }
          }
          barIssues: issuesWithFilters (filters: {search: "Bar"}) {
            edges {
              node {
                id
              }
            }
          }
        }
      }
    """

    milestone = MilestoneFactory.create()
    issue1 = IssueFactory.create(milestone=milestone, name="Foo")
    issue2 = IssueFactory.create(milestone=milestone, name="Foo Bar")
    issue3 = IssueFactory.create(milestone=milestone, name="Bar Foo")
    issue4 = IssueFactory.create(milestone=milestone, name="Bar Bin")

    with assert_num_queries(3):
        res = gql_client.query(query, {"id": to_base64("MilestoneType", milestone.pk)})

    assert isinstance(res.data, dict)
    result = res.data["milestone"]
    assert isinstance(result, dict)

    foo_expected = {to_base64("IssueType", i.pk) for i in [issue1, issue2, issue3]}
    assert {edge["node"]["id"] for edge in result["fooIssues"]["edges"]} == foo_expected

    bar_expected = {to_base64("IssueType", i.pk) for i in [issue2, issue3, issue4]}
    assert {edge["node"]["id"] for edge in result["barIssues"]["edges"]} == bar_expected


@pytest.mark.django_db(transaction=True)
def test_query_prefetch_with_aliases_same_field(db, gql_client: GraphQLTestClient):
    query = """
      query TestQuery ($node_id: ID!) {
        project (id: $node_id) {
          id
          a: milestones {
            id
            name
          }
          b: milestones {
            id
            name
          }
        }
      }
    """

    project = ProjectFactory.create()
    milestones = MilestoneFactory.create_batch(3, project=project)

    expected_milestones = [
        {
            "id": to_base64("MilestoneType", m.id),
            "name": m.name,
        }
        for m in milestones
    ]

    node_id = to_base64("ProjectType", project.pk)

    with assert_num_queries(2 if DjangoOptimizerExtension.enabled.get() else 3):
        res = gql_client.query(query, {"node_id": node_id})

    assert res.data == {
        "project": {
            "id": node_id,
            "a": expected_milestones,
            "b": expected_milestones,
        },
    }


@pytest.mark.django_db(transaction=True)
def test_query_prefetch_with_aliases_different_subselections(
    db, gql_client: GraphQLTestClient
):
    query = """
      query TestQuery ($node_id: ID!) {
        project (id: $node_id) {
          id
          a: milestones {
            id
          }
          b: milestones {
            id
            name
          }
        }
      }
    """

    project = ProjectFactory.create()
    milestones = MilestoneFactory.create_batch(3, project=project)
    node_id = to_base64("ProjectType", project.pk)

    with assert_num_queries(2 if DjangoOptimizerExtension.enabled.get() else 3):
        res = gql_client.query(query, {"node_id": node_id})

    assert res.data == {
        "project": {
            "id": node_id,
            "a": [{"id": to_base64("MilestoneType", m.id)} for m in milestones],
            "b": [
                {"id": to_base64("MilestoneType", m.id), "name": m.name}
                for m in milestones
            ],
        },
    }


@pytest.mark.django_db(transaction=True)
def test_query_with_optimizer_paginated_prefetch():
    @strawberry_django.type(Milestone, pagination=True)
    class MilestoneTypeWithNestedPrefetch:
        @strawberry_django.field()
        def name(self, info: Info) -> str:
            return self.name

    @strawberry_django.type(
        Project,
    )
    class ProjectTypeWithPrefetch:
        @strawberry_django.field()
        def name(self, info: Info) -> str:
            return self.name

        milestones: list[MilestoneTypeWithNestedPrefetch]

    milestone1 = MilestoneFactory.create()
    project = milestone1.project
    MilestoneFactory.create(project=project)

    @strawberry.type
    class Query:
        projects: list[ProjectTypeWithPrefetch] = strawberry_django.field()

    query1 = utils.generate_query(Query, enable_optimizer=False)
    query_str = """
      fragment f on ProjectTypeWithPrefetch {
         milestones (pagination: {limit: 1}) {
           name
         }
      }

      query TestQuery {
        projects {
            name
            ...f
        }
      }
    """

    # NOTE: The following assertion doesn't work because the
    # DjangoOptimizerExtension instance is not the one within the
    # generate_query wrapper
    """
    assert DjangoOptimizerExtension.enabled.get()
    """
    result1 = query1(query_str)

    assert isinstance(result1, ExecutionResult)
    assert not result1.errors
    assert result1.data == {
        "projects": [
            {
                "name": project.name,
                "milestones": [
                    {
                        "name": milestone1.name,
                    },
                ],
            },
        ],
    }

    query2 = utils.generate_query(Query, enable_optimizer=True)
    result2 = query2(query_str)

    assert isinstance(result2, ExecutionResult)
    assert result2.data == {
        "projects": [
            {
                "name": project.name,
                "milestones": [
                    {
                        "name": milestone1.name,
                    },
                ],
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
def test_nested_prefetch_with_filter(db, gql_client: GraphQLTestClient):
    query = """
      query TestQuery ($id: ID!) {
        milestone(id: $id) {
          id
          name
          issues (filters: {search: "Foo"}) {
            id
            name
          }
        }
      }
    """

    milestone = MilestoneFactory.create()
    issue1 = IssueFactory.create(milestone=milestone, name="Foo")
    issue2 = IssueFactory.create(milestone=milestone, name="Foo Bar")
    IssueFactory.create(milestone=milestone, name="Bar")
    issue4 = IssueFactory.create(milestone=milestone, name="Bar Foo")
    IssueFactory.create(milestone=milestone, name="Bar Bin")

    with assert_num_queries(2):
        res = gql_client.query(
            query,
            {"id": to_base64("MilestoneType", milestone.pk)},
        )

    assert isinstance(res.data, dict)
    assert res.data == {
        "milestone": {
            "id": to_base64("MilestoneType", milestone.pk),
            "name": milestone.name,
            "issues": [
                {
                    "id": to_base64("IssueType", issue.pk),
                    "name": issue.name,
                }
                for issue in [issue1, issue2, issue4]
            ],
        },
    }


@pytest.mark.django_db(transaction=True)
def test_nested_prefetch_with_filter_and_pagination(db, gql_client: GraphQLTestClient):
    query = """
      query TestQuery ($id: ID!) {
        milestone(id: $id) {
          id
          name
          issues (filters: {search: "Foo"}, pagination: {limit: 2}) {
            id
            name
          }
        }
      }
    """

    milestone = MilestoneFactory.create()
    issue1 = IssueFactory.create(milestone=milestone, name="Foo")
    issue2 = IssueFactory.create(milestone=milestone, name="Foo Bar")
    IssueFactory.create(milestone=milestone, name="Bar")
    IssueFactory.create(milestone=milestone, name="Bar Foo")
    IssueFactory.create(milestone=milestone, name="Bar Bin")

    with assert_num_queries(2):
        res = gql_client.query(
            query,
            {"id": to_base64("MilestoneType", milestone.pk)},
        )

    assert isinstance(res.data, dict)
    assert res.data == {
        "milestone": {
            "id": to_base64("MilestoneType", milestone.pk),
            "name": milestone.name,
            "issues": [
                {
                    "id": to_base64("IssueType", issue.pk),
                    "name": issue.name,
                }
                for issue in [issue1, issue2]
            ],
        },
    }


@pytest.mark.django_db(transaction=True)
def test_nested_prefetch_with_multiple_levels(db, gql_client: GraphQLTestClient):
    query = """
      query TestQuery ($id: ID!) {
        milestone(id: $id) {
          id
          name
          issues (order: { name: ASC }) {
            id
            name
            tags {
              id
              name
            }
          }
        }
      }
    """

    milestone = MilestoneFactory.create()

    issue1 = IssueFactory.create(milestone=milestone, name="2Foo")
    issue2 = IssueFactory.create(milestone=milestone, name="1Foo")
    issue3 = IssueFactory.create(milestone=milestone, name="4Foo")
    issue4 = IssueFactory.create(milestone=milestone, name="3Foo")
    issue5 = IssueFactory.create(milestone=milestone, name="5Foo")

    tag1 = TagFactory.create()
    issue1.tags.add(tag1)
    issue2.tags.add(tag1)
    tag2 = TagFactory.create()
    issue2.tags.add(tag2)
    issue3.tags.add(tag2)

    with assert_num_queries(3 if DjangoOptimizerExtension.enabled.get() else 7):
        res = gql_client.query(
            query,
            {"id": to_base64("MilestoneType", milestone.pk)},
        )

    expected_issues = [
        {
            "id": to_base64("IssueType", issue.pk),
            "name": issue.name,
            "tags": [
                {"id": to_base64("TagType", tag.pk), "name": tag.name} for tag in tags
            ],
        }
        for issue, tags in [
            (issue2, [tag1, tag2]),
            (issue1, [tag1]),
            (issue4, []),
            (issue3, [tag2]),
            (issue5, []),
        ]
    ]

    assert isinstance(res.data, dict)
    assert res.data == {
        "milestone": {
            "id": to_base64("MilestoneType", milestone.pk),
            "name": milestone.name,
            "issues": expected_issues,
        },
    }


@pytest.mark.django_db(transaction=True)
def test_nested_prefetch_with_get_queryset(
    db,
    gql_client: GraphQLTestClient,
    mocker: MockerFixture,
):
    mock_get_queryset = mocker.spy(StaffType, "get_queryset")

    query = """
      query TestQuery ($id: ID!) {
        issue(id: $id) {
          id
          staffAssignees {
            id
          }
        }
      }
    """

    issue = IssueFactory.create()
    user = UserFactory.create()
    staff = StaffUserFactory.create()
    for u in [user, staff]:
        Assignee.objects.create(user=u, issue=issue)

    res = gql_client.query(
        query,
        {"id": to_base64("IssueType", issue.pk)},
    )

    assert isinstance(res.data, dict)
    assert res.data == {
        "issue": {
            "id": to_base64("IssueType", issue.pk),
            "staffAssignees": [{"id": to_base64("StaffType", staff.username)}],
        },
    }
    mock_get_queryset.assert_called_once()


@pytest.mark.django_db(transaction=True)
def test_prefetch_hint_with_same_name_field_no_extra_queries(
    db,
):
    @strawberry_django.type(Issue)
    class IssueType:
        pk: strawberry.ID

    @strawberry_django.type(Milestone)
    class MilestoneType:
        pk: strawberry.ID

        @strawberry_django.field(
            prefetch_related=[
                lambda info: Prefetch(
                    "issues",
                    queryset=Issue.objects.filter(name__startswith="Foo"),
                    to_attr="_my_issues",
                ),
            ],
        )
        def issues(self) -> list[IssueType]:
            return self._my_issues  # type: ignore

    @strawberry.type
    class Query:
        milestone: MilestoneType = strawberry_django.field()

    schema = strawberry.Schema(query=Query, extensions=[DjangoOptimizerExtension])

    milestone1 = MilestoneFactory.create()
    milestone2 = MilestoneFactory.create()

    issue1 = IssueFactory.create(name="Foo", milestone=milestone1)
    IssueFactory.create(name="Bar", milestone=milestone1)
    IssueFactory.create(name="Foo", milestone=milestone2)

    query = """\
      query TestQuery ($pk: ID!) {
        milestone(pk: $pk) {
          pk
          issues {
            pk
          }
        }
      }
    """

    with assert_num_queries(2):
        res = schema.execute_sync(query, {"pk": milestone1.pk})

    assert res.errors is None
    assert res.data == {
        "milestone": {
            "pk": str(milestone1.pk),
            "issues": [{"pk": str(issue1.pk)}],
        },
    }


@pytest.mark.django_db(transaction=True)
def test_query_paginated(db, gql_client: GraphQLTestClient):
    query = """
      query TestQuery ($pagination: OffsetPaginationInput) {
        issuesPaginated (pagination: $pagination) {
          totalCount
          results {
            name
            milestone {
              name
            }
          }
        }
      }
    """

    milestone1 = MilestoneFactory.create()
    milestone2 = MilestoneFactory.create()

    issue1 = IssueFactory.create(milestone=milestone1)
    issue2 = IssueFactory.create(milestone=milestone1)
    issue3 = IssueFactory.create(milestone=milestone1)
    issue4 = IssueFactory.create(milestone=milestone2)
    issue5 = IssueFactory.create(milestone=milestone2)

    with assert_num_queries(2 if DjangoOptimizerExtension.enabled.get() else 7):
        res = gql_client.query(query)

    assert res.data == {
        "issuesPaginated": {
            "totalCount": 5,
            "results": [
                {"name": issue1.name, "milestone": {"name": milestone1.name}},
                {"name": issue2.name, "milestone": {"name": milestone1.name}},
                {"name": issue3.name, "milestone": {"name": milestone1.name}},
                {"name": issue4.name, "milestone": {"name": milestone2.name}},
                {"name": issue5.name, "milestone": {"name": milestone2.name}},
            ],
        }
    }

    with assert_num_queries(2 if DjangoOptimizerExtension.enabled.get() else 4):
        res = gql_client.query(query, variables={"pagination": {"limit": 2}})

    assert res.data == {
        "issuesPaginated": {
            "totalCount": 5,
            "results": [
                {"name": issue1.name, "milestone": {"name": milestone1.name}},
                {"name": issue2.name, "milestone": {"name": milestone1.name}},
            ],
        }
    }

    with assert_num_queries(2 if DjangoOptimizerExtension.enabled.get() else 4):
        res = gql_client.query(
            query, variables={"pagination": {"limit": 2, "offset": 2}}
        )

    assert res.data == {
        "issuesPaginated": {
            "totalCount": 5,
            "results": [
                {"name": issue3.name, "milestone": {"name": milestone1.name}},
                {"name": issue4.name, "milestone": {"name": milestone2.name}},
            ],
        }
    }


@pytest.mark.django_db(transaction=True)
def test_query_paginated_nested(db, gql_client: GraphQLTestClient):
    query = """
      query TestQuery ($pagination: OffsetPaginationInput) {
        milestoneList {
          name
          issuesPaginated  (pagination: $pagination) {
            totalCount
            results {
              name
              milestone {
                name
              }
            }
          }
        }
      }
    """

    milestone1 = MilestoneFactory.create()
    milestone2 = MilestoneFactory.create()

    issue1 = IssueFactory.create(milestone=milestone1)
    issue2 = IssueFactory.create(milestone=milestone1)
    issue3 = IssueFactory.create(milestone=milestone1)
    issue4 = IssueFactory.create(milestone=milestone2)
    issue5 = IssueFactory.create(milestone=milestone2)

    with assert_num_queries(2 if DjangoOptimizerExtension.enabled.get() else 5):
        res = gql_client.query(query)

    assert res.data == {
        "milestoneList": [
            {
                "name": milestone1.name,
                "issuesPaginated": {
                    "totalCount": 3,
                    "results": [
                        {"name": issue1.name, "milestone": {"name": milestone1.name}},
                        {"name": issue2.name, "milestone": {"name": milestone1.name}},
                        {"name": issue3.name, "milestone": {"name": milestone1.name}},
                    ],
                },
            },
            {
                "name": milestone2.name,
                "issuesPaginated": {
                    "totalCount": 2,
                    "results": [
                        {"name": issue4.name, "milestone": {"name": milestone2.name}},
                        {"name": issue5.name, "milestone": {"name": milestone2.name}},
                    ],
                },
            },
        ]
    }

    with assert_num_queries(2 if DjangoOptimizerExtension.enabled.get() else 5):
        res = gql_client.query(query, variables={"pagination": {"limit": 1}})

    assert res.data == {
        "milestoneList": [
            {
                "name": milestone1.name,
                "issuesPaginated": {
                    "totalCount": 3,
                    "results": [
                        {"name": issue1.name, "milestone": {"name": milestone1.name}},
                    ],
                },
            },
            {
                "name": milestone2.name,
                "issuesPaginated": {
                    "totalCount": 2,
                    "results": [
                        {"name": issue4.name, "milestone": {"name": milestone2.name}},
                    ],
                },
            },
        ]
    }

    with assert_num_queries(3 if DjangoOptimizerExtension.enabled.get() else 5):
        res = gql_client.query(
            query, variables={"pagination": {"limit": 1, "offset": 2}}
        )

    assert res.data == {
        "milestoneList": [
            {
                "name": milestone1.name,
                "issuesPaginated": {
                    "totalCount": 3,
                    "results": [
                        {"name": issue3.name, "milestone": {"name": milestone1.name}},
                    ],
                },
            },
            {
                "name": milestone2.name,
                "issuesPaginated": {
                    "totalCount": 2,
                    "results": [],
                },
            },
        ]
    }


@pytest.mark.django_db(transaction=True)
def test_prefetch_multi_field_single_optional(db, gql_client: GraphQLTestClient):
    milestone1 = MilestoneFactory.create()
    milestone2 = MilestoneFactory.create()

    issue = IssueFactory.create(name="Foo", milestone=milestone1)
    issue_id = str(
        GlobalID(get_object_definition(IssueType, strict=True).name, str(issue.id))
    )

    milestone_id_1 = str(
        GlobalID(
            get_object_definition(MilestoneType, strict=True).name, str(milestone1.id)
        )
    )
    milestone_id_2 = str(
        GlobalID(
            get_object_definition(MilestoneType, strict=True).name, str(milestone2.id)
        )
    )

    query = """\
      query TestQuery($id1: ID!, $id2: ID!) {
        a: milestone(id: $id1) {
          firstIssue {
            id
          }
        }
        b: milestone(id: $id2) {
          firstIssue {
            id
          }
        }
      }
    """

    with assert_num_queries(4):
        res = gql_client.query(
            query, variables={"id1": milestone_id_1, "id2": milestone_id_2}
        )

    assert res.errors is None
    assert res.data == {
        "a": {
            "firstIssue": {
                "id": issue_id,
            },
        },
        "b": {
            "firstIssue": None,
        },
    }


@pytest.mark.django_db(transaction=True)
def test_prefetch_multi_field_single_required(db, gql_client: GraphQLTestClient):
    milestone = MilestoneFactory.create()

    issue = IssueFactory.create(name="Foo", milestone=milestone)
    issue_id = str(
        GlobalID(get_object_definition(IssueType, strict=True).name, str(issue.id))
    )

    milestone_id = str(
        GlobalID(
            get_object_definition(MilestoneType, strict=True).name, str(milestone.id)
        )
    )

    query = """\
      query TestQuery($id: ID!) {
        milestone(id: $id) {
          firstIssueRequired {
            id
          }
        }
      }
    """

    with assert_num_queries(2):
        res = gql_client.query(query, variables={"id": milestone_id})

    assert res.errors is None
    assert res.data == {
        "milestone": {
            "firstIssueRequired": {
                "id": issue_id,
            },
        },
    }


@pytest.mark.django_db(transaction=True)
def test_prefetch_multi_field_single_required_missing(
    db, gql_client: GraphQLTestClient
):
    milestone1 = MilestoneFactory.create()

    milestone_id = str(
        GlobalID(
            get_object_definition(MilestoneType, strict=True).name, str(milestone1.id)
        )
    )

    query = """\
      query TestQuery($id: ID!) {
        milestone(id: $id) {
          firstIssueRequired {
            id
          }
        }
      }
    """

    with assert_num_queries(2):
        res = gql_client.query(
            query, variables={"id": milestone_id}, assert_no_errors=False
        )

    assert res.errors is not None
    assert res.errors == [
        {
            "locations": [{"column": 11, "line": 3}],
            "message": "Issue matching query does not exist.",
            "path": ["milestone", "firstIssueRequired"],
        }
    ]


@pytest.mark.django_db(transaction=True)
def test_prefetch_multi_field_single_required_multiple_returned(
    db, gql_client: GraphQLTestClient
):
    milestone = MilestoneFactory.create()

    milestone_id = str(
        GlobalID(
            get_object_definition(MilestoneType, strict=True).name, str(milestone.id)
        )
    )
    IssueFactory.create(name="Foo", milestone=milestone)
    IssueFactory.create(name="Bar", milestone=milestone)

    query = """\
      query TestQuery($id: ID!) {
        milestone(id: $id) {
          firstIssueRequired {
            id
          }
        }
      }
    """

    with assert_num_queries(2):
        res = gql_client.query(
            query, variables={"id": milestone_id}, assert_no_errors=False
        )

    assert res.errors is not None
    assert res.errors == [
        {
            "locations": [{"column": 11, "line": 3}],
            "message": "get() returned more than one Issue -- it returned 2!",
            "path": ["milestone", "firstIssueRequired"],
        }
    ]


@pytest.mark.django_db(transaction=True)
def test_no_window_function_for_normal_prefetch(
    db,
):
    @strawberry_django.type(Project)
    class ProjectType:
        pk: strawberry.ID
        name: str

        @staticmethod
        def get_queryset(qs, info):
            # get_queryset exists to force the optimizer to use prefetch instead of select_related
            return qs

    @strawberry_django.type(Milestone)
    class MilestoneType:
        pk: strawberry.ID
        project: ProjectType

    @strawberry.type
    class Query:
        milestones: list[MilestoneType] = strawberry_django.field()

    schema = strawberry.Schema(query=Query, extensions=[DjangoOptimizerExtension])

    milestone1 = MilestoneFactory.create()
    milestone2 = MilestoneFactory.create()

    query = """\
      query TestQuery {
        milestones {
          pk
          project { pk name }
        }
      }
    """

    with CaptureQueriesContext(connection=connections[DEFAULT_DB_ALIAS]) as ctx:
        res = schema.execute_sync(query)
        assert len(ctx.captured_queries) == 2
        # Test that the Prefetch does not use Window pagination unnecessarily
        assert not any(
            '"_strawberry_row_number"' in q["sql"] for q in ctx.captured_queries
        )

    assert res.errors is None
    assert res.data == {
        "milestones": [
            {
                "pk": str(milestone1.pk),
                "project": {
                    "pk": str(milestone1.project.pk),
                    "name": milestone1.project.name,
                },
            },
            {
                "pk": str(milestone2.pk),
                "project": {
                    "pk": str(milestone2.project.pk),
                    "name": milestone2.project.name,
                },
            },
        ]
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("gql_client", ["async", "sync"], indirect=True)
def test_custom_prefetch_optimization(gql_client):
    project = ProjectFactory.create()
    milestone = MilestoneFactory.create(project=project, name="Hello")

    project_id = str(
        GlobalID(get_object_definition(ProjectType, strict=True).name, str(project.id))
    )
    milestone_id = str(
        GlobalID(
            get_object_definition(MilestoneType, strict=True).name, str(milestone.id)
        )
    )
    query = """\
      query TestQuery($id: ID!) {
        project(id: $id) {
          id
          customMilestones {
            id
            name
          }
        }
      }
    """

    with assert_num_queries(2) as ctx:
        res = gql_client.query(
            query, variables={"id": project_id}, assert_no_errors=False
        )
    assert Milestone._meta.db_table in ctx.captured_queries[1]["sql"]
    assert (
        Milestone._meta.get_field("due_date").name not in ctx.captured_queries[1]["sql"]
    )

    assert res.errors is None
    assert res.data == {
        "project": {
            "id": project_id,
            "customMilestones": [{"id": milestone_id, "name": milestone.name}],
        }
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("gql_client", ["async", "sync"], indirect=True)
def test_custom_prefetch_optimization_nested(gql_client):
    project = ProjectFactory.create()
    milestone1 = MilestoneFactory.create(project=project, name="Hello1")
    milestone2 = MilestoneFactory.create(project=project, name="Hello2")

    project_id = str(
        GlobalID(get_object_definition(ProjectType, strict=True).name, str(project.id))
    )
    milestone1_id = str(
        GlobalID(
            get_object_definition(MilestoneType, strict=True).name, str(milestone1.id)
        )
    )
    milestone2_id = str(
        GlobalID(
            get_object_definition(MilestoneType, strict=True).name, str(milestone2.id)
        )
    )
    query = """\
      query TestQuery($id: ID!) {
        milestone(id: $id) {
          id
          project {
            id
            customMilestones {
                id name
              }
          }
        }
      }
    """

    with assert_num_queries(2) as ctx:
        res = gql_client.query(
            query, variables={"id": milestone1_id}, assert_no_errors=False
        )
    assert Milestone._meta.db_table in ctx.captured_queries[1]["sql"]
    assert (
        Milestone._meta.get_field("due_date").name not in ctx.captured_queries[1]["sql"]
    )

    assert res.errors is None
    assert res.data == {
        "milestone": {
            "id": milestone1_id,
            "project": {
                "id": project_id,
                "customMilestones": [
                    {"id": milestone1_id, "name": milestone1.name},
                    {"id": milestone2_id, "name": milestone2.name},
                ],
            },
        }
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("gql_client", ["async", "sync"], indirect=True)
def test_custom_prefetch_model_property_optimization(gql_client):
    project = ProjectFactory.create()
    milestone = MilestoneFactory.create(project=project, name="Hello")

    project_id = str(
        GlobalID(get_object_definition(ProjectType, strict=True).name, str(project.id))
    )
    milestone_id = str(
        GlobalID(
            get_object_definition(MilestoneType, strict=True).name, str(milestone.id)
        )
    )
    query = """\
      query TestQuery($id: ID!) {
        project(id: $id) {
          id
          customMilestonesModelProperty {
            id
            name
          }
        }
      }
    """

    with assert_num_queries(2) as ctx:
        res = gql_client.query(
            query, variables={"id": project_id}, assert_no_errors=False
        )
    assert Milestone._meta.db_table in ctx.captured_queries[1]["sql"]
    assert (
        Milestone._meta.get_field("due_date").name not in ctx.captured_queries[1]["sql"]
    )

    assert res.errors is None
    assert res.data == {
        "project": {
            "id": project_id,
            "customMilestonesModelProperty": [
                {"id": milestone_id, "name": milestone.name}
            ],
        }
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("gql_client", ["async", "sync"], indirect=True)
def test_custom_prefetch_optimization_model_property_nested(gql_client):
    project = ProjectFactory.create()
    milestone1 = MilestoneFactory.create(project=project, name="Hello1")
    milestone2 = MilestoneFactory.create(project=project, name="Hello2")

    project_id = str(
        GlobalID(get_object_definition(ProjectType, strict=True).name, str(project.id))
    )
    milestone1_id = str(
        GlobalID(
            get_object_definition(MilestoneType, strict=True).name, str(milestone1.id)
        )
    )
    milestone2_id = str(
        GlobalID(
            get_object_definition(MilestoneType, strict=True).name, str(milestone2.id)
        )
    )
    query = """\
      query TestQuery($id: ID!) {
        milestone(id: $id) {
          id
          project {
            id
            customMilestonesModelProperty {
                id name
              }
          }
        }
      }
    """

    with assert_num_queries(2) as ctx:
        res = gql_client.query(
            query, variables={"id": milestone1_id}, assert_no_errors=False
        )
    assert Milestone._meta.db_table in ctx.captured_queries[1]["sql"]
    assert (
        Milestone._meta.get_field("due_date").name not in ctx.captured_queries[1]["sql"]
    )

    assert res.errors is None
    assert res.data == {
        "milestone": {
            "id": milestone1_id,
            "project": {
                "id": project_id,
                "customMilestonesModelProperty": [
                    {"id": milestone1_id, "name": milestone1.name},
                    {"id": milestone2_id, "name": milestone2.name},
                ],
            },
        }
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("gql_client", ["async", "sync"], indirect=True)
def test_custom_prefetch_optimize_auto_selects_fk(gql_client):
    """Regression test for #862: optimize() inside Prefetch auto-adds FK field to .only()."""
    project = ProjectFactory.create()
    milestone = MilestoneFactory.create(project=project, name="Hello")

    query = """\
      query TestQuery {
        projectList {
          customMilestones {
            id
            name
          }
        }
      }
    """

    with assert_num_queries(2) as ctx:
        res = gql_client.query(query, assert_no_errors=False)
    assert res.errors is None

    milestone_id = str(
        GlobalID(
            get_object_definition(MilestoneType, strict=True).name, str(milestone.id)
        )
    )
    assert res.data == {
        "projectList": [
            {"customMilestones": [{"id": milestone_id, "name": milestone.name}]}
        ]
    }

    prefetch_sql = next(
        q["sql"] for q in ctx.captured_queries if Milestone._meta.db_table in q["sql"]
    )
    assert "project_id" in prefetch_sql
    assert Milestone._meta.get_field("due_date").name not in prefetch_sql


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("gql_client", ["async", "sync"], indirect=True)
def test_correct_annotation_info(gql_client):
    project = ProjectFactory.create()
    milestone = MilestoneFactory.create(project=project, name="Hello")

    project_id = str(
        GlobalID(get_object_definition(ProjectType, strict=True).name, str(project.id))
    )
    milestone_id = str(
        GlobalID(
            get_object_definition(MilestoneType, strict=True).name, str(milestone.id)
        )
    )
    query = """\
      query TestQuery($id: ID!) {
        project(id: $id) {
          id
          milestones {
            id
            graphqlPath
          }
        }
      }
    """

    res = gql_client.query(query, variables={"id": project_id}, assert_no_errors=False)
    assert res.errors is None
    assert res.data == {
        "project": {
            "id": project_id,
            "milestones": [
                {
                    "id": milestone_id,
                    "graphqlPath": "project,0,milestones,0,graphqlPath",
                }
            ],
        }
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("gql_client", ["async", "sync"], indirect=True)
def test_correct_annotation_info_nested(gql_client):
    project = ProjectFactory.create()
    milestone1 = MilestoneFactory.create(project=project, name="Hello1")
    milestone2 = MilestoneFactory.create(project=project, name="Hello2")

    project_id = str(
        GlobalID(get_object_definition(ProjectType, strict=True).name, str(project.id))
    )
    milestone1_id = str(
        GlobalID(
            get_object_definition(MilestoneType, strict=True).name, str(milestone1.id)
        )
    )
    milestone2_id = str(
        GlobalID(
            get_object_definition(MilestoneType, strict=True).name, str(milestone2.id)
        )
    )
    query = """\
      query TestQuery($id: ID!) {
        milestone(id: $id) {
          id
          graphqlPath
          project {
            id
            milestones {
                id
                graphqlPath
            }
          }
        }
      }
    """

    res = gql_client.query(
        query, variables={"id": milestone1_id}, assert_no_errors=False
    )
    assert res.errors is None
    assert res.data == {
        "milestone": {
            "id": milestone1_id,
            "graphqlPath": "milestone,0,graphqlPath",
            "project": {
                "id": project_id,
                "milestones": [
                    {
                        "id": milestone1_id,
                        "graphqlPath": "milestone,0,project,0,milestones,0,graphqlPath",
                    },
                    {
                        "id": milestone2_id,
                        "graphqlPath": "milestone,0,project,0,milestones,0,graphqlPath",
                    },
                ],
            },
        }
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("gql_client", ["async", "sync"], indirect=True)
def test_mixed_annotation_prefetch(gql_client):
    project = ProjectFactory.create()
    MilestoneFactory.create(project=project, name="Hello")

    project_id = str(
        GlobalID(get_object_definition(ProjectType, strict=True).name, str(project.id))
    )
    query = """\
      query TestQuery($id: ID!) {
        project(id: $id) {
          milestones {
            mixedAnnotatedPrefetch
            mixedPrefetchAnnotated
          }
        }
      }
    """

    res = gql_client.query(query, variables={"id": project_id}, assert_no_errors=False)
    assert res.errors is None
    assert res.data == {
        "project": {
            "milestones": [
                {
                    "mixedAnnotatedPrefetch": "dummy",
                    "mixedPrefetchAnnotated": "dummy",
                }
            ],
        }
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("gql_client", ["sync", "async"], indirect=True)
def test_nested_annotation_via_select_related(db, gql_client: GraphQLTestClient):
    """Test that annotations work on nested types accessed via select_related.

    Regression test for https://github.com/strawberry-graphql/strawberry-django/issues/549
    and https://github.com/strawberry-graphql/strawberry-django/issues/743

    When querying a nested type (e.g., issue.milestone.project) via select_related,
    annotations on the nested type should work correctly. Previously, the optimizer
    would try to annotate the outer queryset with a prefixed path (e.g.,
    `milestone__project__annotation`), but this doesn't populate the annotation on
    the nested object - it populates it on the root object.
    """
    from django.db.models.functions import Upper

    @strawberry_django.type(Project)
    class ProjectTypeWithAnnotation:
        name: strawberry.auto
        name_upper: str = strawberry_django.field(
            annotate=Upper("name"),
        )

    @strawberry_django.type(Milestone)
    class MilestoneTypeWithAnnotation:
        name: strawberry.auto
        project: ProjectTypeWithAnnotation

    @strawberry_django.type(Issue)
    class IssueTypeWithAnnotation:
        name: strawberry.auto
        milestone: MilestoneTypeWithAnnotation

    @strawberry.type
    class Query:
        issues: list[IssueTypeWithAnnotation] = strawberry_django.field()

    schema = strawberry.Schema(
        query=Query,
        extensions=[DjangoOptimizerExtension],
    )

    project = ProjectFactory.create(name="TestProject")
    milestone = MilestoneFactory.create(project=project, name="Milestone1")
    IssueFactory.create(milestone=milestone, name="Issue1")

    query = """\
      query TestQuery {
        issues {
          name
          milestone {
            name
            project {
              name
              nameUpper
            }
          }
        }
      }
    """

    result = schema.execute_sync(query)
    assert result.errors is None, result.errors
    assert result.data == {
        "issues": [
            {
                "name": "Issue1",
                "milestone": {
                    "name": "Milestone1",
                    "project": {
                        "name": "TestProject",
                        "nameUpper": "TESTPROJECT",
                    },
                },
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
def test_annotation_on_type_via_immediate_fk(db):
    """Test that annotations work on types accessed via an immediate FK (1-level deep).

    Regression test for https://github.com/strawberry-graphql/strawberry-django/issues/869

    When querying a nested type via FK (e.g., milestone.project) where the nested type
    has an annotated field, the optimizer should use prefetch_related instead of
    select_related so the annotation is applied to the related model's queryset.
    """
    from django.db.models import Count

    @strawberry_django.type(Project)
    class ProjectTypeWithAnnotation:
        name: strawberry.auto
        milestone_count: int = strawberry_django.field(
            annotate=Count("milestone"),
        )

    @strawberry_django.type(Milestone)
    class MilestoneTypeWithAnnotation:
        name: strawberry.auto
        project: ProjectTypeWithAnnotation

    @strawberry.type
    class Query:
        milestones: list[MilestoneTypeWithAnnotation] = strawberry_django.field()

    schema = strawberry.Schema(
        query=Query,
        extensions=[DjangoOptimizerExtension],
    )

    project = ProjectFactory.create(name="TestProject")
    MilestoneFactory.create(project=project, name="M1")
    MilestoneFactory.create(project=project, name="M2")

    query = """\
      query TestQuery {
        milestones {
          name
          project {
            name
            milestoneCount
          }
        }
      }
    """

    result = schema.execute_sync(query)
    assert result.errors is None, result.errors
    assert result.data is not None
    milestones = sorted(result.data["milestones"], key=operator.itemgetter("name"))
    assert milestones == [
        {
            "name": "M1",
            "project": {
                "name": "TestProject",
                "milestoneCount": 2,
            },
        },
        {
            "name": "M2",
            "project": {
                "name": "TestProject",
                "milestoneCount": 2,
            },
        },
    ]


@pytest.mark.django_db(transaction=True)
def test_annotation_on_type_via_immediate_fk_dict_style(db):
    """Test dict-style annotate on type accessed via FK (1-level deep).

    Regression test for https://github.com/strawberry-graphql/strawberry-django/issues/869

    Uses annotate={"key": expr} format (as reported in the issue) instead of
    annotate=expr shorthand.
    """
    from django.db.models import Count

    @strawberry_django.type(Milestone)
    class MilestoneTypeWithAnnotation:
        name: strawberry.auto
        issue_count: int = strawberry_django.field(
            annotate={"issue_count": Count("issue")},
        )

    @strawberry_django.type(Issue)
    class IssueTypeWithAnnotation:
        name: strawberry.auto
        milestone: MilestoneTypeWithAnnotation

    @strawberry.type
    class Query:
        issues: list[IssueTypeWithAnnotation] = strawberry_django.field()

    schema = strawberry.Schema(
        query=Query,
        extensions=[DjangoOptimizerExtension],
    )

    project = ProjectFactory.create(name="TestProject")
    milestone = MilestoneFactory.create(project=project, name="Milestone1")
    IssueFactory.create(milestone=milestone, name="Issue1")
    IssueFactory.create(milestone=milestone, name="Issue2")

    query = """\
      query TestQuery {
        issues {
          name
          milestone {
            name
            issueCount
          }
        }
      }
    """

    result = schema.execute_sync(query)
    assert result.errors is None, result.errors
    assert result.data is not None
    issues = sorted(result.data["issues"], key=operator.itemgetter("name"))
    assert issues == [
        {
            "name": "Issue1",
            "milestone": {
                "name": "Milestone1",
                "issueCount": 2,
            },
        },
        {
            "name": "Issue2",
            "milestone": {
                "name": "Milestone1",
                "issueCount": 2,
            },
        },
    ]


@pytest.mark.django_db(transaction=True)
def test_annotation_on_type_via_reverse_one_to_one(db):
    """Test annotations on type accessed via reverse OneToOne.

    Regression test for https://github.com/strawberry-graphql/strawberry-django/issues/869

    When querying User → assigned_role (reverse OneToOne) where
    UserAssignedRoleType has an annotation, the optimizer should use
    prefetch_related instead of select_related.
    """
    from django.contrib.auth import get_user_model
    from django.db.models import Value
    from django.db.models.functions import Upper

    from tests.projects.models import Role, UserAssignedRole

    @strawberry_django.type(UserAssignedRole)
    class UserAssignedRoleTypeWithAnnotation:
        role_name_upper: str = strawberry_django.field(
            annotate=Upper(Value("ADMIN")),
        )

    @strawberry_django.type(get_user_model())
    class UserTypeWithAssignedRole:
        username: strawberry.auto
        assigned_role: UserAssignedRoleTypeWithAnnotation | None

    @strawberry.type
    class Query:
        users: list[UserTypeWithAssignedRole] = strawberry_django.field()

    schema = strawberry.Schema(
        query=Query,
        extensions=[DjangoOptimizerExtension],
    )

    user = UserFactory.create(username="testuser")
    role = Role.objects.create(name="Admin")
    UserAssignedRole.objects.create(user=user, role=role)

    query = """\
      query TestQuery {
        users {
          username
          assignedRole {
            roleNameUpper
          }
        }
      }
    """

    result = schema.execute_sync(query)
    assert result.errors is None, result.errors
    assert result.data is not None
    users = [u for u in result.data["users"] if u["username"] == "testuser"]
    assert len(users) == 1
    assert users[0] == {
        "username": "testuser",
        "assignedRole": {
            "roleNameUpper": "ADMIN",
        },
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("gql_client", ["sync"], indirect=True)
def test_prefetch_related_without_explicit_ordering(db, gql_client: GraphQLTestClient):
    """Test that prefetch_related works correctly without explicit ordering.

    Regression test for https://github.com/strawberry-graphql/strawberry-django/issues/772

    When using prefetch_related with a custom queryset that has no explicit ordering,
    the deterministic ordering added by get_queryset should not break the prefetch cache.

    This uses to_attr which is the recommended approach.
    """

    @strawberry_django.type(Milestone)
    class MilestoneTypeTest:
        name: strawberry.auto

    @strawberry_django.type(Project)
    class ProjectTypeTest:
        name: strawberry.auto

        @strawberry_django.field(
            prefetch_related=[
                Prefetch(
                    "milestones",
                    queryset=Milestone.objects.filter(name__startswith="Test"),
                    to_attr="_filtered_milestones",
                )
            ]
        )
        def filtered_milestones(self) -> list[MilestoneTypeTest]:
            return self._filtered_milestones  # type: ignore

    @strawberry.type
    class Query:
        projects: list[ProjectTypeTest] = strawberry_django.field()

    schema = strawberry.Schema(
        query=Query,
        extensions=[DjangoOptimizerExtension],
    )

    # Create test data
    project1 = ProjectFactory.create(name="Project1")
    project2 = ProjectFactory.create(name="Project2")
    MilestoneFactory.create(project=project1, name="TestMilestone1")
    MilestoneFactory.create(project=project1, name="TestMilestone2")
    MilestoneFactory.create(
        project=project1, name="OtherMilestone"
    )  # Should be filtered out
    MilestoneFactory.create(project=project2, name="TestMilestone3")

    query = """\
      query TestQuery {
        projects {
          name
          filteredMilestones {
            name
          }
        }
      }
    """

    # This should not cause N+1 queries
    # Expected: 1 query for projects + 1 query for prefetched milestones = 2 queries
    if DjangoOptimizerExtension.enabled.get():
        with assert_num_queries(2):
            result = schema.execute_sync(query)
    else:
        result = schema.execute_sync(query)

    assert result.errors is None, result.errors
    assert result.data is not None
    # Verify the data is correct
    projects_data = sorted(result.data["projects"], key=operator.itemgetter("name"))
    assert len(projects_data) == 2
    assert projects_data[0]["name"] == "Project1"
    assert len(projects_data[0]["filteredMilestones"]) == 2
    assert projects_data[1]["name"] == "Project2"
    assert len(projects_data[1]["filteredMilestones"]) == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("gql_client", ["sync"], indirect=True)
def test_prefetch_related_without_to_attr(db, gql_client: GraphQLTestClient):
    """Test that prefetch_related works correctly without to_attr.

    Additional regression test for https://github.com/strawberry-graphql/strawberry-django/issues/772

    When using prefetch_related without to_attr, accessing the related manager
    should still use the prefetch cache.
    """

    @strawberry_django.type(Milestone)
    class MilestoneTypeTest:
        name: strawberry.auto

    @strawberry_django.type(Project)
    class ProjectTypeTest:
        name: strawberry.auto

        # Using prefetch_related without to_attr
        @strawberry_django.field(
            prefetch_related=[
                Prefetch(
                    "milestones",
                    queryset=Milestone.objects.filter(name__startswith="Test"),
                )
            ]
        )
        def filtered_milestones(self) -> list[MilestoneTypeTest]:
            # This should use the prefetch cache, not trigger a new query
            return list(self.milestones.all())  # type: ignore

    @strawberry.type
    class Query:
        projects: list[ProjectTypeTest] = strawberry_django.field()

    schema = strawberry.Schema(
        query=Query,
        extensions=[DjangoOptimizerExtension],
    )

    # Create test data
    project1 = ProjectFactory.create(name="Project1")
    project2 = ProjectFactory.create(name="Project2")
    MilestoneFactory.create(project=project1, name="TestMilestone1")
    MilestoneFactory.create(project=project1, name="TestMilestone2")
    MilestoneFactory.create(
        project=project1, name="OtherMilestone"
    )  # Won't be prefetched due to filter
    MilestoneFactory.create(project=project2, name="TestMilestone3")

    query = """\
      query TestQuery {
        projects {
          name
          filteredMilestones {
            name
          }
        }
      }
    """

    # Without to_attr, calling .all() might not use the prefetch cache
    # This test may fail, showing the N+1 issue
    if DjangoOptimizerExtension.enabled.get():
        with assert_num_queries(2):
            result = schema.execute_sync(query)
    else:
        result = schema.execute_sync(query)

    assert result.errors is None, result.errors


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("gql_client", ["sync"], indirect=True)
def test_merged_custom_prefetches(db, gql_client: GraphQLTestClient):
    """Test that duplicated prefetch_related hints are correctly merged."""

    @strawberry_django.type(Issue)
    class IssueTypeTest:
        name: strawberry.auto
        kind: strawberry.auto

    @strawberry_django.type(Milestone)
    class MilestoneTypeTest:
        name: strawberry.auto

        @strawberry_django.field()
        @staticmethod
        def bugs(parent: strawberry.Parent[Milestone]) -> list[IssueTypeTest]:
            # This is not the most efficient way to do this, it only exists for this test.
            return getattr(parent, "bugs", [])

        @strawberry_django.field()
        @staticmethod
        def has_bugs(parent: strawberry.Parent[Milestone]) -> bool:
            # This is not the most efficient way to do this, it only exists for this test.
            return bool(getattr(parent, "bugs", None))

    @strawberry_django.type(Project)
    class ProjectTypeTest:
        name: strawberry.auto

        @staticmethod
        def _prefetch_custom_milestones(_: GraphQLResolveInfo) -> Prefetch:
            return Prefetch(
                "milestones",
                to_attr="custom_milestones",
                queryset=Milestone.objects.all().prefetch_related(
                    Prefetch(
                        "issues",
                        Issue.objects.all().filter(kind=Issue.Kind.BUG),
                        to_attr="bugs",
                    )
                ),
            )

        @strawberry_django.field(prefetch_related=_prefetch_custom_milestones)
        @staticmethod
        def milestones(parent: strawberry.Parent[Project]) -> list[MilestoneTypeTest]:
            return getattr(parent, "custom_milestones", [])

        @strawberry_django.field(prefetch_related=_prefetch_custom_milestones)
        @staticmethod
        def milestones2(parent: strawberry.Parent[Project]) -> list[MilestoneTypeTest]:
            return getattr(parent, "custom_milestones", [])

    @strawberry.type
    class Query:
        projects: list[ProjectTypeTest] = strawberry_django.field()

    schema = strawberry.Schema(
        query=Query,
        extensions=[DjangoOptimizerExtension],
    )

    # Create test data
    project1 = ProjectFactory.create(name="Project1")
    project2 = ProjectFactory.create(name="Project2")
    milestone1 = MilestoneFactory.create(project=project1, name="Milestone1")
    milestone2 = MilestoneFactory.create(project=project1, name="Milestone2")
    milestone3 = MilestoneFactory.create(project=project2, name="Milestone3")
    IssueFactory.create(milestone=milestone1, name="TestFeat1M1", kind="f")
    IssueFactory.create(milestone=milestone1, name="TestBug1M1", kind="b")
    IssueFactory.create(milestone=milestone1, name="TestFeat2M1", kind="f")
    IssueFactory.create(milestone=milestone2, name="TestFeat1M2", kind="f")
    IssueFactory.create(milestone=milestone3, name="TestFeat1M3", kind="f")
    IssueFactory.create(milestone=milestone3, name="TestBug1M3", kind="b")

    query = """\
      query TestQuery {
        projects {
          name
          milestones {
            name
            hasBugs
            bugs { name }
          }
          milestones2 { name }
        }
      }
    """
    if DjangoOptimizerExtension.enabled.get():
        with assert_num_queries(3):
            result = schema.execute_sync(query)
    else:
        result = schema.execute_sync(query)

    assert result.errors is None, result.errors
    assert result.data == {
        "projects": [
            {
                "name": "Project1",
                "milestones": [
                    {
                        "name": "Milestone1",
                        "hasBugs": True,
                        "bugs": [{"name": "TestBug1M1"}],
                    },
                    {"name": "Milestone2", "hasBugs": False, "bugs": []},
                ],
                "milestones2": [
                    {"name": "Milestone1"},
                    {"name": "Milestone2"},
                ],
            },
            {
                "name": "Project2",
                "milestones": [
                    {
                        "name": "Milestone3",
                        "hasBugs": True,
                        "bugs": [{"name": "TestBug1M3"}],
                    },
                ],
                "milestones2": [
                    {"name": "Milestone3"},
                ],
            },
        ],
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("gql_client", ["sync"], indirect=True)
def test_prefetch_with_optimize_and_only(db, gql_client: GraphQLTestClient):
    """Prefetch with optimize() and only optimization does not cause N+1.

    Regression test for https://github.com/strawberry-graphql/strawberry-django/issues/862
    """
    from strawberry_django.optimizer import optimize

    @strawberry_django.type(Milestone)
    class MilestoneTypeTest:
        name: strawberry.auto

    @strawberry_django.type(Project)
    class ProjectTypeTest:
        name: strawberry.auto

        @strawberry_django.field(
            prefetch_related=[
                lambda info: Prefetch(
                    "milestones",
                    queryset=optimize(
                        Milestone.objects.filter(name__startswith="Test"),
                        info,
                    ),
                    to_attr="_optimized_milestones",
                )
            ]
        )
        def optimized_milestones(self) -> list[MilestoneTypeTest]:
            return self._optimized_milestones  # type: ignore

    @strawberry.type
    class Query:
        projects: list[ProjectTypeTest] = strawberry_django.field()

    schema = strawberry.Schema(
        query=Query,
        extensions=[DjangoOptimizerExtension],
    )

    project1 = ProjectFactory.create(name="Project1")
    project2 = ProjectFactory.create(name="Project2")
    MilestoneFactory.create(project=project1, name="TestMilestone1")
    MilestoneFactory.create(project=project1, name="TestMilestone2")
    MilestoneFactory.create(project=project1, name="OtherMilestone")
    MilestoneFactory.create(project=project2, name="TestMilestone3")

    query = """\
      query TestQuery {
        projects {
          name
          optimizedMilestones {
            name
          }
        }
      }
    """

    with assert_num_queries(2):
        result = schema.execute_sync(query)

    assert result.errors is None, result.errors
    projects_data = sorted(result.data["projects"], key=operator.itemgetter("name"))
    assert len(projects_data) == 2
    assert projects_data[0]["name"] == "Project1"
    assert len(projects_data[0]["optimizedMilestones"]) == 2
    assert projects_data[1]["name"] == "Project2"
    assert len(projects_data[1]["optimizedMilestones"]) == 1
