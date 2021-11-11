import pytest


@pytest.fixture
def query(schema):
    def query(query):
        return schema.execute_sync(query)

    return query
