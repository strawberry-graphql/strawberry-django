import textwrap
import uuid

import pytest
import strawberry
from django.test import override_settings
from strawberry import auto

import strawberry_django
from tests import models


@strawberry_django.type(models.Fruit)
class FruitType:
    id: auto
    name: auto


@strawberry_django.type(models.UUIDModel)
class UUIDModelType:
    id: auto
    text: auto


@strawberry_django.type(models.NonIdPkModel)
class NonIdPkModelType:
    code: auto
    text: auto


@strawberry_django.type(models.User)
class UserType:
    id: auto
    name: auto


@strawberry.type
class Query:
    fruit: FruitType = strawberry_django.field()
    fruit_by_name: FruitType | None = strawberry_django.field(lookup_key="name")
    uuid_model: UUIDModelType = strawberry_django.field(lookup_key="pk")
    uuid_model_by_id: UUIDModelType = strawberry_django.field(lookup_key="id")
    non_id_pk_model: NonIdPkModelType = strawberry_django.field(lookup_key="code")
    user_by_group: UserType = strawberry_django.field(lookup_key="group")
    user_by_tag: UserType = strawberry_django.field(lookup_key="tag")


schema = strawberry.Schema(query=Query)


def test_lookup_key_schema():
    assert (
        textwrap.dedent(str(schema))
        == textwrap.dedent(
            """\
      type FruitType {
        id: ID!
        name: String!
      }

      type NonIdPkModelType {
        code: String!
        text: String!
      }

      type Query {
        fruit(pk: ID!): FruitType!
        fruitByName(name: String!): FruitType
        uuidModel(pk: UUID!): UUIDModelType!
        uuidModelById(id: UUID!): UUIDModelType!
        nonIdPkModel(code: String!): NonIdPkModelType!
        userByGroup(group: ID!): UserType!
        userByTag(tag: ID!): UserType!
      }

      scalar UUID

      type UUIDModelType {
        id: UUID!
        text: String!
      }

      type UserType {
        id: ID!
        name: String!
      }
    """,
        ).strip()
    )


@pytest.mark.django_db(transaction=True)
def test_lookup_key_with_custom_pk_field_name():
    with override_settings(STRAWBERRY_DJANGO={"DEFAULT_PK_FIELD_NAME": "id"}):

        @strawberry.type
        class Query:
            fruit: FruitType = strawberry_django.field()
            fruit_by_name: FruitType = strawberry_django.field(lookup_key="name")

        schema = strawberry.Schema(query=Query)

        assert "fruit(id: ID!): FruitType!" in str(schema)
        assert "fruitByName(name: String!): FruitType!" in str(schema)

        fruit = models.Fruit.objects.create(name="Banana")
        res = schema.execute_sync(
            """\
          query Fruit ($id: ID!, $name: String!) {
            fruit(id: $id) { name }
            fruitByName(name: $name) { id }
          }
        """,
            variable_values={"id": fruit.pk, "name": "Banana"},
        )
        assert res.errors is None
        assert res.data == {
            "fruit": {"name": "Banana"},
            "fruitByName": {"id": str(fruit.pk)},
        }


@pytest.mark.django_db(transaction=True)
def test_lookup_key_by_field():
    models.Fruit.objects.create(name="Apple")
    banana = models.Fruit.objects.create(name="Banana")

    res = schema.execute_sync(
        """\
      query Fruit ($name: String!) {
        fruitByName(name: $name) { id name }
      }
    """,
        variable_values={"name": "Banana"},
    )
    assert res.errors is None
    assert res.data == {"fruitByName": {"id": str(banana.pk), "name": "Banana"}}

    res = schema.execute_sync('{ fruitByName(name: "Cherry") { id name } }')
    assert res.errors is None
    assert res.data == {"fruitByName": None}


@pytest.mark.django_db(transaction=True)
def test_lookup_key_by_uuid_pk():
    obj = models.UUIDModel.objects.create(text="foo")
    models.UUIDModel.objects.create(text="bar")

    res = schema.execute_sync(
        """\
      query UUIDModel ($pk: UUID!) {
        uuidModel(pk: $pk) { id text }
        uuidModelById(id: $pk) { text }
      }
    """,
        variable_values={"pk": str(obj.pk)},
    )
    assert res.errors is None
    assert res.data == {
        "uuidModel": {"id": str(obj.pk), "text": "foo"},
        "uuidModelById": {"text": "foo"},
    }

    res = schema.execute_sync('{ uuidModel(pk: "not-a-uuid") { text } }')
    assert res.errors is not None
    assert res.data is None

    res = schema.execute_sync(
        f'{{ uuidModel(pk: "{uuid.uuid4()}") {{ text }} }}',
    )
    assert res.errors is not None
    assert res.errors[0].message == "UUIDModel matching query does not exist."


@pytest.mark.django_db(transaction=True)
def test_lookup_key_by_non_id_pk():
    models.NonIdPkModel.objects.create(code="abc", text="foo")
    models.NonIdPkModel.objects.create(code="def", text="bar")

    res = schema.execute_sync('{ nonIdPkModel(code: "def") { code text } }')
    assert res.errors is None
    assert res.data == {"nonIdPkModel": {"code": "def", "text": "bar"}}


@pytest.mark.django_db(transaction=True)
def test_lookup_key_by_relation():
    group = models.Group.objects.create(name="Some Group")
    tag = models.Tag.objects.create(name="Some Tag")
    models.User.objects.create(name="Other User")
    user = models.User.objects.create(name="Some User", group=group, tag=tag)

    res = schema.execute_sync(
        """\
      query User ($group: ID!, $tag: ID!) {
        userByGroup(group: $group) { id name }
        userByTag(tag: $tag) { id name }
      }
    """,
        variable_values={"group": group.pk, "tag": tag.pk},
    )
    assert res.errors is None
    assert res.data == {
        "userByGroup": {"id": str(user.pk), "name": "Some User"},
        "userByTag": {"id": str(user.pk), "name": "Some User"},
    }


def test_lookup_key_reverse_relation():
    @strawberry_django.type(models.Group)
    class GroupType:
        name: auto

    @strawberry.type
    class Query:
        group: GroupType = strawberry_django.field(lookup_key="users")

    with pytest.raises(
        TypeError,
        match=(
            r"Cannot look up Group by 'users': "
            r"only concrete model fields can be used as a lookup key"
        ),
    ):
        strawberry.Schema(query=Query)


def test_lookup_key_unknown_field():
    @strawberry.type
    class Query:
        fruit: FruitType = strawberry_django.field(lookup_key="flavor")

    with pytest.raises(TypeError, match="Fruit has no field named 'flavor'"):
        strawberry.Schema(query=Query)
