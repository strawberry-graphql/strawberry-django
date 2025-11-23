# Tests

This directory contains example tests demonstrating how to test Strawberry Django applications.

## Running Tests

```bash
# Run all tests
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run specific test file
poetry run pytest tests/test_user_queries.py

# Run with coverage report
poetry run pytest --cov=app --cov-report=html
```

## Test Structure

- `conftest.py` - Pytest fixtures and configuration
- `test_user_queries.py` - Example tests for user-related queries and mutations

## Writing Tests

### Basic Query Test

```python
def test_simple_query(graphql_client):
    query = """
        query {
            products(pagination: { limit: 10 }) {
                id
                name
            }
        }
    """
    result = graphql_client.query(query)
    assert result.errors is None
    assert len(result.data["products"]) <= 10
```

### Testing with Authentication

```python
def test_authenticated_query(graphql_client, user, client):
    # Set up authentication
    client.force_login(user)
    
    query = """
        query {
            me {
                id
                name
            }
        }
    """
    
    # Pass request context to the query
    result = graphql_client.query(query, context_value={"request": client})
    assert result.data["me"]["id"] == user.id
```

### Testing Mutations

```python
def test_mutation(graphql_client, user):
    mutation = """
        mutation AddToCart($productId: GlobalID!, $quantity: Int!) {
            cartAddItem(product: $productId, quantity: $quantity) {
                id
                quantity
            }
        }
    """
    
    result = graphql_client.query(
        mutation,
        variables={
            "productId": "UHJvZHVjdFR5cGU6MQ==",
            "quantity": 2,
        },
    )
    assert result.errors is None
    assert result.data["cartAddItem"]["quantity"] == 2
```

## Best Practices

1. **Use fixtures** - Create reusable test data in `conftest.py`
2. **Test permissions** - Verify that protected queries/mutations require authentication
3. **Test error cases** - Ensure proper error handling and validation
4. **Use transactions** - Tests automatically roll back database changes
5. **Mock external services** - Isolate tests from external dependencies

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-django Documentation](https://pytest-django.readthedocs.io/)
- [Strawberry Testing Documentation](https://strawberry.rocks/docs/general/testing)
