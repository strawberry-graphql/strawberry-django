import pytest
from pytest_django import DjangoAssertNumQueries
from strawberry.relay.utils import to_base64

from .schema import FruitModel, schema


@pytest.fixture(autouse=True)
def _fixtures(transactional_db):
    for pk, name, color in [
        (1, "Banana", "yellow"),
        (2, "Apple", "red"),
        (3, "Pineapple", "yellow"),
        (4, "Grape", "purple"),
        (5, "Orange", "orange"),
    ]:
        FruitModel.objects.create(
            id=pk,
            name=name,
            color=color,
        )


def test_query_node():
    result = schema.execute_sync(
        """
        query TestQuery ($id: ID!) {
            node (id: $id) {
                ... on Node {
                    id
                }
                ... on Fruit {
                    name
                    color
                }
            }
        }
        """,
        variable_values={
            "id": to_base64("Fruit", 2),
        },
    )
    assert result.errors is None
    assert result.data == {
        "node": {
            "id": to_base64("Fruit", 2),
            "color": "red",
            "name": "Apple",
        },
    }


async def test_query_node_with_async_permissions():
    result = await schema.execute(
        """
        query TestQuery ($id: ID!) {
            nodeWithAsyncPermissions (id: $id) {
                ... on Node {
                    id
                }
                ... on Fruit {
                    name
                    color
                }
            }
        }
        """,
        variable_values={
            "id": to_base64("Fruit", 2),
        },
    )
    assert result.errors is None
    assert result.data == {
        "nodeWithAsyncPermissions": {
            "id": to_base64("Fruit", 2),
            "color": "red",
            "name": "Apple",
        },
    }


def test_query_node_optional():
    result = schema.execute_sync(
        """
        query TestQuery ($id: ID!) {
            nodeOptional (id: $id) {
                ... on Node {
                    id
                }
                ... on Fruit {
                    name
                    color
                }
            }
        }
        """,
        variable_values={
            "id": to_base64("Fruit", 999),
        },
    )
    assert result.errors is None
    assert result.data == {"nodeOptional": None}


async def test_query_node_async():
    result = await schema.execute(
        """
        query TestQuery ($id: ID!) {
            node (id: $id) {
                ... on Node {
                    id
                }
                ... on Fruit {
                    name
                    color
                }
            }
        }
        """,
        variable_values={
            "id": to_base64("Fruit", 2),
        },
    )
    assert result.errors is None
    assert result.data == {
        "node": {
            "id": to_base64("Fruit", 2),
            "color": "red",
            "name": "Apple",
        },
    }


async def test_query_node_optional_async():
    result = await schema.execute(
        """
        query TestQuery ($id: ID!) {
            nodeOptional (id: $id) {
                ... on Node {
                    id
                }
                ... on Fruit {
                    name
                    color
                }
            }
        }
        """,
        variable_values={
            "id": to_base64("Fruit", 999),
        },
    )
    assert result.errors is None
    assert result.data == {"nodeOptional": None}


def test_query_nodes():
    result = schema.execute_sync(
        """
        query TestQuery ($ids: [ID!]!) {
            nodes (ids: $ids) {
                ... on Node {
                    id
                }
                ... on Fruit {
                    name
                    color
                }
            }
        }
        """,
        variable_values={
            "ids": [to_base64("Fruit", 2), to_base64("Fruit", 4)],
        },
    )
    assert result.errors is None
    assert result.data == {
        "nodes": [
            {
                "id": to_base64("Fruit", 2),
                "name": "Apple",
                "color": "red",
            },
            {
                "id": to_base64("Fruit", 4),
                "name": "Grape",
                "color": "purple",
            },
        ],
    }


def test_query_nodes_optional():
    result = schema.execute_sync(
        """
        query TestQuery ($ids: [ID!]!) {
            nodesOptional (ids: $ids) {
                ... on Node {
                    id
                }
                ... on Fruit {
                    name
                    color
                }
            }
        }
        """,
        variable_values={
            "ids": [
                to_base64("Fruit", 2),
                to_base64("Fruit", 999),
                to_base64("Fruit", 4),
            ],
        },
    )
    assert result.errors is None
    assert result.data == {
        "nodesOptional": [
            {
                "id": to_base64("Fruit", 2),
                "name": "Apple",
                "color": "red",
            },
            None,
            {
                "id": to_base64("Fruit", 4),
                "name": "Grape",
                "color": "purple",
            },
        ],
    }


async def test_query_nodes_async():
    result = await schema.execute(
        """
        query TestQuery ($ids: [ID!]!) {
            nodes (ids: $ids) {
                ... on Node {
                    id
                }
                ... on Fruit {
                    name
                    color
                }
            }
        }
        """,
        variable_values={
            "ids": [
                to_base64("Fruit", 2),
                to_base64("Fruit", 4),
            ],
        },
    )
    assert result.errors is None
    assert result.data == {
        "nodes": [
            {
                "id": to_base64("Fruit", 2),
                "name": "Apple",
                "color": "red",
            },
            {
                "id": to_base64("Fruit", 4),
                "name": "Grape",
                "color": "purple",
            },
        ],
    }


async def test_query_nodes_optional_async():
    result = await schema.execute(
        """
        query TestQuery ($ids: [ID!]!) {
            nodesOptional (ids: $ids) {
                ... on Node {
                    id
                }
                ... on Fruit {
                    name
                    color
                }
            }
        }
        """,
        variable_values={
            "ids": [
                to_base64("Fruit", 2),
                to_base64("Fruit", 998),
                to_base64("Fruit", 4),
                to_base64("Fruit", 999),
            ],
        },
    )
    assert result.errors is None
    assert result.data == {
        "nodesOptional": [
            {
                "id": to_base64("Fruit", 2),
                "name": "Apple",
                "color": "red",
            },
            None,
            {
                "id": to_base64("Fruit", 4),
                "name": "Grape",
                "color": "purple",
            },
            None,
        ],
    }


fruits_query = """
query TestQuery (
    $first: Int = null
    $last: Int = null
    $before: String = null,
    $after: String = null,
) {{
    {} (
        first: $first
        last: $last
        before: $before
        after: $after
    ) {{
        pageInfo {{
            hasNextPage
            hasPreviousPage
            startCursor
            endCursor
        }}
        edges {{
            cursor
            node {{
                id
                name
                color
            }}
        }}
    }}
}}
"""

attrs = [
    "fruits",
    "fruitsLazy",
    "fruitsWithFiltersAndOrder",
    "fruitsCustomResolver",
    "fruitsCustomResolverWithFiltersAndOrder",
]


@pytest.mark.parametrize("query_attr", attrs)
def test_query_connection(query_attr: str):
    result = schema.execute_sync(
        fruits_query.format(query_attr),
        variable_values={},
    )
    assert result.errors is None
    assert result.data == {
        query_attr: {
            "edges": [
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjA=",
                    "node": {
                        "id": to_base64("Fruit", 1),
                        "color": "yellow",
                        "name": "Banana",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjE=",
                    "node": {
                        "id": to_base64("Fruit", 2),
                        "color": "red",
                        "name": "Apple",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjI=",
                    "node": {
                        "id": to_base64("Fruit", 3),
                        "color": "yellow",
                        "name": "Pineapple",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjM=",
                    "node": {
                        "id": to_base64("Fruit", 4),
                        "color": "purple",
                        "name": "Grape",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjQ=",
                    "node": {
                        "id": to_base64("Fruit", 5),
                        "color": "orange",
                        "name": "Orange",
                    },
                },
            ],
            "pageInfo": {
                "hasNextPage": False,
                "hasPreviousPage": False,
                "startCursor": to_base64("arrayconnection", "0"),
                "endCursor": to_base64("arrayconnection", "4"),
            },
        },
    }


@pytest.mark.parametrize("query_attr", attrs)
async def test_query_connection_async(query_attr: str):
    result = await schema.execute(
        fruits_query.format(query_attr),
        variable_values={},
    )
    assert result.errors is None
    assert result.data == {
        query_attr: {
            "edges": [
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjA=",
                    "node": {
                        "id": to_base64("Fruit", 1),
                        "color": "yellow",
                        "name": "Banana",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjE=",
                    "node": {
                        "id": to_base64("Fruit", 2),
                        "color": "red",
                        "name": "Apple",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjI=",
                    "node": {
                        "id": to_base64("Fruit", 3),
                        "color": "yellow",
                        "name": "Pineapple",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjM=",
                    "node": {
                        "id": to_base64("Fruit", 4),
                        "color": "purple",
                        "name": "Grape",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjQ=",
                    "node": {
                        "id": to_base64("Fruit", 5),
                        "color": "orange",
                        "name": "Orange",
                    },
                },
            ],
            "pageInfo": {
                "hasNextPage": False,
                "hasPreviousPage": False,
                "startCursor": to_base64("arrayconnection", "0"),
                "endCursor": to_base64("arrayconnection", "4"),
            },
        },
    }


@pytest.mark.parametrize("query_attr", attrs)
def test_query_connection_filtering_first(query_attr: str):
    result = schema.execute_sync(
        fruits_query.format(query_attr),
        variable_values={"first": 2},
    )
    assert result.errors is None
    assert result.data == {
        query_attr: {
            "edges": [
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjA=",
                    "node": {
                        "id": to_base64("Fruit", 1),
                        "color": "yellow",
                        "name": "Banana",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjE=",
                    "node": {
                        "id": to_base64("Fruit", 2),
                        "color": "red",
                        "name": "Apple",
                    },
                },
            ],
            "pageInfo": {
                "hasNextPage": True,
                "hasPreviousPage": False,
                "startCursor": to_base64("arrayconnection", "0"),
                "endCursor": to_base64("arrayconnection", "1"),
            },
        },
    }


@pytest.mark.parametrize("query_attr", attrs)
async def test_query_connection_filtering_first_async(query_attr: str):
    result = await schema.execute(
        fruits_query.format(query_attr),
        variable_values={"first": 2},
    )
    assert result.errors is None
    assert result.data == {
        query_attr: {
            "edges": [
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjA=",
                    "node": {
                        "id": to_base64("Fruit", 1),
                        "color": "yellow",
                        "name": "Banana",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjE=",
                    "node": {
                        "id": to_base64("Fruit", 2),
                        "color": "red",
                        "name": "Apple",
                    },
                },
            ],
            "pageInfo": {
                "hasNextPage": True,
                "hasPreviousPage": False,
                "startCursor": to_base64("arrayconnection", "0"),
                "endCursor": to_base64("arrayconnection", "1"),
            },
        },
    }


@pytest.mark.parametrize("query_attr", attrs)
def test_query_connection_filtering_first_with_after(query_attr: str):
    result = schema.execute_sync(
        fruits_query.format(query_attr),
        variable_values={"first": 2, "after": to_base64("arrayconnection", "1")},
    )
    assert result.errors is None
    assert result.data == {
        query_attr: {
            "edges": [
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjI=",
                    "node": {
                        "id": to_base64("Fruit", 3),
                        "color": "yellow",
                        "name": "Pineapple",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjM=",
                    "node": {
                        "id": to_base64("Fruit", 4),
                        "color": "purple",
                        "name": "Grape",
                    },
                },
            ],
            "pageInfo": {
                "hasNextPage": True,
                "hasPreviousPage": True,
                "startCursor": to_base64("arrayconnection", "2"),
                "endCursor": to_base64("arrayconnection", "3"),
            },
        },
    }


@pytest.mark.parametrize("query_attr", attrs)
async def test_query_connection_filtering_first_with_after_async(query_attr: str):
    result = await schema.execute(
        fruits_query.format(query_attr),
        variable_values={"first": 2, "after": to_base64("arrayconnection", "1")},
    )
    assert result.errors is None
    assert result.data == {
        query_attr: {
            "edges": [
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjI=",
                    "node": {
                        "id": to_base64("Fruit", 3),
                        "color": "yellow",
                        "name": "Pineapple",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjM=",
                    "node": {
                        "id": to_base64("Fruit", 4),
                        "color": "purple",
                        "name": "Grape",
                    },
                },
            ],
            "pageInfo": {
                "hasNextPage": True,
                "hasPreviousPage": True,
                "startCursor": to_base64("arrayconnection", "2"),
                "endCursor": to_base64("arrayconnection", "3"),
            },
        },
    }


@pytest.mark.parametrize("query_attr", attrs)
def test_query_connection_filtering_last(query_attr: str):
    result = schema.execute_sync(
        fruits_query.format(query_attr),
        variable_values={"last": 2},
    )
    assert result.errors is None
    assert result.data == {
        query_attr: {
            "edges": [
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjM=",
                    "node": {
                        "id": to_base64("Fruit", 4),
                        "color": "purple",
                        "name": "Grape",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjQ=",
                    "node": {
                        "id": to_base64("Fruit", 5),
                        "color": "orange",
                        "name": "Orange",
                    },
                },
            ],
            "pageInfo": {
                "hasNextPage": False,
                "hasPreviousPage": True,
                "startCursor": to_base64("arrayconnection", "3"),
                "endCursor": to_base64("arrayconnection", "4"),
            },
        },
    }


@pytest.mark.parametrize("query_attr", attrs)
async def test_query_connection_filtering_last_async(query_attr: str):
    result = await schema.execute(
        fruits_query.format(query_attr),
        variable_values={"last": 2},
    )
    assert result.errors is None
    assert result.data == {
        query_attr: {
            "edges": [
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjM=",
                    "node": {
                        "id": to_base64("Fruit", 4),
                        "color": "purple",
                        "name": "Grape",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjQ=",
                    "node": {
                        "id": to_base64("Fruit", 5),
                        "color": "orange",
                        "name": "Orange",
                    },
                },
            ],
            "pageInfo": {
                "hasNextPage": False,
                "hasPreviousPage": True,
                "startCursor": to_base64("arrayconnection", "3"),
                "endCursor": to_base64("arrayconnection", "4"),
            },
        },
    }


@pytest.mark.parametrize("query_attr", attrs)
def test_query_connection_filtering_first_with_before(query_attr: str):
    result = schema.execute_sync(
        fruits_query.format(query_attr),
        variable_values={"first": 1, "before": to_base64("arrayconnection", "3")},
    )
    assert result.errors is None
    assert result.data == {
        query_attr: {
            "edges": [
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjI=",
                    "node": {
                        "id": to_base64("Fruit", 3),
                        "color": "yellow",
                        "name": "Pineapple",
                    },
                },
            ],
            "pageInfo": {
                "hasNextPage": True,
                "hasPreviousPage": True,
                "startCursor": to_base64("arrayconnection", "2"),
                "endCursor": to_base64("arrayconnection", "2"),
            },
        },
    }


@pytest.mark.parametrize("query_attr", attrs)
async def test_query_connection_filtering_first_with_before_async(query_attr: str):
    result = await schema.execute(
        fruits_query.format(query_attr),
        variable_values={"first": 1, "before": to_base64("arrayconnection", "3")},
    )
    assert result.errors is None
    assert result.data == {
        query_attr: {
            "edges": [
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjI=",
                    "node": {
                        "id": to_base64("Fruit", 3),
                        "color": "yellow",
                        "name": "Pineapple",
                    },
                },
            ],
            "pageInfo": {
                "hasNextPage": True,
                "hasPreviousPage": True,
                "startCursor": to_base64("arrayconnection", "2"),
                "endCursor": to_base64("arrayconnection", "2"),
            },
        },
    }


@pytest.mark.parametrize("query_attr", attrs)
def test_query_connection_filtering_last_with_before(query_attr: str):
    result = schema.execute_sync(
        fruits_query.format(query_attr),
        variable_values={"last": 2, "before": to_base64("arrayconnection", "4")},
    )
    assert result.errors is None
    assert result.data == {
        query_attr: {
            "edges": [
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjI=",
                    "node": {
                        "id": to_base64("Fruit", 3),
                        "color": "yellow",
                        "name": "Pineapple",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjM=",
                    "node": {
                        "id": to_base64("Fruit", 4),
                        "color": "purple",
                        "name": "Grape",
                    },
                },
            ],
            "pageInfo": {
                "hasNextPage": True,
                "hasPreviousPage": True,
                "startCursor": to_base64("arrayconnection", "2"),
                "endCursor": to_base64("arrayconnection", "3"),
            },
        },
    }


@pytest.mark.parametrize("query_attr", attrs)
async def test_query_connection_filtering_last_with_before_async(query_attr: str):
    result = await schema.execute(
        fruits_query.format(query_attr),
        variable_values={"last": 2, "before": to_base64("arrayconnection", "4")},
    )
    assert result.errors is None
    assert result.data == {
        query_attr: {
            "edges": [
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjI=",
                    "node": {
                        "id": to_base64("Fruit", 3),
                        "color": "yellow",
                        "name": "Pineapple",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjM=",
                    "node": {
                        "id": to_base64("Fruit", 4),
                        "color": "purple",
                        "name": "Grape",
                    },
                },
            ],
            "pageInfo": {
                "hasNextPage": True,
                "hasPreviousPage": True,
                "startCursor": to_base64("arrayconnection", "2"),
                "endCursor": to_base64("arrayconnection", "3"),
            },
        },
    }


fruits_query_filters_order = """
query TestQuery (
    $first: Int = null
    $last: Int = null
    $before: String = null,
    $after: String = null,
    $filters: FruitFilter
    $order: FruitOrder
) {{
    {} (
        first: $first
        last: $last
        before: $before
        after: $after
        filters: $filters
        order: $order
    ) {{
        pageInfo {{
            hasNextPage
            hasPreviousPage
            startCursor
            endCursor
        }}
        edges {{
            cursor
            node {{
                id
                name
                color
            }}
        }}
    }}
}}
"""

custom_attrs = [
    "fruitsWithFiltersAndOrder",
    "fruitsCustomResolverWithFiltersAndOrder",
]


@pytest.mark.parametrize("query_attr", custom_attrs)
def test_query_connection_with_filters(query_attr: str):
    result = schema.execute_sync(
        fruits_query_filters_order.format(query_attr),
        variable_values={"filters": {"name": {"endsWith": "e"}}},
    )
    assert result.errors is None
    assert result.data == {
        query_attr: {
            "edges": [
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjA=",
                    "node": {
                        "id": to_base64("Fruit", 2),
                        "color": "red",
                        "name": "Apple",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjE=",
                    "node": {
                        "id": to_base64("Fruit", 3),
                        "color": "yellow",
                        "name": "Pineapple",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjI=",
                    "node": {
                        "id": to_base64("Fruit", 4),
                        "color": "purple",
                        "name": "Grape",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjM=",
                    "node": {
                        "id": to_base64("Fruit", 5),
                        "color": "orange",
                        "name": "Orange",
                    },
                },
            ],
            "pageInfo": {
                "hasNextPage": False,
                "hasPreviousPage": False,
                "startCursor": to_base64("arrayconnection", "0"),
                "endCursor": to_base64("arrayconnection", "3"),
            },
        },
    }


@pytest.mark.parametrize("query_attr", custom_attrs)
def test_query_connection_with_filters_and_order(query_attr: str):
    result = schema.execute_sync(
        fruits_query_filters_order.format(query_attr),
        variable_values={
            "filters": {"name": {"endsWith": "e"}},
            "order": {"name": "DESC"},
        },
    )
    assert result.errors is None
    assert result.data == {
        query_attr: {
            "edges": [
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjA=",
                    "node": {
                        "id": to_base64("Fruit", 3),
                        "color": "yellow",
                        "name": "Pineapple",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjE=",
                    "node": {
                        "id": to_base64("Fruit", 5),
                        "color": "orange",
                        "name": "Orange",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjI=",
                    "node": {
                        "id": to_base64("Fruit", 4),
                        "color": "purple",
                        "name": "Grape",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjM=",
                    "node": {
                        "id": to_base64("Fruit", 2),
                        "color": "red",
                        "name": "Apple",
                    },
                },
            ],
            "pageInfo": {
                "hasNextPage": False,
                "hasPreviousPage": False,
                "startCursor": to_base64("arrayconnection", "0"),
                "endCursor": to_base64("arrayconnection", "3"),
            },
        },
    }


@pytest.mark.parametrize("query_attr", custom_attrs)
def test_query_connection_custom_resolver_filtering_first(query_attr: str):
    result = schema.execute_sync(
        fruits_query_filters_order.format(query_attr),
        variable_values={"first": 2, "filters": {"name": {"endsWith": "e"}}},
    )
    assert result.errors is None
    assert result.data == {
        query_attr: {
            "edges": [
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjA=",
                    "node": {
                        "id": to_base64("Fruit", 2),
                        "color": "red",
                        "name": "Apple",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjE=",
                    "node": {
                        "id": to_base64("Fruit", 3),
                        "color": "yellow",
                        "name": "Pineapple",
                    },
                },
            ],
            "pageInfo": {
                "hasNextPage": True,
                "hasPreviousPage": False,
                "startCursor": to_base64("arrayconnection", "0"),
                "endCursor": to_base64("arrayconnection", "1"),
            },
        },
    }


@pytest.mark.parametrize("query_attr", custom_attrs)
def test_query_connection_custom_resolver_filtering_first_with_after(query_attr: str):
    result = schema.execute_sync(
        fruits_query_filters_order.format(query_attr),
        variable_values={
            "first": 2,
            "after": to_base64("arrayconnection", "1"),
            "filters": {"name": {"endsWith": "e"}},
        },
    )
    assert result.errors is None
    assert result.data == {
        query_attr: {
            "edges": [
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjI=",
                    "node": {
                        "id": to_base64("Fruit", 4),
                        "color": "purple",
                        "name": "Grape",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjM=",
                    "node": {
                        "id": to_base64("Fruit", 5),
                        "color": "orange",
                        "name": "Orange",
                    },
                },
            ],
            "pageInfo": {
                "hasNextPage": False,
                "hasPreviousPage": True,
                "startCursor": to_base64("arrayconnection", "2"),
                "endCursor": to_base64("arrayconnection", "3"),
            },
        },
    }


@pytest.mark.parametrize("query_attr", custom_attrs)
def test_query_connection_custom_resolver_filtering_last(query_attr: str):
    result = schema.execute_sync(
        fruits_query_filters_order.format(query_attr),
        variable_values={"last": 2, "filters": {"name": {"endsWith": "e"}}},
    )
    assert result.errors is None
    assert result.data == {
        query_attr: {
            "edges": [
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjI=",
                    "node": {
                        "id": to_base64("Fruit", 4),
                        "color": "purple",
                        "name": "Grape",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjM=",
                    "node": {
                        "id": to_base64("Fruit", 5),
                        "color": "orange",
                        "name": "Orange",
                    },
                },
            ],
            "pageInfo": {
                "hasNextPage": False,
                "hasPreviousPage": True,
                "startCursor": to_base64("arrayconnection", "2"),
                "endCursor": to_base64("arrayconnection", "3"),
            },
        },
    }


@pytest.mark.parametrize("query_attr", custom_attrs)
def test_query_connection_custom_resolver_filtering_last_with_before(query_attr: str):
    result = schema.execute_sync(
        fruits_query_filters_order.format(query_attr),
        variable_values={
            "last": 2,
            "before": to_base64("arrayconnection", "3"),
            "filters": {"name": {"endsWith": "e"}},
        },
    )
    assert result.errors is None
    assert result.data == {
        query_attr: {
            "edges": [
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjE=",
                    "node": {
                        "id": to_base64("Fruit", 3),
                        "color": "yellow",
                        "name": "Pineapple",
                    },
                },
                {
                    "cursor": "YXJyYXljb25uZWN0aW9uOjI=",
                    "node": {
                        "id": to_base64("Fruit", 4),
                        "color": "purple",
                        "name": "Grape",
                    },
                },
            ],
            "pageInfo": {
                "hasNextPage": True,
                "hasPreviousPage": True,
                "startCursor": to_base64("arrayconnection", "1"),
                "endCursor": to_base64("arrayconnection", "2"),
            },
        },
    }


fruits_query_total_count = """
query TestQuery (
    $first: Int = null
    $last: Int = null
    $before: String = null,
    $after: String = null,
) {{
    {} (
        first: $first
        last: $last
        before: $before
        after: $after
    ) {{
        totalCount
    }}
}}
"""

attrs = [
    "fruits",
    "fruitsLazy",
    "fruitsWithFiltersAndOrder",
    "fruitsCustomResolver",
    "fruitsCustomResolverWithFiltersAndOrder",
]


@pytest.mark.parametrize("query_attr", custom_attrs)
def test_query_connection_total_count_sql_queries(
    django_assert_num_queries: DjangoAssertNumQueries, query_attr: str
):
    with django_assert_num_queries(1):
        result = schema.execute_sync(
            fruits_query_total_count.format(query_attr),
            variable_values={},
        )
    assert result.errors is None
    assert result.data == {
        query_attr: {"totalCount": 5},
    }
