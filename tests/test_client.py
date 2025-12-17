import pytest
from django.test.client import Client

from strawberry_django.test.client import AsyncTestClient
from tests.utils import GraphQLTestClient

query_to_non_existed_field = "{ nonExistentField { id } }"


def check_non_existed_field_error(errors):
    assert isinstance(errors, list)
    assert len(errors) == 1
    error = errors[0]
    assert isinstance(error, dict)
    assert "nonExistentField" in error["message"]
    assert "Cannot query field" in error["message"]
    assert error["locations"]


def test_client_assert_no_errors_verbose_message(db):
    """Test that GraphQLTestClient (sync) raises AssertionError with verbose error messages.

    This test directly uses GraphQLTestClient with a sync Client to verify the verbose
    error message functionality in the sync client implementation.
    """
    client = GraphQLTestClient("/graphql/", Client())

    with pytest.raises(AssertionError) as exc_info:
        client.query(query_to_non_existed_field)

    check_non_existed_field_error(exc_info.value.args[0])


@pytest.mark.asyncio
async def test_async_client_assert_no_errors_verbose_message(db):
    """Test that AsyncTestClient raises AssertionError with verbose error messages.

    This test directly uses AsyncTestClient to verify the verbose error message
    functionality in the async client implementation.
    """
    client = AsyncTestClient("/graphql_async/")

    with pytest.raises(AssertionError) as exc_info:
        await client.query(query_to_non_existed_field)

    check_non_existed_field_error(exc_info.value.args[0])
