"""Regression tests for `_parse_pk` honoring `DEFAULT_PK_FIELD_NAME`.

`_parse_pk` reads a mutation input under `key_attr` (defaulting to the
`DEFAULT_PK_FIELD_NAME` setting), but it used to always look the instance up by
`pk=`, ignoring `key_attr`. When `DEFAULT_PK_FIELD_NAME` names a non-pk field,
`update` and relation-by-field inputs then queried `get(pk=<value-of-the-field>)`
and raised `DoesNotExist` / matched the wrong row. Filters already honor the
setting; these tests pin the same behavior for mutations.

Regression test for https://github.com/strawberry-graphql/strawberry-django/issues/927
"""

import pytest

from strawberry_django.mutations import resolvers
from tests import models


@pytest.fixture
def colors(db):
    # ``pk`` and ``name`` are deliberately misaligned so a lookup by the wrong
    # field resolves a different row (or none), surfacing the bug.
    red = models.Color.objects.create(name="red")
    blue = models.Color.objects.create(name="blue")
    assert red.pk != blue.pk
    return red, blue


def test_parse_pk_dict_by_non_pk_key(colors):
    """A dict input under a non-pk `key_attr` looks the instance up by that field."""
    red, _ = colors
    obj, data = resolvers._parse_pk({"name": "red"}, models.Color, key_attr="name")  # pyright: ignore[reportArgumentType]
    assert obj == red
    assert data == {"name": "red"}


def test_parse_pk_bare_value_by_non_pk_key(colors):
    """A bare value with a non-pk `key_attr` looks the instance up by that field."""
    _, blue = colors
    obj, data = resolvers._parse_pk("blue", models.Color, key_attr="name")  # pyright: ignore[reportArgumentType]
    assert obj == blue
    assert data is None


def test_parse_pk_non_pk_key_does_not_fall_back_to_pk(colors):
    """A non-pk `key_attr` must query that field, never `pk=`.

    Before the fix this queried ``get(pk="red")`` and raised ``ValueError`` /
    ``DoesNotExist`` instead of resolving by name.
    """
    red, _ = colors
    obj, _data = resolvers._parse_pk({"name": "red"}, models.Color, key_attr="name")  # pyright: ignore[reportArgumentType]
    assert obj is not None
    assert obj.pk == red.pk


@pytest.mark.parametrize("key_attr", [None, "pk", "id"])
def test_parse_pk_default_path_uses_pk(colors, key_attr):
    """The pk path stays byte-for-byte equivalent: `pk`/`id` resolve by `pk`.

    `id` is the primary key of `Color`, so it must map to a `pk=` lookup; `None`
    falls back to the `DEFAULT_PK_FIELD_NAME` default of `pk`.
    """
    red, blue = colors
    dict_key = key_attr or "pk"
    # dict branch
    obj, data = resolvers._parse_pk(
        {dict_key: blue.pk},  # pyright: ignore[reportArgumentType]
        models.Color,
        key_attr=key_attr,
    )
    assert obj == blue
    assert data == {dict_key: blue.pk}
    # bare-value branch
    obj, data = resolvers._parse_pk(red.pk, models.Color, key_attr=key_attr)
    assert obj == red
    assert data is None


@pytest.mark.parametrize("key_attr", [None, "pk", "code"])
def test_pk_lookup_non_id_pk_routes_to_pk(key_attr):
    """A `key_attr` naming a non-`id` primary key still routes via `pk=`.

    `NonIdPkModel`'s primary key is the `code` field. `_pk_lookup` only reads
    `model._meta.pk` (no DB), so we can assert the lookup dict directly. This is
    the part the object-equality tests can't see: `get(pk=v)` and `get(code=v)`
    resolve the same row, so only inspecting the dict proves we kept the `pk=`
    key for the default path instead of `{code: v}`.
    """
    assert resolvers._pk_lookup(models.NonIdPkModel, key_attr, "x") == {"pk": "x"}


def test_pk_lookup_non_pk_key_keeps_that_field():
    """A `key_attr` that is *not* the primary key looks up by that field."""
    assert resolvers._pk_lookup(models.NonIdPkModel, "text", "x") == {"text": "x"}


@pytest.fixture
def coded(db):
    a = models.NonIdPkModel.objects.create(code="a", text="alpha")
    b = models.NonIdPkModel.objects.create(code="b", text="beta")
    return a, b


@pytest.mark.parametrize("key_attr", [None, "pk", "code"])
def test_parse_pk_non_id_pk_default_path_uses_pk(coded, key_attr):
    """Models with a non-`id` primary key still resolve via `pk` end to end."""
    a, b = coded
    dict_key = key_attr or "pk"
    # dict branch
    obj, data = resolvers._parse_pk(
        {dict_key: b.pk},  # pyright: ignore[reportArgumentType]
        models.NonIdPkModel,
        key_attr=key_attr,
    )
    assert obj == b
    assert data == {dict_key: b.pk}
    # bare-value branch
    obj, data = resolvers._parse_pk(a.pk, models.NonIdPkModel, key_attr=key_attr)
    assert obj == a
    assert data is None
