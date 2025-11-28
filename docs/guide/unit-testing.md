---
title: Unit Testing
---

# Unit Testing

Unit testing can be done by following the
[Strawberry's testing docs](https://strawberry.rocks/docs/operations/testing) reference.

This library provides `TestClient` and `AsyncTestClient` that make it easier to run tests by mimicking calls to your GraphQL API with Django's test client.

## Installation

The test clients are included with strawberry-django. No additional installation required.

## TestClient (Sync)

The synchronous test client for testing regular Django views.

### Basic Usage

```python
from strawberry_django.test.client import TestClient


def test_query(db):
    client = TestClient("/graphql")
    response = client.query("""
        query {
            fruits {
                id
                name
            }
        }
    """)
    assert response.errors is None
    assert response.data == {"fruits": [{"id": "1", "name": "Apple"}]}
```

### Constructor

```python
TestClient(path: str, client: Client | None = None)
```

| Parameter | Type             | Description                                                                    |
| --------- | ---------------- | ------------------------------------------------------------------------------ |
| `path`    | `str`            | The URL path to your GraphQL endpoint (e.g., `"/graphql"`)                     |
| `client`  | `Client \| None` | Optional Django test `Client` instance. If not provided, a new one is created. |

### query() Method

```python
client.query(
    query: str,
    variables: dict[str, Any] | None = None,
    headers: dict[str, object] | None = None,
    files: dict[str, object] | None = None,
    assert_no_errors: bool = True,
) -> Response
```

| Parameter          | Type   | Default  | Description                                |
| ------------------ | ------ | -------- | ------------------------------------------ |
| `query`            | `str`  | required | The GraphQL query/mutation string          |
| `variables`        | `dict` | `None`   | Variables to pass to the query             |
| `headers`          | `dict` | `None`   | HTTP headers to include in the request     |
| `files`            | `dict` | `None`   | Files for multipart uploads                |
| `assert_no_errors` | `bool` | `True`   | Automatically assert no errors in response |

### Response Object

The `query()` method returns a `Response` object:

```python
@dataclass
class Response:
    errors: list[GraphQLFormattedError] | None
    data: dict[str, object] | None
    extensions: dict[str, object] | None
```

### Testing with Variables

```python
def test_with_variables(db):
    client = TestClient("/graphql")
    response = client.query(
        """
        query GetFruit($id: ID!) {
            fruit(id: $id) {
                name
            }
        }
        """,
        variables={"id": "1"},
    )
    assert response.data == {"fruit": {"name": "Apple"}}
```

### Testing Mutations

```python
def test_create_fruit(db):
    client = TestClient("/graphql")
    response = client.query(
        """
        mutation CreateFruit($input: FruitInput!) {
            createFruit(input: $input) {
                id
                name
            }
        }
        """,
        variables={"input": {"name": "Banana", "color": "yellow"}},
    )
    assert response.errors is None
    assert response.data["createFruit"]["name"] == "Banana"
```

### Testing with Authentication

Use the `login()` context manager to simulate an authenticated user:

```python
from django.contrib.auth import get_user_model

User = get_user_model()


def test_authenticated_query(db):
    user = User.objects.create_user(username="testuser", password="testpass")
    client = TestClient("/graphql")

    with client.login(user):
        response = client.query("""
            query {
                me {
                    username
                }
            }
        """)

    assert response.errors is None
    assert response.data == {"me": {"username": "testuser"}}
```

### Testing with Custom Headers

```python
def test_with_headers(db):
    client = TestClient("/graphql")
    response = client.query(
        """
        query {
            protectedData
        }
        """,
        headers={"Authorization": "Bearer token123"},
    )
    assert response.errors is None
```

### Testing File Uploads

```python
from django.core.files.uploadedfile import SimpleUploadedFile


def test_file_upload(db):
    client = TestClient("/graphql")
    test_file = SimpleUploadedFile("test.txt", b"file content", content_type="text/plain")

    response = client.query(
        """
        mutation UploadFile($file: Upload!) {
            uploadFile(file: $file) {
                success
            }
        }
        """,
        variables={"file": None},
        files={"file": test_file},
    )
    assert response.errors is None
```

### Expecting Errors

When testing error cases, set `assert_no_errors=False`:

```python
def test_validation_error(db):
    client = TestClient("/graphql")
    response = client.query(
        """
        mutation {
            createFruit(input: {name: ""}) {
                id
            }
        }
        """,
        assert_no_errors=False,
    )
    assert response.errors is not None
    assert "name" in response.errors[0]["message"].lower()
```

## AsyncTestClient

The asynchronous test client for testing async views and ASGI applications.

### Basic Usage

```python
import pytest
from strawberry_django.test.client import AsyncTestClient


@pytest.mark.asyncio
async def test_async_query(db):
    client = AsyncTestClient("/graphql")
    response = await client.query("""
        query {
            fruits {
                id
                name
            }
        }
    """)
    assert response.errors is None
```

### Constructor

```python
AsyncTestClient(path: str, client: AsyncClient | None = None)
```

| Parameter | Type                  | Description                            |
| --------- | --------------------- | -------------------------------------- |
| `path`    | `str`                 | The URL path to your GraphQL endpoint  |
| `client`  | `AsyncClient \| None` | Optional Django `AsyncClient` instance |

### Async Login

```python
@pytest.mark.asyncio
async def test_async_authenticated(db):
    user = await sync_to_async(User.objects.create_user)(
        username="testuser", password="testpass"
    )
    client = AsyncTestClient("/graphql")

    async with client.login(user):
        response = await client.query("""
            query {
                me {
                    username
                }
            }
        """)

    assert response.data == {"me": {"username": "testuser"}}
```

## Using with pytest-django

For pytest-django users, remember to use the `db` fixture:

```python
import pytest


@pytest.mark.django_db
def test_with_database():
    client = TestClient("/graphql")
    # ... your test


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_async_with_database():
    client = AsyncTestClient("/graphql")
    # ... your async test
```

## Using a Custom Django Client

You can pass a pre-configured Django test client:

```python
from django.test import Client


def test_with_custom_client(db):
    django_client = Client(enforce_csrf_checks=True)
    client = TestClient("/graphql", client=django_client)
    # ...
```

## Testing Subscriptions

For testing subscriptions, refer to the [Strawberry WebSocket testing documentation](https://strawberry.rocks/docs/integrations/channels#testing).

## See Also

- [Strawberry Testing Docs](https://strawberry.rocks/docs/operations/testing) - Core testing documentation
- [Django Testing Docs](https://docs.djangoproject.com/en/4.2/topics/testing/) - Django's test framework
- [pytest-django](https://pytest-django.readthedocs.io/) - pytest plugin for Django
