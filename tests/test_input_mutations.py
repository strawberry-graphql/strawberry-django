import pytest
from strawberry.relay import from_base64, to_base64

from tests.utils import GraphQLTestClient, assert_num_queries

from .projects.faker import (
    IssueFactory,
    MilestoneFactory,
    ProjectFactory,
    TagFactory,
    UserFactory,
)
from .projects.models import Issue, Milestone, Project


@pytest.mark.django_db(transaction=True)
def test_input_mutation(db, gql_client: GraphQLTestClient):
    query = """
    mutation CreateProject ($input: CreateProjectInput!) {
        createProject (input: $input) {
          ... on ProjectType {
            name
            cost
            dueDate
          }
        }
      }
    """
    with assert_num_queries(1):
        res = gql_client.query(
            query,
            {
                "input": {
                    "name": "Some Project",
                    "cost": "12.50",
                    "dueDate": "2030-01-01",
                },
            },
        )
        assert res.data == {
            "createProject": {
                "name": "Some Project",
                # The cost is properly set, but this user doesn't have
                # permission to see it
                "cost": None,
                "dueDate": "2030-01-01",
            },
        }


@pytest.mark.django_db(transaction=True)
def test_input_mutation_with_internal_error_code(db, gql_client: GraphQLTestClient):
    query = """
    mutation CreateProject ($input: CreateProjectInput!) {
        createProject (input: $input) {
          ... on ProjectType {
            name
            cost
          }
          ... on OperationInfo {
            messages {
              field
              message
              kind
              code
            }
          }
        }
      }
    """
    with assert_num_queries(0):
        res = gql_client.query(
            query,
            {"input": {"name": 100 * "way to long", "cost": "10.40"}},
        )
        assert res.data == {
            "createProject": {
                "messages": [
                    {
                        "field": "name",
                        "kind": "VALIDATION",
                        "message": (
                            "Ensure this value has at most 255 characters (it has"
                            " 1100)."
                        ),
                        "code": "max_length",
                    },
                ],
            },
        }


@pytest.mark.django_db(transaction=True)
def test_input_mutation_with_explicit_error_code(db, gql_client: GraphQLTestClient):
    query = """
    mutation CreateProject ($input: CreateProjectInput!) {
        createProject (input: $input) {
          ... on ProjectType {
            name
            cost
          }
          ... on OperationInfo {
            messages {
              field
              message
              kind
              code
            }
          }
        }
      }
    """
    with assert_num_queries(0):
        res = gql_client.query(
            query,
            {"input": {"name": "Some Project", "cost": "-1"}},
        )
        assert res.data == {
            "createProject": {
                "messages": [
                    {
                        "field": "cost",
                        "kind": "VALIDATION",
                        "message": "Cost cannot be lower than zero",
                        "code": "min_cost",
                    },
                ],
            },
        }


@pytest.mark.django_db(transaction=True)
def test_input_mutation_with_errors(db, gql_client: GraphQLTestClient):
    query = """
    mutation CreateProject ($input: CreateProjectInput!) {
        createProject (input: $input) {
          ... on ProjectType {
            name
            cost
          }
          ... on OperationInfo {
            messages {
              field
              message
              kind
              code
            }
          }
        }
      }
    """
    with assert_num_queries(0):
        res = gql_client.query(
            query,
            {"input": {"name": "Some Project", "cost": "501.50"}},
        )
        assert res.data == {
            "createProject": {
                "messages": [
                    {
                        "field": "cost",
                        "kind": "VALIDATION",
                        "message": "Cost cannot be higher than 500",
                        "code": None,
                    },
                ],
            },
        }


@pytest.mark.django_db(transaction=True)
def test_input_create_mutation(db, gql_client: GraphQLTestClient):
    query = """
    mutation CreateIssue ($input: IssueInput!) {
      createIssue (input: $input) {
        __typename
        ... on OperationInfo {
          messages {
            kind
            field
            message
          }
        }
        ... on IssueType {
          id
          name
          milestone {
            id
            name
          }
          priority
          kind
          tags {
            id
            name
          }
        }
      }
    }
    """
    milestone = MilestoneFactory.create()
    tags = TagFactory.create_batch(4)
    res = gql_client.query(
        query,
        {
            "input": {
                "name": "Some Issue",
                "milestone": {"id": to_base64("MilestoneType", milestone.pk)},
                "priority": 5,
                "kind": Issue.Kind.FEATURE.value,
                "tags": [{"id": to_base64("TagType", t.pk)} for t in tags],
            },
        },
    )
    assert res.data
    assert isinstance(res.data["createIssue"], dict)

    typename, pk = from_base64(res.data["createIssue"].pop("id"))
    assert typename == "IssueType"
    assert {frozenset(t.items()) for t in res.data["createIssue"].pop("tags")} == {
        frozenset({"id": to_base64("TagType", t.pk), "name": t.name}.items())
        for t in tags
    }

    assert res.data == {
        "createIssue": {
            "__typename": "IssueType",
            "name": "Some Issue",
            "milestone": {
                "id": to_base64("MilestoneType", milestone.pk),
                "name": milestone.name,
            },
            "priority": 5,
            "kind": "f",
        },
    }
    issue = Issue.objects.get(pk=pk)
    assert issue.name == "Some Issue"
    assert issue.priority == 5
    assert issue.kind == Issue.Kind.FEATURE
    assert issue.milestone == milestone
    assert set(issue.tags.all()) == set(tags)


@pytest.mark.django_db(transaction=True)
def test_input_create_mutation_nested_creation(db, gql_client: GraphQLTestClient):
    query = """
    mutation CreateMilestone ($input: MilestoneInput!) {
      createMilestone (input: $input) {
        __typename
        ... on OperationInfo {
          messages {
            kind
            field
            message
          }
        }
        ... on MilestoneType {
          id
          name
          project {
            id
            name
          }
        }
      }
    }
    """
    assert not Project.objects.filter(name="New Project").exists()

    res = gql_client.query(
        query,
        {
            "input": {
                "name": "Some Milestone",
                "project": {
                    "name": "New Project",
                },
            },
        },
    )
    assert res.data
    assert isinstance(res.data["createMilestone"], dict)

    typename, pk = from_base64(res.data["createMilestone"].pop("id"))
    assert typename == "MilestoneType"

    project = Project.objects.get(name="New Project")

    assert res.data == {
        "createMilestone": {
            "__typename": "MilestoneType",
            "name": "Some Milestone",
            "project": {
                "id": to_base64("ProjectType", project.pk),
                "name": project.name,
            },
        },
    }


@pytest.mark.django_db(transaction=True)
def test_input_create_with_m2m_mutation(db, gql_client: GraphQLTestClient):
    query = """
    mutation CreateMilestone ($input: MilestoneInput!) {
      createMilestone (input: $input) {
        __typename
        ... on OperationInfo {
          messages {
            kind
            field
            message
          }
        }
        ... on MilestoneType {
          id
          name
          project {
            id
            name
          }
          issues {
            id
            name
          }
        }
      }
    }
    """
    project = ProjectFactory.create()

    res = gql_client.query(
        query,
        {
            "input": {
                "name": "Some Milestone",
                "project": {
                    "id": to_base64("ProjectType", project.pk),
                },
                "issues": [
                    {
                        "name": "Milestone Issue 1",
                    },
                    {
                        "name": "Milestone Issue 2",
                    },
                ],
            },
        },
    )
    assert res.data
    assert isinstance(res.data["createMilestone"], dict)

    typename, pk = from_base64(res.data["createMilestone"].pop("id"))
    assert typename == "MilestoneType"

    issues = res.data["createMilestone"].pop("issues")
    assert {i["name"] for i in issues} == {"Milestone Issue 1", "Milestone Issue 2"}

    assert res.data == {
        "createMilestone": {
            "__typename": "MilestoneType",
            "name": "Some Milestone",
            "project": {
                "id": to_base64("ProjectType", project.pk),
                "name": project.name,
            },
        },
    }

    milestone = Milestone.objects.get(pk=pk)
    assert milestone.name == "Some Milestone"
    assert milestone.project == project
    assert {i.name for i in milestone.issues.all()} == {
        "Milestone Issue 1",
        "Milestone Issue 2",
    }


@pytest.mark.django_db(transaction=True)
def test_input_update_mutation(db, gql_client: GraphQLTestClient):
    query = """
    mutation CreateIssue ($input: IssueInputPartial!) {
      updateIssue (input: $input) {
        __typename
        ... on OperationInfo {
          messages {
            kind
            field
            message
          }
        }
        ... on IssueType {
          id
          name
          milestone {
            id
            name
          }
          priority
          kind
          tags {
            id
            name
          }
        }
      }
    }
    """
    issue = IssueFactory.create(
        name="Old name",
        milestone=MilestoneFactory.create(),
        priority=0,
        kind=Issue.Kind.BUG,
    )
    tags = TagFactory.create_batch(4)
    issue.tags.set(tags)

    milestone = MilestoneFactory.create()
    add_tags = TagFactory.create_batch(2)
    remove_tags = tags[:2]

    res = gql_client.query(
        query,
        {
            "input": {
                "id": to_base64("IssueType", issue.pk),
                "name": "New name",
                "milestone": {"id": to_base64("MilestoneType", milestone.pk)},
                "priority": 5,
                "kind": Issue.Kind.FEATURE.value,
                "tags": {
                    "add": [{"id": to_base64("TagType", t.pk)} for t in add_tags],
                    "remove": [{"id": to_base64("TagType", t.pk)} for t in remove_tags],
                },
            },
        },
    )
    assert res.data
    assert isinstance(res.data["updateIssue"], dict)

    expected_tags = tags + add_tags
    for removed in remove_tags:
        expected_tags.remove(removed)

    assert {frozenset(t.items()) for t in res.data["updateIssue"].pop("tags")} == {
        frozenset({"id": to_base64("TagType", t.pk), "name": t.name}.items())
        for t in expected_tags
    }

    assert res.data == {
        "updateIssue": {
            "__typename": "IssueType",
            "id": to_base64("IssueType", issue.pk),
            "name": "New name",
            "milestone": {
                "id": to_base64("MilestoneType", milestone.pk),
                "name": milestone.name,
            },
            "priority": 5,
            "kind": "f",
        },
    }

    issue.refresh_from_db()
    assert issue.name == "New name"
    assert issue.priority == 5
    assert issue.kind == Issue.Kind.FEATURE
    assert issue.milestone == milestone
    assert set(issue.tags.all()) == set(expected_tags)


@pytest.mark.django_db(transaction=True)
def test_input_nested_update_mutation(db, gql_client: GraphQLTestClient):
    query = """
    mutation CreateIssue ($input: IssueInputPartial!) {
      updateIssue (input: $input) {
        __typename
        ... on OperationInfo {
          messages {
            kind
            field
            message
          }
        }
        ... on IssueType {
          id
          name
          milestone {
            id
            name
          }
          priority
          kind
        }
      }
    }
    """
    issue = IssueFactory.create(
        name="Old name",
        milestone=MilestoneFactory.create(),
        priority=0,
        kind=Issue.Kind.BUG,
    )
    milestone = MilestoneFactory.create(name="Something")

    res = gql_client.query(
        query,
        {
            "input": {
                "id": to_base64("IssueType", issue.pk),
                "name": "New name",
                "milestone": {
                    "id": to_base64("MilestoneType", milestone.pk),
                    "name": "foo",
                },
            },
        },
    )
    assert res.data
    assert isinstance(res.data["updateIssue"], dict)
    assert res.data["updateIssue"]["milestone"]["name"] == "foo"
    milestone.refresh_from_db()
    assert milestone.name == "foo"


@pytest.mark.django_db(transaction=True)
def test_input_update_m2m_set_not_null_mutation(db, gql_client: GraphQLTestClient):
    query = """
    mutation UpdateProject ($input: ProjectInputPartial!) {
      updateProject (input: $input) {
        __typename
        ... on OperationInfo {
          messages {
            kind
            field
            message
          }
        }
        ... on ProjectType {
          id
          name
          dueDate
          milestones {
            id
            name
          }
          cost
        }
      }
    }
    """
    project = ProjectFactory.create(
        name="Project Name",
    )
    milestone_1 = MilestoneFactory.create(project=project)
    milestone_1_id = to_base64("MilestoneType", milestone_1.pk)
    MilestoneFactory.create(project=project)

    res = gql_client.query(
        query,
        {
            "input": {
                "id": to_base64("ProjectType", project.pk),
                "milestones": [{"id": milestone_1_id}],
            },
        },
    )
    assert res.data
    assert isinstance(res.data["updateProject"], dict)

    assert len(res.data["updateProject"]["milestones"]) == 1
    assert res.data["updateProject"]["milestones"][0]["id"] == milestone_1_id


@pytest.mark.django_db(transaction=True)
def test_input_update_m2m_set_mutation(db, gql_client: GraphQLTestClient):
    query = """
    mutation CreateIssue ($input: IssueInputPartial!) {
      updateIssue (input: $input) {
        __typename
        ... on OperationInfo {
          messages {
            kind
            field
            message
          }
        }
        ... on IssueType {
          id
          name
          milestone {
            id
            name
          }
          priority
          kind
          tags {
            id
            name
          }
          issueAssignees {
            owner
            user {
              id
            }
          }
        }
      }
    }
    """
    issue = IssueFactory.create(
        name="Old name",
        milestone=MilestoneFactory.create(),
        priority=0,
        kind=Issue.Kind.BUG,
    )
    tags = TagFactory.create_batch(4)
    issue.tags.set(tags)
    milestone = MilestoneFactory.create()

    user_1 = UserFactory.create()
    user_2 = UserFactory.create()
    user_3 = UserFactory.create()

    assignee = issue.issue_assignees.create(
        user=user_3,
        owner=False,
    )

    res = gql_client.query(
        query,
        {
            "input": {
                "id": to_base64("IssueType", issue.pk),
                "name": "New name",
                "milestone": {"id": to_base64("MilestoneType", milestone.pk)},
                "priority": 5,
                "kind": Issue.Kind.FEATURE.value,
                "tags": {
                    "set": [
                        {"id": None, "name": "Foobar"},
                        {"name": "Foobin"},
                    ],
                },
                "issueAssignees": {
                    "set": [
                        {
                            "user": {"id": to_base64("UserType", user_1.username)},
                        },
                        {
                            "user": {"id": to_base64("UserType", user_2.username)},
                            "owner": True,
                        },
                        {
                            "id": to_base64("AssigneeType", assignee.pk),
                            "owner": True,
                        },
                    ],
                },
            },
        },
    )
    assert res.data
    assert isinstance(res.data["updateIssue"], dict)

    tags = res.data["updateIssue"].pop("tags")
    assert len(tags) == 2
    assert {t["name"] for t in tags} == {"Foobar", "Foobin"}

    assert {
        (r["user"]["id"], r["owner"])
        for r in res.data["updateIssue"].pop("issueAssignees")
    } == {
        (to_base64("UserType", user_1.username), False),
        (to_base64("UserType", user_2.username), True),
        (to_base64("UserType", user_3.username), True),
    }

    assert res.data == {
        "updateIssue": {
            "__typename": "IssueType",
            "id": to_base64("IssueType", issue.pk),
            "name": "New name",
            "milestone": {
                "id": to_base64("MilestoneType", milestone.pk),
                "name": milestone.name,
            },
            "priority": 5,
            "kind": "f",
        },
    }

    issue.refresh_from_db()
    assert issue.name == "New name"
    assert issue.priority == 5
    assert issue.kind == Issue.Kind.FEATURE
    assert issue.milestone == milestone


@pytest.mark.django_db(transaction=True)
def test_input_update_m2m_set_through_mutation(db, gql_client: GraphQLTestClient):
    query = """
    mutation CreateIssue ($input: IssueInputPartial!) {
      updateIssue (input: $input) {
        __typename
        ... on OperationInfo {
          messages {
            kind
            field
            message
          }
        }
        ... on IssueType {
          id
          name
          milestone {
            id
            name
          }
          priority
          kind
          tags {
            id
            name
          }
          issueAssignees {
            owner
            user {
              id
            }
          }
        }
      }
    }
    """
    issue = IssueFactory.create(
        name="Old name",
        milestone=MilestoneFactory.create(),
        priority=0,
        kind=Issue.Kind.BUG,
    )
    tags = TagFactory.create_batch(4)
    issue.tags.set(tags)
    milestone = MilestoneFactory.create()

    user_1 = UserFactory.create()
    user_2 = UserFactory.create()
    user_3 = UserFactory.create()

    issue.issue_assignees.create(
        user=user_3,
        owner=False,
    )

    res = gql_client.query(
        query,
        {
            "input": {
                "id": to_base64("IssueType", issue.pk),
                "name": "New name",
                "milestone": {"id": to_base64("MilestoneType", milestone.pk)},
                "priority": 5,
                "kind": Issue.Kind.FEATURE.value,
                "tags": {
                    "set": [
                        {"id": None, "name": "Foobar"},
                        {"name": "Foobin"},
                    ],
                },
                "assignees": {
                    "set": [
                        {
                            "id": to_base64("UserType", user_1.username),
                        },
                        {
                            "id": to_base64("UserType", user_2.username),
                            "throughDefaults": {
                                "owner": True,
                            },
                        },
                        {
                            "id": to_base64("UserType", user_3.username),
                            "throughDefaults": {
                                "owner": True,
                            },
                        },
                    ],
                },
            },
        },
    )
    assert res.data
    assert isinstance(res.data["updateIssue"], dict)

    tags = res.data["updateIssue"].pop("tags")
    assert len(tags) == 2
    assert {t["name"] for t in tags} == {"Foobar", "Foobin"}

    assert {
        (r["user"]["id"], r["owner"])
        for r in res.data["updateIssue"].pop("issueAssignees")
    } == {
        (to_base64("UserType", user_1.username), False),
        (to_base64("UserType", user_2.username), True),
        (to_base64("UserType", user_3.username), True),
    }

    assert res.data == {
        "updateIssue": {
            "__typename": "IssueType",
            "id": to_base64("IssueType", issue.pk),
            "name": "New name",
            "milestone": {
                "id": to_base64("MilestoneType", milestone.pk),
                "name": milestone.name,
            },
            "priority": 5,
            "kind": "f",
        },
    }

    issue.refresh_from_db()
    assert issue.name == "New name"
    assert issue.priority == 5
    assert issue.kind == Issue.Kind.FEATURE
    assert issue.milestone == milestone


@pytest.mark.django_db(transaction=True)
def test_input_update_mutation_with_key_attr(db, gql_client: GraphQLTestClient):
    query = """
    mutation UpdateIssueWithKeyAttr ($input: IssueInputPartialWithoutId!) {
      updateIssueWithKeyAttr (input: $input) {
        __typename
        ... on OperationInfo {
          messages {
            kind
            field
            message
          }
        }
        ... on IssueType {
          name
          milestone {
            id
            name
          }
          priority
          kind
          tags {
            id
            name
          }
        }
      }
    }
    """
    issue = IssueFactory.create(
        name="Unique name",
        milestone=MilestoneFactory.create(),
        priority=0,
        kind=Issue.Kind.BUG,
    )
    tags = TagFactory.create_batch(4)
    issue.tags.set(tags)

    milestone = MilestoneFactory.create()
    add_tags = TagFactory.create_batch(2)
    remove_tags = tags[:2]

    res = gql_client.query(
        query,
        {
            "input": {
                "name": "Unique name",
                "milestone": {"id": to_base64("MilestoneType", milestone.pk)},
                "priority": 5,
                "kind": Issue.Kind.FEATURE.value,
                "tags": {
                    "add": [{"id": to_base64("TagType", t.pk)} for t in add_tags],
                    "remove": [{"id": to_base64("TagType", t.pk)} for t in remove_tags],
                },
            },
        },
    )
    assert res.data
    assert isinstance(res.data["updateIssueWithKeyAttr"], dict)

    expected_tags = tags + add_tags
    for removed in remove_tags:
        expected_tags.remove(removed)

    assert {
        frozenset(t.items()) for t in res.data["updateIssueWithKeyAttr"].pop("tags")
    } == {
        frozenset({"id": to_base64("TagType", t.pk), "name": t.name}.items())
        for t in expected_tags
    }

    assert res.data == {
        "updateIssueWithKeyAttr": {
            "__typename": "IssueType",
            "name": "Unique name",
            "milestone": {
                "id": to_base64("MilestoneType", milestone.pk),
                "name": milestone.name,
            },
            "priority": 5,
            "kind": "f",
        },
    }

    issue.refresh_from_db()
    assert issue.priority == 5
    assert issue.kind == Issue.Kind.FEATURE
    assert issue.milestone == milestone
    assert set(issue.tags.all()) == set(expected_tags)


@pytest.mark.django_db(transaction=True)
def test_input_delete_mutation(db, gql_client: GraphQLTestClient):
    query = """
    mutation DeleteIssue ($input: NodeInput!) {
      deleteIssue (input: $input) {
        __typename
        ... on OperationInfo {
          messages {
            kind
            field
            message
          }
        }
        ... on IssueType {
          id
          name
          milestone {
            id
            name
          }
          priority
          kind
        }
      }
    }
    """
    issue = IssueFactory.create()
    assert issue.milestone
    assert issue.kind

    res = gql_client.query(
        query,
        {
            "input": {
                "id": to_base64("IssueType", issue.pk),
            },
        },
    )
    assert res.data
    assert isinstance(res.data["deleteIssue"], dict)
    assert res.data == {
        "deleteIssue": {
            "__typename": "IssueType",
            "id": to_base64("IssueType", issue.pk),
            "name": issue.name,
            "milestone": {
                "id": to_base64("MilestoneType", issue.milestone.pk),
                "name": issue.milestone.name,
            },
            "priority": issue.priority,
            "kind": issue.kind.value,  # type: ignore
        },
    }

    with pytest.raises(Issue.DoesNotExist):
        Issue.objects.get(pk=issue.pk)


@pytest.mark.django_db(transaction=True)
def test_input_delete_mutation_with_key_attr(db, gql_client: GraphQLTestClient):
    query = """
    mutation DeleteIssue ($input: MilestoneIssueInput!) {
      deleteIssueWithKeyAttr (input: $input) {
        __typename
        ... on OperationInfo {
          messages {
            kind
            field
            message
          }
        }
        ... on IssueType {
          id
          name
          milestone {
            id
            name
          }
          priority
          kind
        }
      }
    }
    """
    issue = IssueFactory.create()
    assert issue.milestone
    assert issue.kind

    res = gql_client.query(
        query,
        {
            "input": {
                "name": issue.name,
            },
        },
    )
    assert res.data
    assert isinstance(res.data["deleteIssueWithKeyAttr"], dict)
    assert res.data == {
        "deleteIssueWithKeyAttr": {
            "__typename": "IssueType",
            "id": to_base64("IssueType", issue.pk),
            "name": issue.name,
            "milestone": {
                "id": to_base64("MilestoneType", issue.milestone.pk),
                "name": issue.milestone.name,
            },
            "priority": issue.priority,
            "kind": issue.kind.value,  # type: ignore
        },
    }

    with pytest.raises(Issue.DoesNotExist):
        Issue.objects.get(pk=issue.pk)


@pytest.mark.django_db(transaction=True)
def test_mutation_full_clean_without_kwargs(db, gql_client: GraphQLTestClient):
    query = """
    mutation CreateQuiz ($input: CreateQuizInput!) {
      createQuiz (input: $input) {
        __typename
        ... on OperationInfo {
          messages {
            kind
            field
            message
          }
        }
        ... on QuizType {
          title
          sequence
        }
      }
    }
    """
    res = gql_client.query(
        query,
        {
            "input": {
                "title": "ABC",
            },
        },
    )
    expected = {"createQuiz": {"__typename": "QuizType", "sequence": 1, "title": "ABC"}}
    assert res.data == expected
    res = gql_client.query(
        query,
        {
            "input": {
                "title": "ABC",
            },
        },
    )
    expected = {
        "createQuiz": {
            "__typename": "OperationInfo",
            "messages": [
                {
                    "field": "sequence",
                    "kind": "VALIDATION",
                    "message": "Quiz with this Sequence already exists.",
                },
            ],
        },
    }
    assert res.data == expected


@pytest.mark.django_db(transaction=True)
def test_mutation_full_clean_with_kwargs(db, gql_client: GraphQLTestClient):
    query = """
    mutation CreateQuiz ($input: CreateQuizInput!) {
      createQuiz (input: $input) {
        __typename
        ... on OperationInfo {
          messages {
            kind
            field
            message
          }
        }
        ... on QuizType {
          title
          sequence
        }
      }
    }
    """
    res = gql_client.query(
        query,
        {"input": {"title": "ABC", "fullCleanOptions": True}},
    )
    expected = {"createQuiz": {"__typename": "QuizType", "sequence": 1, "title": "ABC"}}
    assert res.data == expected

    res = gql_client.query(
        query,
        {"input": {"title": "ABC", "fullCleanOptions": True}},
    )
    expected = {"createQuiz": {"__typename": "QuizType", "sequence": 2, "title": "ABC"}}
    assert res.data == expected

    res = gql_client.query(
        query,
        {"input": {"title": "ABC", "fullCleanOptions": True}},
    )
    expected = {"createQuiz": {"__typename": "QuizType", "sequence": 3, "title": "ABC"}}
    assert res.data == expected

    res = gql_client.query(
        query,
        {"input": {"title": "ABC", "fullCleanOptions": True}},
    )
    expected = {"createQuiz": {"__typename": "QuizType", "sequence": 4, "title": "ABC"}}
    assert res.data == expected
