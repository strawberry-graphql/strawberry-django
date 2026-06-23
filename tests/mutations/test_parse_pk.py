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
    obj, data = resolvers._parse_pk({"name": "red"}, models.Color, key_attr="name")
    assert obj == red
    assert data == {"name": "red"}


def test_parse_pk_bare_value_by_non_pk_key(colors):
    """A bare value with a non-pk `key_attr` looks the instance up by that field."""
    _, blue = colors
    obj, data = resolvers._parse_pk("blue", models.Color, key_attr="name")
    assert obj == blue
    assert data is None


def test_parse_pk_non_pk_key_does_not_fall_back_to_pk(colors):
    """A non-pk `key_attr` must query that field, never `pk=`.

    Before the fix this queried ``get(pk="red")`` and raised ``ValueError`` /
    ``DoesNotExist`` instead of resolving by name.
    """
    red, _ = colors
    obj, _data = resolvers._parse_pk({"name": "red"}, models.Color, key_attr="name")
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
        {dict_key: blue.pk}, models.Color, key_attr=key_attr
    )
    assert obj == blue
    assert data == {dict_key: blue.pk}
    # bare-value branch
    obj, data = resolvers._parse_pk(red.pk, models.Color, key_attr=key_attr)
    assert obj == red
    assert data is None
