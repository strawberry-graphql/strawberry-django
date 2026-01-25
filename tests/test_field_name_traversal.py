"""Tests for field_name with double-underscore relationship traversal."""

import operator
from typing import TYPE_CHECKING, Any, cast

import pytest
from django.contrib.auth import get_user_model
from django.db.models.constants import LOOKUP_SEP
from strawberry.types import get_object_definition

from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.resolvers import _django_getattr  # noqa: PLC2701
from tests.projects.models import Role, UserAssignedRole
from tests.utils import assert_num_queries

if TYPE_CHECKING:
    from strawberry_django.fields.field import StrawberryDjangoField

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_field_name_traversal_basic(db):
    """Test basic relationship traversal with field_name."""
    from tests.projects.schema import UserType

    # Create test data
    user = User.objects.create(username="testuser", email="test@example.com")
    role = Role.objects.create(name="Admin", description="Administrator role")
    UserAssignedRole.objects.create(user=user, role=role)

    # Refresh from db to test actual field resolution
    user = User.objects.get(pk=user.pk)

    # Test that we can access the role directly via field_name="assigned_role__role"
    definition = get_object_definition(UserType, strict=True)
    role_field = next(f for f in definition.fields if f.python_name == "role")
    role_field = cast("StrawberryDjangoField", role_field)

    # Verify the field uses the correct django_name
    assert role_field.django_name == "assigned_role__role"

    # Test actual resolution - simulate what would happen in GraphQL query
    # The field should be able to traverse the relationship
    result = role_field.get_result(user, None, [], {})
    result = cast("Any", result)

    # Since we're not in an async context and the field doesn't have a custom resolver,
    # it should use the default getattr which now supports __ traversal
    assert result is not None
    assert result.name == "Admin"
    assert result.description == "Administrator role"


def test_field_name_traversal_to_scalar(db):
    """Test relationship traversal to a scalar field."""
    from tests.projects.schema import UserType

    # Create test data
    user = User.objects.create(username="testuser2", email="test2@example.com")
    role = Role.objects.create(name="Editor", description="Editor role")
    UserAssignedRole.objects.create(user=user, role=role)

    # Refresh from db
    user = User.objects.get(pk=user.pk)

    # Test role_name field which uses field_name="assigned_role__role__name"
    definition = get_object_definition(UserType, strict=True)
    role_name_field = next(f for f in definition.fields if f.python_name == "role_name")
    role_name_field = cast("StrawberryDjangoField", role_name_field)

    assert role_name_field.django_name == "assigned_role__role__name"

    # Test resolution
    result = role_name_field.get_result(user, None, [], {})
    assert result == "Editor"


def test_field_name_traversal_with_none_intermediate(db):
    """Test that None in intermediate relationships returns None."""
    from tests.projects.schema import UserType

    # Create user WITHOUT assigned role
    user = User.objects.create(username="testuser3", email="test3@example.com")

    # Refresh from db
    user = User.objects.get(pk=user.pk)

    # Test role field - should return None since assigned_role doesn't exist
    definition = get_object_definition(UserType, strict=True)
    role_field = next(f for f in definition.fields if f.python_name == "role")
    role_field = cast("StrawberryDjangoField", role_field)

    # When assigned_role is None, the traversal should return None
    result = role_field.get_result(user, None, [], {})
    assert result is None


def test_field_name_traversal_with_none_scalar(db):
    """Test that None in intermediate relationships returns None for scalar fields."""
    from tests.projects.schema import UserType

    # Create user WITHOUT assigned role
    user = User.objects.create(username="testuser4", email="test4@example.com")

    # Refresh from db
    user = User.objects.get(pk=user.pk)

    # Test role_name field - should return None since assigned_role doesn't exist
    definition = get_object_definition(UserType, strict=True)
    role_name_field = next(f for f in definition.fields if f.python_name == "role_name")
    role_name_field = cast("StrawberryDjangoField", role_name_field)

    result = role_name_field.get_result(user, None, [], {})
    assert result is None


def test_field_name_traversal_scalar_query_count(db, gql_client):
    """Ensure scalar traversal doesn't generate extra queries with optimizer."""
    if gql_client.is_async:
        pytest.skip("Query counting with async client can lock sqlite tables")

    user1 = User.objects.create(username="query_user1", email="q1@example.com")
    user2 = User.objects.create(username="query_user2", email="q2@example.com")

    role1 = Role.objects.create(name="Role1", description="Role1 description")
    role2 = Role.objects.create(name="Role2", description="Role2 description")

    UserAssignedRole.objects.create(user=user1, role=role1)
    UserAssignedRole.objects.create(user=user2, role=role2)

    query = """
        query GetUsers {
            userList {
                email
                roleName
            }
        }
    """

    expected_queries = 1 if DjangoOptimizerExtension.enabled.get() else 5
    with assert_num_queries(expected_queries):
        res = gql_client.query(query)

    assert res.errors is None

    expected_users = [
        {"email": "q1@example.com", "roleName": "Role1"},
        {"email": "q2@example.com", "roleName": "Role2"},
    ]
    actual_users = sorted(res.data["userList"], key=operator.itemgetter("email"))
    assert actual_users == sorted(expected_users, key=operator.itemgetter("email"))


def test_field_name_traversal_object_query_count(db, gql_client):
    """GraphQL integration test for object traversal via field_name."""
    if gql_client.is_async:
        pytest.skip("Query counting with async client can lock sqlite tables")

    user1 = User.objects.create(username="role_user1", email="r1@example.com")
    user2 = User.objects.create(username="role_user2", email="r2@example.com")

    role1 = Role.objects.create(name="RoleA", description="RoleA description")
    role2 = Role.objects.create(name="RoleB", description="RoleB description")

    UserAssignedRole.objects.create(user=user1, role=role1)
    UserAssignedRole.objects.create(user=user2, role=role2)

    query = """
        query GetUsersWithRoles {
            userList {
                email
                role {
                    name
                }
            }
        }
    """

    expected_queries = 1 if DjangoOptimizerExtension.enabled.get() else 5
    with assert_num_queries(expected_queries):
        res = gql_client.query(query)

    assert res.errors is None

    expected_users = [
        {"email": "r1@example.com", "role": {"name": "RoleA"}},
        {"email": "r2@example.com", "role": {"name": "RoleB"}},
    ]
    actual_users = sorted(res.data["userList"], key=operator.itemgetter("email"))
    assert actual_users == sorted(expected_users, key=operator.itemgetter("email"))


def test_django_getattr_traversal():
    """Unit test for _django_getattr with double-underscore notation."""

    # Create a mock object structure
    class MockRole:
        name = "TestRole"
        description = "Test description"

    class MockAssignedRole:
        role = MockRole()

    class MockUser:
        assigned_role = MockAssignedRole()

    user = MockUser()

    # Test single level
    result = _django_getattr(user, "assigned_role")
    assert result is user.assigned_role

    # Test double underscore traversal
    result = _django_getattr(user, "assigned_role__role")
    assert result is user.assigned_role.role

    # Test triple underscore traversal to scalar
    result = _django_getattr(user, "assigned_role__role__name")
    assert result == "TestRole"

    # Test traversal where intermediate attribute exists but a deeper attribute is missing
    class EmptyMockAssignedRole:
        pass

    class UserWithEmptyAssignedRole:
        assigned_role = EmptyMockAssignedRole()

    user_with_empty = UserWithEmptyAssignedRole()

    with pytest.raises(AttributeError):
        _django_getattr(user_with_empty, "assigned_role__nonexistent")

    assert (
        _django_getattr(user_with_empty, "assigned_role__nonexistent", "default")
        == "default"
    )


def test_django_getattr_traversal_model_branch(db):
    """Exercise models.Model traversal behavior for unset related fields."""
    user = User.objects.create(
        username="model_branch_user",
        email="model_branch@example.com",
    )

    assert _django_getattr(user, LOOKUP_SEP.join(["assigned_role", "role"])) is None

    with pytest.raises(AttributeError):
        _django_getattr(user, LOOKUP_SEP.join(["nonexistent", "name"]))


def test_django_getattr_traversal_with_none():
    """Test _django_getattr returns None when intermediate value is None."""

    class MockUser:
        assigned_role = None

    user = MockUser()

    # Test that traversal returns None when intermediate is None
    result = _django_getattr(user, "assigned_role__role")
    assert result is None

    # Test with deeper traversal
    result = _django_getattr(user, "assigned_role__role__name")
    assert result is None


def test_django_getattr_traversal_attribute_error():
    """Test _django_getattr raises AttributeError when attribute doesn't exist."""

    class MockUser:
        pass

    user = MockUser()

    # Should raise AttributeError for non-existent attribute
    with pytest.raises(AttributeError):
        _django_getattr(user, "nonexistent__field")

    with pytest.raises(AttributeError):
        _django_getattr(user, "__role")

    with pytest.raises(AttributeError):
        _django_getattr(user, "role__")

    with pytest.raises(AttributeError):
        _django_getattr(user, "assigned_role____name")


def test_django_getattr_traversal_with_default():
    """Test _django_getattr returns default for missing attributes."""

    class MockUser:
        assigned_role = None

    user = MockUser()

    # Test that None is returned when intermediate is None
    result = _django_getattr(user, "assigned_role__role", "default_value")
    assert result is None

    # Test with AttributeError
    result = _django_getattr(user, "nonexistent__field", "default_value")
    assert result == "default_value"

    result = _django_getattr(user, "__role", "default_value")
    assert result == "default_value"

    result = _django_getattr(user, "assigned_role____name", "default_value")
    assert result == "default_value"
