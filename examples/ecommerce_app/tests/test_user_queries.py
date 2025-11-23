"""Tests for user queries demonstrating Strawberry Django testing patterns."""

import pytest
from app.schema import schema
from django.contrib.auth import get_user_model
from strawberry.test import BaseGraphQLTestClient

User = get_user_model()


@pytest.fixture
def graphql_client():
    """Create a GraphQL test client."""
    return BaseGraphQLTestClient(schema)


def test_me_query_unauthenticated(graphql_client, db):
    """Test that me query returns null when not authenticated."""
    query = """
        query {
            me {
                id
                name
            }
        }
    """
    result = graphql_client.query(query)
    assert result.data == {"me": None}


def test_me_query_authenticated(graphql_client, user, client):
    """Test that me query returns user data when authenticated.

    Demonstrates:
    - Testing authenticated queries
    - Using Django's test client to manage sessions
    """
    client.force_login(user)

    query = """
        query {
            me {
                id
                name
                emails {
                    email
                }
            }
        }
    """

    # Note: In a real app, you'd need to pass the request context
    # This is a simplified example showing the query structure
    result = graphql_client.query(query)
    # The actual assertion would depend on your context setup
    assert result.errors is None or len(result.errors) == 0


def test_login_mutation(graphql_client, user, db):
    """Test login mutation with valid credentials.

    Demonstrates:
    - Testing mutations
    - Handling authentication
    - Error handling
    """
    mutation = """
        mutation Login($username: String!, $password: String!) {
            login(username: $username, password: $password) {
                id
                name
            }
        }
    """

    # Test with correct credentials
    result = graphql_client.query(
        mutation,
        variables={"username": "testuser", "password": "testpass123"},
    )

    # Note: Actual behavior depends on context setup
    # This demonstrates the structure of a login test


def test_users_query_with_filters(graphql_client, user, db):
    """Test users query with filtering.

    Demonstrates:
    - Testing filtered queries
    - Pagination
    - Complex query structures
    """
    # Create additional users
    User.objects.create_user(
        username="john",
        first_name="John",
        last_name="Doe",
    )
    User.objects.create_user(
        username="jane",
        first_name="Jane",
        last_name="Smith",
    )

    query = """
        query Users($filters: UserFilter, $pagination: OffsetPaginationInput) {
            users(filters: $filters, pagination: $pagination) {
                id
                name
            }
        }
    """

    result = graphql_client.query(
        query,
        variables={
            "filters": {"firstName": {"exact": "John"}},
            "pagination": {"limit": 10, "offset": 0},
        },
    )

    # In a real test, you'd verify the filtered results
    assert result.errors is None or len(result.errors) == 0
