from unittest.mock import patch

import pytest
import strawberry
from graphql import validate

from strawberry_django.extensions.django_validation_cache import DjangoValidationCache


@pytest.mark.filterwarnings("ignore::django.core.cache.backends.base.CacheKeyWarning")
@patch("strawberry_django.extensions.django_validation_cache.validate", wraps=validate)
def test_validation_cache_extension(mock_validate):
    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self) -> str:
            return "world"

        @strawberry.field
        def ping(self) -> str:
            return "pong"

    schema = strawberry.Schema(query=Query, extensions=[DjangoValidationCache()])

    query = "query { hello }"

    result = schema.execute_sync(query)

    assert not result.errors
    assert result.data == {"hello": "world"}

    assert mock_validate.call_count == 1

    # Run query multiple times
    for _ in range(3):
        result = schema.execute_sync(query)
        assert not result.errors
        assert result.data == {"hello": "world"}

    # validate is still only called once
    assert mock_validate.call_count == 1

    # Running a second query doesn't cache
    query2 = "query { ping }"
    result = schema.execute_sync(query2)

    assert not result.errors
    assert result.data == {"ping": "pong"}

    assert mock_validate.call_count == 2
