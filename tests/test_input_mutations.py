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
from .projects.models import BugReproduction, Issue, Milestone, Project, Version


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
    mutation CreateIssue ($input: IssueInputWithMilestones!) {
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

    typename, _pk = from_base64(res.data["createMilestone"].pop("id"))
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
def test_input_create_mutation_multiple_level_nested_m2m_creation(
    db, gql_client: GraphQLTestClient
):
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
          milestones {
            id
            name
            issues {
              id
              name
                bugReproduction {
                  id
                  description
                }
            }
          }
        }
      }
    }
    """

    project = ProjectFactory.create(name="Some Project")

    res = gql_client.query(
        query,
        {
            "input": {
                "id": to_base64("ProjectType", project.pk),
                "milestones": [
                    {
                        "name": "Some Milestone",
                        "issues": [
                            {
                                "name": "Some Issue",
                                "bugReproduction": {
                                    "description": "Steps to reproduce"
                                },
                            }
                        ],
                    }
                ],
            },
        },
    )

    assert res.data
    assert isinstance(res.data["updateProject"], dict)

    project_typename, project_pk = from_base64(res.data["updateProject"].pop("id"))
    assert project_typename == "ProjectType"
    assert project.pk == int(project_pk)

    milestones = Milestone.objects.all()
    assert len(milestones) == 1
    assert len(res.data["updateProject"]["milestones"]) == 1

    fetched_milestone = res.data["updateProject"]["milestones"][0]
    milestone_typename, milestone_pk = from_base64(fetched_milestone.pop("id"))
    assert milestone_typename == "MilestoneType"
    assert milestones[0] == Milestone.objects.get(pk=milestone_pk)

    issues = Issue.objects.all()
    assert len(issues) == 1
    assert len(fetched_milestone["issues"]) == 1

    fetched_issue = fetched_milestone["issues"][0]
    issue_typename, issue_pk = from_base64(fetched_issue.pop("id"))
    assert issue_typename == "IssueType"
    assert issues[0] == Issue.objects.get(pk=issue_pk)

    bug_reproductions = BugReproduction.objects.all()
    assert len(bug_reproductions) == 1
    bug_reproduction_typename, bug_reproduction_pk = from_base64(
        fetched_issue["bugReproduction"].pop("id")
    )
    assert bug_reproduction_typename == "BugReproductionType"
    assert bug_reproductions[0] == BugReproduction.objects.get(pk=bug_reproduction_pk)

    assert res.data == {
        "updateProject": {
            "__typename": "ProjectType",
            "name": "Some Project",
            "milestones": [
                {
                    "name": "Some Milestone",
                    "issues": [
                        {
                            "name": "Some Issue",
                            "bugReproduction": {"description": "Steps to reproduce"},
                        }
                    ],
                }
            ],
        },
    }


@pytest.mark.django_db(transaction=True)
def test_input_create_mutation_multiple_level_nested_list_input_creation(
    db, gql_client: GraphQLTestClient
):
    query = """
    mutation UpdateProjectWithMilestoneList ($input: ProjectWithMilestoneListInputPartial!) {
      updateProjectWithMilestoneList (input: $input) {
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
          milestones {
            id
            name
            issues {
              id
              name
              bugReproduction {
                id
                description
              }
            }
          }
        }
      }
    }
    """

    milestone = MilestoneFactory.create(name="Milestone 1")
    project = milestone.project

    res = gql_client.query(
        query,
        {
            "input": {
                "id": to_base64("ProjectType", project.pk),
                "milestones": {
                    "add": [
                        {
                            "id": None,
                            "name": "Extra Milestone",
                            "issues": [
                                {
                                    "name": "Some Issue",
                                    "bugReproduction": {"description": "Test"},
                                }
                            ],
                        }
                    ]
                },
            },
        },
    )

    assert res.data
    assert isinstance(res.data["updateProjectWithMilestoneList"], dict)

    project_typename, _ = from_base64(
        res.data["updateProjectWithMilestoneList"].pop("id")
    )
    assert project_typename == "ProjectType"

    milestones = Milestone.objects.all()
    assert len(milestones) == 2

    fetched_milestones = res.data["updateProjectWithMilestoneList"]["milestones"]
    assert len(fetched_milestones) == 2

    milestone_typename, milestone_pk = from_base64(fetched_milestones[1].pop("id"))
    assert milestone_typename == "MilestoneType"
    created_milestone = Milestone.objects.exclude(pk=milestone.pk).get()
    assert created_milestone.pk == int(milestone_pk)
    assert created_milestone.name == fetched_milestones[1]["name"]


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("unset_pk", [True, False])
def test_input_create_mutation_multiple_level_nested_creation(
    db, gql_client: GraphQLTestClient, unset_pk: bool
):
    query = """
    mutation CreateIssue ($input: IssueInputWithMilestones!) {
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
            project {
              id
              name
            }
          }
        }
      }
    }
    """
    res = gql_client.query(
        query,
        {
            "input": {
                "name": "Some Issue",
                "milestone": {
                    "name": "Some Milestone",
                    "project": {
                        **({} if unset_pk else {"id": None}),
                        "name": "Some Project",
                    },
                },
            },
        },
    )
    assert res.data
    assert isinstance(res.data["createIssue"], dict)

    issue_typename, issue_pk = from_base64(res.data["createIssue"].pop("id"))
    assert issue_typename == "IssueType"
    issue = Issue.objects.get(pk=issue_pk)

    milestone_typename, milestone_pk = from_base64(
        res.data["createIssue"]["milestone"].pop("id")
    )
    assert milestone_typename == "MilestoneType"
    milestone = Milestone.objects.get(pk=milestone_pk)
    assert issue.milestone == milestone

    project_typename, project_pk = from_base64(
        res.data["createIssue"]["milestone"]["project"].pop("id")
    )
    assert project_typename == "ProjectType"
    project = Project.objects.get(pk=project_pk)
    assert issue.milestone.project == project

    assert res.data == {
        "createIssue": {
            "__typename": "IssueType",
            "name": issue.name,
            "milestone": {"name": milestone.name, "project": {"name": project.name}},
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
    mutation UpdateIssue ($input: IssueInputPartial!) {
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
def test_input_nested_unique_together_update_mutation(
    db, gql_client: GraphQLTestClient
):
    query = """
    mutation UpdateIssue ($input: IssueInputPartial!) {
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
          versions {
            name
          }
        }
      }
    }
    """
    issue = IssueFactory.create()
    assert not Version.objects.exists()

    # Execute two sequential queries with nested Version objects having `unique_together` contraint.
    # Only one instance of `Version` is expected to be created with no unique contrant failure
    for _ in range(2):
        res = gql_client.query(
            query,
            {
                "input": {
                    "id": to_base64("IssueType", issue.pk),
                    "versions": {"set": [{"name": "beta"}, {"name": "beta"}]},
                },
            },
        )
        assert res.data
        assert isinstance(res.data["updateIssue"], dict)

    versions = Version.objects.all()
    assert len(versions) == 1
    assert len(res.data["updateIssue"]["versions"]) == 1
    assert res.data["updateIssue"]["versions"][0]["name"] == versions[0].name


@pytest.mark.django_db(transaction=True)
def test_input_nested_update_mutation(db, gql_client: GraphQLTestClient):
    query = """
    mutation UpdateIssue ($input: IssueInputPartial!) {
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
    mutation UpdateIssue ($input: IssueInputPartial!) {
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
    mutation UpdateIssue ($input: IssueInputPartial!) {
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
                "pk": None,
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
        {"input": {"pk": None, "title": "ABC", "fullCleanOptions": True}},
    )
    expected = {"createQuiz": {"__typename": "QuizType", "sequence": 2, "title": "ABC"}}
    assert res.data == expected

    res = gql_client.query(
        query,
        {"input": {"pk": None, "title": "ABC", "fullCleanOptions": True}},
    )
    expected = {"createQuiz": {"__typename": "QuizType", "sequence": 3, "title": "ABC"}}
    assert res.data == expected

    res = gql_client.query(
        query,
        {"input": {"pk": None, "title": "ABC", "fullCleanOptions": True}},
    )
    expected = {"createQuiz": {"__typename": "QuizType", "sequence": 4, "title": "ABC"}}
    assert res.data == expected
