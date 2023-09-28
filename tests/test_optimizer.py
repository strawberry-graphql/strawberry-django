import datetime
from typing import Any, List, cast

import pytest
from django.utils import timezone
from strawberry.relay import to_base64

from strawberry_django.optimizer import DjangoOptimizerExtension

from .projects.faker import (
    IssueFactory,
    MilestoneFactory,
    ProjectFactory,
    StaffUserFactory,
    TagFactory,
    UserFactory,
)
from .projects.models import Assignee, Issue
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
def test_staff_query(db, gql_client: GraphQLTestClient):
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


@pytest.mark.django_db(transaction=True)
def test_interface_query(db, gql_client: GraphQLTestClient):
    query = """
      query TestQuery ($id: GlobalID!) {
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
        frozenset(d.items()) for d in cast(List, res.data["node"].pop("tags"))
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

    with assert_num_queries(2 if DjangoOptimizerExtension.enabled.get() else 18):
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
              milestoneAgain: milestone {
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
                        "milestoneAgain": m_res,
                    },
                )

    with assert_num_queries(2 if DjangoOptimizerExtension.enabled.get() else 56):
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
      query TestQuery ($node_id: GlobalID!) {
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
      query TestQuery ($node_id: GlobalID!) {
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
                    asserts_errors=False,
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

      query TestQuery ($node_id: GlobalID!) {
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
            otherIssues: issues {
              id
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
                "otherIssues": [],
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
                m_res["otherIssues"].append(
                    {
                        "id": to_base64("IssueType", i.id),
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
        with assert_num_queries(3 if DjangoOptimizerExtension.enabled.get() else 8):
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

    with assert_num_queries(3 if DjangoOptimizerExtension.enabled.get() else 5):
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

    with assert_num_queries(5):
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
      query TestQuery ($node_id: GlobalID!) {
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
                asserts_errors=False,
            )
            assert res.errors


@pytest.mark.django_db(transaction=True)
def test_query_annotate_with_callable(db, gql_client: GraphQLTestClient):
    query = """
      query TestQuery ($node_id: GlobalID!) {
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
                    asserts_errors=False,
                )
                assert res.errors
