# Unit testing

Unit testing can be done by following the
[strawberry's testing docs](https://strawberry.rocks/docs/operations/testing) reference.

This lib also provides a `TestClient` and an `AsyncTestClient` that makes it easier
to run tests by mimicing a call to your API.

For example, suppose you have a `me` query which returns the currently logged in
user or `None` in case it is not authenticated. You could test it like this:

```python
from strawberry_django.test.client import TestClient


def test_me_unauthenticated(db):
    client = TestClient("/graphql")
    res = gql_client.query("""
      query TestQuery {
        me {
          pk
          email
          firstName
          lastName
        }
      }
    """)
    assert res.errors is None
    assert res.data == {"me": None}


def test_me_authenticated(db):
    user = User.objects.create(...)
    client = TestClient("/graphql")

    with client.login(user):
      res = client.query("""
        query TestQuery {
          me {
            pk
            email
            firstName
            lastName
          }
        }
      """)

    assert res.errors is None
    assert res.data == {
        "me": {
            "pk": user.pk,
            "email": user.email,
            "firstName": user.first_name,
            "lastName": user.last_name,
        },
    }
```

For more information how to apply these tests, take a look at the (source)[https://github.com/strawberry-graphql/strawberry-graphql-django/blob/main/strawberry_django/test/client.py] and (this example)[https://github.com/strawberry-graphql/strawberry-graphql-django/blob/main/tests/test_permissions.py#L49]
