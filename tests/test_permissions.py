import sys
from typing import Literal, TypeAlias

import pytest
from django.contrib.auth.models import Permission
from guardian.shortcuts import assign_perm
from strawberry.relay import to_base64

from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.permissions import (
    HasPerm,
    HasRetvalPerm,
    HasSourcePerm,
    PermTarget,
)
from strawberry_django.utils.query import filter_for_user

from .projects.faker import (
    GroupFactory,
    IssueFactory,
    MilestoneFactory,
    StaffUserFactory,
    SuperuserUserFactory,
    UserFactory,
)
from .projects.models import Issue
from .utils import GraphQLTestClient, assert_num_queries

PermKind: TypeAlias = Literal["user", "group", "superuser"]
perm_kinds: list[PermKind] = ["user", "group", "superuser"]


@pytest.mark.django_db(transaction=True)
def test_is_authenticated(db, gql_client: GraphQLTestClient):
    query = """
    query Issue ($id: ID!) {
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
        assert_no_errors=False,
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
    query Issue ($id: ID!) {
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
    query Issue ($id: ID!) {
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
        assert_no_errors=False,
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
    query Issue ($id: ID!) {
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
    query Issue ($id: ID!) {
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
        assert_no_errors=False,
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
            assert_no_errors=False,
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
        pytest.skip("needs async client")
    user = UserFactory.create()
    with gql_client.login(user):
        res = gql_client.query(
            query,
            assert_no_errors=False,
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
    query Issue ($id: ID!) {
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
def test_perm_cached(db, gql_client: GraphQLTestClient):
    """Validates that the permission caching mechanism correctly stores permissions as a set of strings.

    The test targets the `_perm_cache` attribute used in `utils/query.py`. It verifies that
    the attribute behaves as expected, holding a `Set[str]` that represents permission
    codenames, rather than direct Permission objects.

    This test addresses a regression captured by the following error:

    ```
    user_perms: Set[str] = {p.codename for p in perm_cache}
                          ^^^^^^^^^^
    AttributeError: 'str' object has no attribute 'codename'
    ```
    """
    query = """
    query Issue ($id: ID!) {
        issuePermRequired (id: $id) {
          id
          privateName
        }
    }
    """
    issue = IssueFactory.create(name="Test")

    # User with permission
    user_with_perm = UserFactory.create()
    user_with_perm.user_permissions.add(
        Permission.objects.get(codename="view_issue"),
    )
    assign_perm("view_issue", user_with_perm, issue)
    with gql_client.login(user_with_perm):
        if DjangoOptimizerExtension.enabled.get():
            res = gql_client.query(query, {"id": to_base64("IssueType", issue.pk)})
            assert res.data == {
                "issuePermRequired": {
                    "id": to_base64("IssueType", issue.pk),
                    "privateName": issue.name,
                },
            }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("kind", perm_kinds)
def test_perm_required(db, gql_client: GraphQLTestClient, kind: PermKind):
    query = """
    query Issue ($id: ID!) {
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
        assert_no_errors=False,
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
            assert_no_errors=False,
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
    query Issue ($id: ID!) {
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
    query Issue ($id: ID!) {
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
            assert_no_errors=False,
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
                assert_no_errors=False,
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
    query Issue ($id: ID!) {
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
            assert_no_errors=False,
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
                assert_no_errors=False,
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
    query Issue ($id: ID!) {
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
def test_list_obj_perm_required_paginated(
    db, gql_client: GraphQLTestClient, kind: PermKind
):
    query = """
    query Issue {
        issueListObjPermRequiredPaginated(pagination: {limit: 10, offset: 0}) {
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
    assert res.data == {"issueListObjPermRequiredPaginated": []}

    with gql_client.login(user):
        res = gql_client.query(query)
        assert res.data == {"issueListObjPermRequiredPaginated": []}

    if kind == "superuser":
        # Even though the user is a superuser, he doesn't have the permission
        # assigned directly to him for the listing.
        with gql_client.login(user_with_perm):
            res = gql_client.query(query)
            assert res.data == {"issueListObjPermRequiredPaginated": []}
    else:
        with gql_client.login(user_with_perm):
            res = gql_client.query(query)
            assert res.data == {
                "issueListObjPermRequiredPaginated": [
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


def _assign_global_perm(kind: PermKind, user):
    perm = Permission.objects.get(codename="view_issue")
    if kind == "user":
        user.user_permissions.add(perm)
    elif kind == "group":
        group = GroupFactory.create()
        group.permissions.add(perm)
        user.groups.add(group)
    else:  # pragma:nocover
        raise AssertionError


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("kind", ["user", "group"])
def test_obj_perm_required_no_global(db, gql_client: GraphQLTestClient, kind: PermKind):
    query = """
    query Issue ($id: ID!) {
        withGlobal: issueObjPermRequiredOptional (id: $id) {
          id
        }
        withoutGlobal: issueObjPermRequiredNoGlobalOptional (id: $id) {
          id
        }
      }
    """
    issue_no_perm = IssueFactory.create()
    issue_with_perm = IssueFactory.create()

    user = UserFactory.create()
    _assign_global_perm(kind, user)

    # The global permission is enough when it is accepted, but not otherwise
    with gql_client.login(user):
        for issue in [issue_no_perm, issue_with_perm]:
            issue_id = to_base64("IssueType", issue.pk)
            res = gql_client.query(query, {"id": issue_id})
            assert res.data == {
                "withGlobal": {"id": issue_id},
                "withoutGlobal": None,
            }

    if kind == "user":
        assign_perm("view_issue", user, issue_with_perm)
    else:
        assign_perm("view_issue", user.groups.get(), issue_with_perm)

    with gql_client.login(user):
        issue_id = to_base64("IssueType", issue_no_perm.pk)
        res = gql_client.query(query, {"id": issue_id})
        assert res.data == {
            "withGlobal": {"id": issue_id},
            "withoutGlobal": None,
        }

        issue_id = to_base64("IssueType", issue_with_perm.pk)
        res = gql_client.query(query, {"id": issue_id})
        assert res.data == {
            "withGlobal": {"id": issue_id},
            "withoutGlobal": {"id": issue_id},
        }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("kind", ["user", "group"])
def test_list_obj_perm_required_no_global(
    db, gql_client: GraphQLTestClient, kind: PermKind
):
    query = """
    query Issue {
        withGlobal: issueListObjPermRequired {
          id
        }
        withoutGlobal: issueListObjPermRequiredNoGlobal {
          id
        }
      }
    """
    issue_no_perm = IssueFactory.create()
    issue_with_perm = IssueFactory.create()

    user = UserFactory.create()
    _assign_global_perm(kind, user)

    res = gql_client.query(query)
    assert res.data == {"withGlobal": [], "withoutGlobal": []}

    # The global permission is enough when it is accepted, but not otherwise
    with gql_client.login(user):
        res = gql_client.query(query)
        assert res.data == {
            "withGlobal": [
                {"id": to_base64("IssueType", issue_no_perm.pk)},
                {"id": to_base64("IssueType", issue_with_perm.pk)},
            ],
            "withoutGlobal": [],
        }

    if kind == "user":
        assign_perm("view_issue", user, issue_with_perm)
    else:
        assign_perm("view_issue", user.groups.get(), issue_with_perm)

    with gql_client.login(user):
        res = gql_client.query(query)
        assert res.data == {
            "withGlobal": [
                {"id": to_base64("IssueType", issue_no_perm.pk)},
                {"id": to_base64("IssueType", issue_with_perm.pk)},
            ],
            "withoutGlobal": [
                {"id": to_base64("IssueType", issue_with_perm.pk)},
            ],
        }


@pytest.mark.django_db(transaction=True)
def test_filter_for_user_no_global_without_obj_perms_backend(
    db, monkeypatch: pytest.MonkeyPatch
):
    IssueFactory.create()
    user = UserFactory.create()
    user.user_permissions.add(Permission.objects.get(codename="view_issue"))

    # Make the guardian integration unavailable, leaving no backend to check
    # object permissions against
    monkeypatch.setitem(sys.modules, "strawberry_django.integrations.guardian", None)

    qs = Issue.objects.all()
    assert filter_for_user(qs, user, "projects.view_issue").count() == 1
    assert (
        filter_for_user(
            qs,
            user,
            "projects.view_issue",
            accept_global_perms=False,
        ).count()
        == 0
    )


def test_perm_no_global_requires_obj_perm_target():
    with pytest.raises(ValueError, match="accept_global_perms=False"):
        HasPerm("projects.view_issue", accept_global_perms=False)

    with pytest.raises(ValueError, match="accept_global_perms=False"):
        HasRetvalPerm(
            "projects.view_issue",
            target=PermTarget.GLOBAL,
            accept_global_perms=False,
        )

    assert not HasSourcePerm(
        "projects.view_issue", accept_global_perms=False
    ).accept_global_perms
    assert not HasRetvalPerm(
        "projects.view_issue", accept_global_perms=False
    ).accept_global_perms


@pytest.mark.django_db(transaction=True)
def test_query_paginated_with_permissions(db, gql_client: GraphQLTestClient):
    query = """
      query TestQuery ($pagination: OffsetPaginationInput) {
        issuesPaginatedPermRequired (pagination: $pagination) {
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

    # No user logged in
    with assert_num_queries(0):
        res = gql_client.query(query)

    assert res.data == {
        "issuesPaginatedPermRequired": {
            "totalCount": 0,
            "results": [],
        }
    }

    user = UserFactory.create()

    # User logged in without permissions
    with gql_client.login(user):
        with assert_num_queries(4):
            res = gql_client.query(query)

        assert res.data == {
            "issuesPaginatedPermRequired": {
                "totalCount": 0,
                "results": [],
            }
        }

    # User logged in with permissions
    user.user_permissions.add(Permission.objects.get(codename="view_issue"))
    with gql_client.login(user):
        with assert_num_queries(6 if DjangoOptimizerExtension.enabled.get() else 11):
            res = gql_client.query(query)

        assert res.data == {
            "issuesPaginatedPermRequired": {
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

        with assert_num_queries(6 if DjangoOptimizerExtension.enabled.get() else 8):
            res = gql_client.query(query, variables={"pagination": {"limit": 2}})

        assert res.data == {
            "issuesPaginatedPermRequired": {
                "totalCount": 5,
                "results": [
                    {"name": issue1.name, "milestone": {"name": milestone1.name}},
                    {"name": issue2.name, "milestone": {"name": milestone1.name}},
                ],
            }
        }


@pytest.mark.django_db(transaction=True)
def test_query_paginated_with_obj_permissions(db, gql_client: GraphQLTestClient):
    query = """
      query TestQuery ($pagination: OffsetPaginationInput) {
        issuesPaginatedObjPermRequired (pagination: $pagination) {
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

    IssueFactory.create(milestone=milestone1)
    issue2 = IssueFactory.create(milestone=milestone1)
    IssueFactory.create(milestone=milestone1)
    issue4 = IssueFactory.create(milestone=milestone2)
    IssueFactory.create(milestone=milestone2)

    # No user logged in
    with assert_num_queries(0):
        res = gql_client.query(query)

    assert res.data == {
        "issuesPaginatedObjPermRequired": {
            "totalCount": 0,
            "results": [],
        }
    }

    user = UserFactory.create()

    # User logged in without permissions
    with gql_client.login(user):
        with assert_num_queries(5):
            res = gql_client.query(query)

        assert res.data == {
            "issuesPaginatedObjPermRequired": {
                "totalCount": 0,
                "results": [],
            }
        }

    assign_perm("view_issue", user, issue2)
    assign_perm("view_issue", user, issue4)

    # User logged in with permissions
    with gql_client.login(user):
        with assert_num_queries(4 if DjangoOptimizerExtension.enabled.get() else 6):
            res = gql_client.query(query)

        assert res.data == {
            "issuesPaginatedObjPermRequired": {
                "totalCount": 2,
                "results": [
                    {"name": issue2.name, "milestone": {"name": milestone1.name}},
                    {"name": issue4.name, "milestone": {"name": milestone2.name}},
                ],
            }
        }

        with assert_num_queries(4 if DjangoOptimizerExtension.enabled.get() else 5):
            res = gql_client.query(query, variables={"pagination": {"limit": 1}})

        assert res.data == {
            "issuesPaginatedObjPermRequired": {
                "totalCount": 2,
                "results": [
                    {"name": issue2.name, "milestone": {"name": milestone1.name}},
                ],
            }
        }
