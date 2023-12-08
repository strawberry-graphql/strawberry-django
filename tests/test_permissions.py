from typing import List

import pytest
from django.contrib.auth.models import Permission
from guardian.shortcuts import assign_perm
from strawberry.relay import to_base64
from typing_extensions import Literal, TypeAlias

from .projects.faker import (
    GroupFactory,
    IssueFactory,
    StaffUserFactory,
    SuperuserUserFactory,
    UserFactory,
)
from .utils import GraphQLTestClient

PermKind: TypeAlias = Literal["user", "group", "superuser"]
perm_kinds: List[PermKind] = ["user", "group", "superuser"]


@pytest.mark.django_db(transaction=True)
def test_is_authenticated(db, gql_client: GraphQLTestClient):
    query = """
    query Issue ($id: GlobalID!) {
        issueLoginRequired (id: $id) {
          id
          name
        }
      }
    """
    issue = IssueFactory.create()

    res = gql_client.query(
        query,
        {"id": to_base64("IssueType", issue.pk)},
        asserts_errors=False,
    )
    assert res.data is None
    assert res.errors == [
        {
            "message": "User is not authenticated.",
            "locations": [{"line": 3, "column": 9}],
            "path": ["issueLoginRequired"],
        },
    ]

    user = UserFactory.create()
    with gql_client.login(user):
        res = gql_client.query(query, {"id": to_base64("IssueType", issue.pk)})
        assert res.data == {
            "issueLoginRequired": {
                "id": to_base64("IssueType", issue.pk),
                "name": issue.name,
            },
        }


@pytest.mark.django_db(transaction=True)
def test_is_authenticated_optional(db, gql_client: GraphQLTestClient):
    query = """
    query Issue ($id: GlobalID!) {
        issueLoginRequiredOptional (id: $id) {
          id
          name
        }
      }
    """
    issue = IssueFactory.create()

    res = gql_client.query(query, {"id": to_base64("IssueType", issue.pk)})
    assert res.data == {"issueLoginRequiredOptional": None}

    user = UserFactory.create()
    with gql_client.login(user):
        res = gql_client.query(query, {"id": to_base64("IssueType", issue.pk)})
        assert res.data == {
            "issueLoginRequiredOptional": {
                "id": to_base64("IssueType", issue.pk),
                "name": issue.name,
            },
        }


@pytest.mark.django_db(transaction=True)
def test_staff_required(db, gql_client: GraphQLTestClient):
    query = """
    query Issue ($id: GlobalID!) {
        issueStaffRequired (id: $id) {
          id
          name
        }
      }
    """
    issue = IssueFactory.create()

    res = gql_client.query(
        query,
        {"id": to_base64("IssueType", issue.pk)},
        asserts_errors=False,
    )
    assert res.data is None
    assert res.errors == [
        {
            "message": "User is not a staff member.",
            "locations": [{"line": 3, "column": 9}],
            "path": ["issueStaffRequired"],
        },
    ]

    user = UserFactory.create()
    with gql_client.login(user):
        assert res.data is None
        assert res.errors == [
            {
                "message": "User is not a staff member.",
                "locations": [{"line": 3, "column": 9}],
                "path": ["issueStaffRequired"],
            },
        ]

    staff = StaffUserFactory.create()
    with gql_client.login(staff):
        res = gql_client.query(query, {"id": to_base64("IssueType", issue.pk)})
        assert res.data == {
            "issueStaffRequired": {
                "id": to_base64("IssueType", issue.pk),
                "name": issue.name,
            },
        }


@pytest.mark.django_db(transaction=True)
def test_staff_required_optional(db, gql_client: GraphQLTestClient):
    query = """
    query Issue ($id: GlobalID!) {
        issueStaffRequiredOptional (id: $id) {
          id
          name
        }
      }
    """
    issue = IssueFactory.create()

    res = gql_client.query(query, {"id": to_base64("IssueType", issue.pk)})
    assert res.data == {"issueStaffRequiredOptional": None}

    user = UserFactory.create()
    with gql_client.login(user):
        res = gql_client.query(query, {"id": to_base64("IssueType", issue.pk)})
        assert res.data == {"issueStaffRequiredOptional": None}

    staff = StaffUserFactory.create()
    with gql_client.login(staff):
        res = gql_client.query(query, {"id": to_base64("IssueType", issue.pk)})
        assert res.data == {
            "issueStaffRequiredOptional": {
                "id": to_base64("IssueType", issue.pk),
                "name": issue.name,
            },
        }


@pytest.mark.django_db(transaction=True)
def test_superuser_required(db, gql_client: GraphQLTestClient):
    query = """
    query Issue ($id: GlobalID!) {
        issueSuperuserRequired (id: $id) {
          id
          name
        }
      }
    """
    issue = IssueFactory.create()

    res = gql_client.query(
        query,
        {"id": to_base64("IssueType", issue.pk)},
        asserts_errors=False,
    )
    assert res.data is None
    assert res.errors == [
        {
            "message": "User is not a superuser.",
            "locations": [{"line": 3, "column": 9}],
            "path": ["issueSuperuserRequired"],
        },
    ]

    user = UserFactory.create()
    with gql_client.login(user):
        res = gql_client.query(
            query,
            {"id": to_base64("IssueType", issue.pk)},
            asserts_errors=False,
        )
        assert res.data is None
        assert res.errors == [
            {
                "message": "User is not a superuser.",
                "locations": [{"line": 3, "column": 9}],
                "path": ["issueSuperuserRequired"],
            },
        ]

    superuser = SuperuserUserFactory.create()
    with gql_client.login(superuser):
        res = gql_client.query(query, {"id": to_base64("IssueType", issue.pk)})
        assert res.data == {
            "issueSuperuserRequired": {
                "id": to_base64("IssueType", issue.pk),
                "name": issue.name,
            },
        }


@pytest.mark.django_db(transaction=True)
def test_async_user_resolve(db, gql_client: GraphQLTestClient):
    query = """
    query asyncUserResolve {
        asyncUserResolve
      }
    """
    if not gql_client.is_async:
        return
    user = UserFactory.create()
    with gql_client.login(user):
        res = gql_client.query(
            query,
            asserts_errors=False,
        )
        assert res.data is None
        assert res.errors == [
            {
                "message": "You don't have permission to access this app.",
                "locations": [{"line": 3, "column": 9}],
                "path": ["asyncUserResolve"],
            },
        ]

    superuser = SuperuserUserFactory.create()
    with gql_client.login(superuser):
        res = gql_client.query(query)
        assert res.data == {"asyncUserResolve": True}
    user_with_perm = UserFactory.create()
    user_with_perm.user_permissions.add(
        Permission.objects.get(codename="view_issue"),
    )
    with gql_client.login(user_with_perm):
        res = gql_client.query(query)
        assert res.data == {"asyncUserResolve": True}


@pytest.mark.django_db(transaction=True)
def test_superuser_required_optional(db, gql_client: GraphQLTestClient):
    query = """
    query Issue ($id: GlobalID!) {
        issueSuperuserRequiredOptional (id: $id) {
          id
          name
        }
      }
    """
    issue = IssueFactory.create()

    res = gql_client.query(query, {"id": to_base64("IssueType", issue.pk)})
    assert res.data == {"issueSuperuserRequiredOptional": None}

    user = UserFactory.create()
    with gql_client.login(user):
        res = gql_client.query(query, {"id": to_base64("IssueType", issue.pk)})
        assert res.data == {"issueSuperuserRequiredOptional": None}

    superuser = SuperuserUserFactory.create()
    with gql_client.login(superuser):
        res = gql_client.query(query, {"id": to_base64("IssueType", issue.pk)})
        assert res.data == {
            "issueSuperuserRequiredOptional": {
                "id": to_base64("IssueType", issue.pk),
                "name": issue.name,
            },
        }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("kind", perm_kinds)
def test_perm_required(db, gql_client: GraphQLTestClient, kind: PermKind):
    query = """
    query Issue ($id: GlobalID!) {
        issuePermRequired (id: $id) {
          id
          name
        }
      }
    """
    issue = IssueFactory.create()

    res = gql_client.query(
        query,
        {"id": to_base64("IssueType", issue.pk)},
        asserts_errors=False,
    )
    assert res.data is None
    assert res.errors == [
        {
            "message": "You don't have permission to access this app.",
            "locations": [{"line": 3, "column": 9}],
            "path": ["issuePermRequired"],
        },
    ]

    user = UserFactory.create()
    with gql_client.login(user):
        res = gql_client.query(
            query,
            {"id": to_base64("IssueType", issue.pk)},
            asserts_errors=False,
        )
        assert res.data is None
        assert res.errors == [
            {
                "message": "You don't have permission to access this app.",
                "locations": [{"line": 3, "column": 9}],
                "path": ["issuePermRequired"],
            },
        ]

    if kind == "user":
        user_with_perm = UserFactory.create()
        user_with_perm.user_permissions.add(
            Permission.objects.get(codename="view_issue"),
        )
    elif kind == "group":
        user_with_perm = UserFactory.create()
        group = GroupFactory.create()
        group.permissions.add(Permission.objects.get(codename="view_issue"))
        user_with_perm.groups.add(group)
    elif kind == "superuser":
        user_with_perm = SuperuserUserFactory.create()
    else:  # pragma:nocover
        raise AssertionError

    with gql_client.login(user_with_perm):
        res = gql_client.query(query, {"id": to_base64("IssueType", issue.pk)})
        assert res.data == {
            "issuePermRequired": {
                "id": to_base64("IssueType", issue.pk),
                "name": issue.name,
            },
        }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("kind", perm_kinds)
def test_perm_required_optional(db, gql_client: GraphQLTestClient, kind: PermKind):
    query = """
    query Issue ($id: GlobalID!) {
        issuePermRequiredOptional (id: $id) {
          id
          name
        }
      }
    """
    issue = IssueFactory.create()

    res = gql_client.query(query, {"id": to_base64("IssueType", issue.pk)})
    assert res.data == {"issuePermRequiredOptional": None}

    user = UserFactory.create()
    with gql_client.login(user):
        res = gql_client.query(query, {"id": to_base64("IssueType", issue.pk)})
        assert res.data == {"issuePermRequiredOptional": None}

    if kind == "user":
        user_with_perm = UserFactory.create()
        user_with_perm.user_permissions.add(
            Permission.objects.get(codename="view_issue"),
        )
    elif kind == "group":
        user_with_perm = UserFactory.create()
        group = GroupFactory.create()
        group.permissions.add(Permission.objects.get(codename="view_issue"))
        user_with_perm.groups.add(group)
    elif kind == "superuser":
        user_with_perm = SuperuserUserFactory.create()
    else:  # pragma:nocover
        raise AssertionError

    with gql_client.login(user_with_perm):
        res = gql_client.query(query, {"id": to_base64("IssueType", issue.pk)})
        assert res.data == {
            "issuePermRequiredOptional": {
                "id": to_base64("IssueType", issue.pk),
                "name": issue.name,
            },
        }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("kind", perm_kinds)
def test_list_perm_required(db, gql_client: GraphQLTestClient, kind: PermKind):
    query = """
    query Issue {
        issueListPermRequired {
          id
          name
        }
      }
    """
    issue = IssueFactory.create()

    res = gql_client.query(query)
    assert res.data == {"issueListPermRequired": []}

    user = UserFactory.create()
    with gql_client.login(user):
        res = gql_client.query(query)
        assert res.data == {"issueListPermRequired": []}

    if kind == "user":
        user_with_perm = UserFactory.create()
        user_with_perm.user_permissions.add(
            Permission.objects.get(codename="view_issue"),
        )
    elif kind == "group":
        user_with_perm = UserFactory.create()
        group = GroupFactory.create()
        group.permissions.add(Permission.objects.get(codename="view_issue"))
        user_with_perm.groups.add(group)
    elif kind == "superuser":
        user_with_perm = SuperuserUserFactory.create()
    else:  # pragma:nocover
        raise AssertionError

    with gql_client.login(user_with_perm):
        res = gql_client.query(query)
        assert res.data == {
            "issueListPermRequired": [
                {
                    "id": to_base64("IssueType", issue.pk),
                    "name": issue.name,
                },
            ],
        }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("kind", perm_kinds)
def test_conn_perm_required(db, gql_client: GraphQLTestClient, kind: PermKind):
    query = """
    query Issue {
        issueConnPermRequired {
          totalCount
          edges {
            node {
              id
              name
            }
          }
        }
      }
    """
    issue = IssueFactory.create()

    res = gql_client.query(query)
    assert res.data == {"issueConnPermRequired": {"edges": [], "totalCount": 0}}

    user = UserFactory.create()
    with gql_client.login(user):
        res = gql_client.query(query)
        assert res.data == {"issueConnPermRequired": {"edges": [], "totalCount": 0}}

    if kind == "user":
        user_with_perm = UserFactory.create()
        user_with_perm.user_permissions.add(
            Permission.objects.get(codename="view_issue"),
        )
    elif kind == "group":
        user_with_perm = UserFactory.create()
        group = GroupFactory.create()
        group.permissions.add(Permission.objects.get(codename="view_issue"))
        user_with_perm.groups.add(group)
    elif kind == "superuser":
        user_with_perm = SuperuserUserFactory.create()
    else:  # pragma:nocover
        raise AssertionError

    with gql_client.login(user_with_perm):
        res = gql_client.query(query)
        assert res.data == {
            "issueConnPermRequired": {
                "edges": [
                    {
                        "node": {
                            "id": to_base64("IssueType", issue.pk),
                            "name": issue.name,
                        },
                    },
                ],
                "totalCount": 1,
            },
        }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("kind", perm_kinds)
def test_obj_perm_required(db, gql_client: GraphQLTestClient, kind: PermKind):
    query = """
    query Issue ($id: GlobalID!) {
        issueObjPermRequired (id: $id) {
          id
          name
        }
      }
    """
    issue_no_perm = IssueFactory.create()
    issue_with_perm = IssueFactory.create()

    user = UserFactory.create()

    if kind == "user":
        user_with_perm = UserFactory.create()
        assign_perm("view_issue", user_with_perm, issue_with_perm)
    elif kind == "group":
        user_with_perm = UserFactory.create()
        group = GroupFactory.create()
        assign_perm("view_issue", group, issue_with_perm)
        user_with_perm.groups.add(group)
    elif kind == "superuser":
        user_with_perm = SuperuserUserFactory.create()
    else:  # pragma:nocover
        raise AssertionError

    for issue in [issue_no_perm, issue_with_perm]:
        res = gql_client.query(
            query,
            {"id": to_base64("IssueType", issue.pk)},
            asserts_errors=False,
        )
        assert res.data is None
        assert res.errors == [
            {
                "message": "You don't have permission to access this app.",
                "locations": [{"line": 3, "column": 9}],
                "path": ["issueObjPermRequired"],
            },
        ]

    for u in [user, user_with_perm]:
        # Superusers will have access to everything...
        if kind == "superuser":
            continue

        with gql_client.login(u):
            res = gql_client.query(
                query,
                {"id": to_base64("IssueType", issue_no_perm.pk)},
                asserts_errors=False,
            )
            assert res.data is None
            assert res.errors == [
                {
                    "message": "You don't have permission to access this app.",
                    "locations": [{"line": 3, "column": 9}],
                    "path": ["issueObjPermRequired"],
                },
            ]

    with gql_client.login(user_with_perm):
        res = gql_client.query(
            query,
            {"id": to_base64("IssueType", issue_with_perm.pk)},
        )
        assert res.data == {
            "issueObjPermRequired": {
                "id": to_base64("IssueType", issue_with_perm.pk),
                "name": issue_with_perm.name,
            },
        }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("kind", perm_kinds)
def test_obj_perm_required_global(db, gql_client: GraphQLTestClient, kind: PermKind):
    query = """
    query Issue ($id: GlobalID!) {
        issueObjPermRequired (id: $id) {
          id
          name
        }
      }
    """
    issue_no_perm = IssueFactory.create()
    issue_with_perm = IssueFactory.create()

    user = UserFactory.create()

    if kind == "user":
        user_with_perm = UserFactory.create()
        user_with_perm.user_permissions.add(
            Permission.objects.get(codename="view_issue"),
        )
    elif kind == "group":
        user_with_perm = UserFactory.create()
        group = GroupFactory.create()
        group.permissions.add(Permission.objects.get(codename="view_issue"))
        user_with_perm.groups.add(group)
    elif kind == "superuser":
        user_with_perm = SuperuserUserFactory.create()
    else:  # pragma:nocover
        raise AssertionError

    for issue in [issue_no_perm, issue_with_perm]:
        res = gql_client.query(
            query,
            {"id": to_base64("IssueType", issue.pk)},
            asserts_errors=False,
        )
        assert res.data is None
        assert res.errors == [
            {
                "message": "You don't have permission to access this app.",
                "locations": [{"line": 3, "column": 9}],
                "path": ["issueObjPermRequired"],
            },
        ]

        with gql_client.login(user):
            res = gql_client.query(
                query,
                {"id": to_base64("IssueType", issue.pk)},
                asserts_errors=False,
            )
            assert res.data is None
            assert res.errors == [
                {
                    "message": "You don't have permission to access this app.",
                    "locations": [{"line": 3, "column": 9}],
                    "path": ["issueObjPermRequired"],
                },
            ]

        with gql_client.login(user_with_perm):
            res = gql_client.query(
                query,
                {"id": to_base64("IssueType", issue_with_perm.pk)},
            )
            assert res.data == {
                "issueObjPermRequired": {
                    "id": to_base64("IssueType", issue_with_perm.pk),
                    "name": issue_with_perm.name,
                },
            }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("kind", perm_kinds)
def test_obj_perm_required_optional(db, gql_client: GraphQLTestClient, kind: PermKind):
    query = """
    query Issue ($id: GlobalID!) {
        issueObjPermRequiredOptional (id: $id) {
          id
          name
        }
      }
    """
    issue_no_perm = IssueFactory.create()
    issue_with_perm = IssueFactory.create()

    user = UserFactory.create()

    if kind == "user":
        user_with_perm = UserFactory.create()
        assign_perm("view_issue", user_with_perm, issue_with_perm)
    elif kind == "group":
        user_with_perm = UserFactory.create()
        group = GroupFactory.create()
        assign_perm("view_issue", group, issue_with_perm)
        user_with_perm.groups.add(group)
    elif kind == "superuser":
        user_with_perm = SuperuserUserFactory.create()
    else:  # pragma:nocover
        raise AssertionError

    for issue in [issue_no_perm, issue_with_perm]:
        res = gql_client.query(
            query,
            {"id": to_base64("IssueType", issue.pk)},
        )
        assert res.data == {"issueObjPermRequiredOptional": None}

    for u in [user, user_with_perm]:
        # Superusers will have access to everything...
        if kind == "superuser":
            continue

        with gql_client.login(u):
            res = gql_client.query(
                query,
                {"id": to_base64("IssueType", issue_no_perm.pk)},
            )
            assert res.data == {"issueObjPermRequiredOptional": None}

    with gql_client.login(user_with_perm):
        res = gql_client.query(
            query,
            {"id": to_base64("IssueType", issue_with_perm.pk)},
        )
        assert res.data == {
            "issueObjPermRequiredOptional": {
                "id": to_base64("IssueType", issue_with_perm.pk),
                "name": issue_with_perm.name,
            },
        }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("kind", perm_kinds)
def test_list_obj_perm_required(db, gql_client: GraphQLTestClient, kind: PermKind):
    query = """
    query Issue {
        issueListObjPermRequired {
          id
          name
        }
      }
    """
    IssueFactory.create()
    issue_with_perm = IssueFactory.create()

    user = UserFactory.create()

    if kind == "user":
        user_with_perm = UserFactory.create()
        assign_perm("view_issue", user_with_perm, issue_with_perm)
    elif kind == "group":
        user_with_perm = UserFactory.create()
        group = GroupFactory.create()
        assign_perm("view_issue", group, issue_with_perm)
        user_with_perm.groups.add(group)
    elif kind == "superuser":
        user_with_perm = SuperuserUserFactory.create()
    else:  # pragma:nocover
        raise AssertionError

    res = gql_client.query(query)
    assert res.data == {"issueListObjPermRequired": []}

    with gql_client.login(user):
        res = gql_client.query(query)
        assert res.data == {"issueListObjPermRequired": []}

    if kind == "superuser":
        # Even though the user is a superuser, he doesn't have the permission
        # assigned directly to him for the listing.
        with gql_client.login(user_with_perm):
            res = gql_client.query(query)
            assert res.data == {"issueListObjPermRequired": []}
    else:
        with gql_client.login(user_with_perm):
            res = gql_client.query(query)
            assert res.data == {
                "issueListObjPermRequired": [
                    {
                        "id": to_base64("IssueType", issue_with_perm.pk),
                        "name": issue_with_perm.name,
                    },
                ],
            }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("kind", perm_kinds)
def test_conn_obj_perm_required(db, gql_client: GraphQLTestClient, kind: PermKind):
    query = """
    query Issue {
        issueConnObjPermRequired {
          totalCount
          edges {
            node {
              id
              name
            }
          }
        }
      }
    """
    IssueFactory.create()
    issue_with_perm = IssueFactory.create()

    user = UserFactory.create()

    if kind == "user":
        user_with_perm = UserFactory.create()
        assign_perm("view_issue", user_with_perm, issue_with_perm)
    elif kind == "group":
        user_with_perm = UserFactory.create()
        group = GroupFactory.create()
        assign_perm("view_issue", group, issue_with_perm)
        user_with_perm.groups.add(group)
    elif kind == "superuser":
        user_with_perm = SuperuserUserFactory.create()
    else:  # pragma:nocover
        raise AssertionError

    res = gql_client.query(query)
    assert res.data == {"issueConnObjPermRequired": {"edges": [], "totalCount": 0}}

    with gql_client.login(user):
        res = gql_client.query(query)
        assert res.data == {"issueConnObjPermRequired": {"edges": [], "totalCount": 0}}

    if kind == "superuser":
        # Even though the user is a superuser, he doesn't have the permission
        # assigned directly to him for the listing.
        with gql_client.login(user_with_perm):
            res = gql_client.query(query)
            assert res.data == {
                "issueConnObjPermRequired": {"edges": [], "totalCount": 0},
            }
    else:
        with gql_client.login(user_with_perm):
            res = gql_client.query(query)
            assert res.data == {
                "issueConnObjPermRequired": {
                    "edges": [
                        {
                            "node": {
                                "id": to_base64("IssueType", issue_with_perm.pk),
                                "name": issue_with_perm.name,
                            },
                        },
                    ],
                    "totalCount": 1,
                },
            }
