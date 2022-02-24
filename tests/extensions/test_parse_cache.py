from unittest.mock import patch

import pytest
import strawberry
from graphql import parse, version as graphql_version

from strawberry_django.extensions import DjangoParserCache


@pytest.mark.xfail(
    graphql_version < "3.2.0",
    reason=(
        "GraphQL document nodes cannot be unpickled in versions below 3.2. "
        "https://github.com/graphql-python/graphql-core/issues/112"
    ),
)
@pytest.mark.filterwarnings("ignore::django.core.cache.backends.base.CacheKeyWarning")
@patch("strawberry.schema.execute.parse", wraps=parse)
def test_parser_cache_extension(mock_parse):
    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self) -> str:
            return "world"

        @strawberry.field
        def ping(self) -> str:
            return "pong"

    schema = strawberry.Schema(query=Query, extensions=[DjangoParserCache()])

    query = "query { hello }"

    result = schema.execute_sync(query)

    assert not result.errors
    assert result.data == {"hello": "world"}

    assert mock_parse.call_count == 1

    # Run query multiple times
    for _ in range(3):
        result = schema.execute_sync(query)
        assert not result.errors
        assert result.data == {"hello": "world"}

    # validate is still only called once
    assert mock_parse.call_count == 1

    # Running a second query doesn't cache
    query2 = "query { ping }"
    result = schema.execute_sync(query2)

    assert not result.errors
    assert result.data == {"ping": "pong"}

    assert mock_parse.call_count == 2
