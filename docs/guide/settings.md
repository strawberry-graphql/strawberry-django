---
title: Settings
---

# Django Settings

Certain features of this library are configured using custom
[Django settings](https://docs.djangoproject.com/en/4.2/topics/settings/).

## STRAWBERRY_DJANGO

A dictionary with the following optional keys:

- **`FIELD_DESCRIPTION_FROM_HELP_TEXT`** (default: `False`)

      If True, [GraphQL field's description](https://spec.graphql.org/draft/#sec-Descriptions)
      will be fetched from the corresponding Django model field's
      [`help_text` attribute](https://docs.djangoproject.com/en/4.1/ref/models/fields/#help-text).
      If a description is provided using [field customization](fields.md#field-customization),
      that description will be used instead.

- **`TYPE_DESCRIPTION_FROM_MODEL_DOCSTRING`** (default: `False`)

      If True, [GraphQL type descriptions](https://spec.graphql.org/draft/#sec-Descriptions)
      will be fetched from the corresponding Django model's
      [docstring](https://docs.python.org/3/glossary.html#term-docstring).
      If a description is provided using the
      [`strawberry_django.type` decorator](types.md#types-from-django-models),
      that description will be used instead.

- **`MUTATIONS_DEFAULT_ARGUMENT_NAME`** (default: `"data"`)

      Change the [CUD mutations'](mutations.md#cud-mutations) default
      argument name when no option is passed (e.g. to `"input"`)

- **`MUTATIONS_DEFAULT_HANDLE_ERRORS`** (default: `False`)

      Set the default behaviour of the
      [Django Errors Handling](mutations.md#django-errors-handling)
      when no option is passed.

- **`GENERATE_ENUMS_FROM_CHOICES`** (default: `False`)

      If True, fields with `choices` will have automatically generate
      an enum of possibilities instead of being exposed as `String`.
      A better option is to use
      [Django's TextChoices/IntegerChoices](https://docs.djangoproject.com/en/4.2/ref/models/fields/#enumeration-types)
      with the [django-choices-field](../integrations/choices-field.md) integration.

- **`MAP_AUTO_ID_AS_GLOBAL_ID`** (default: `False`)

      If True, `auto` fields that refer to model ids will be mapped to `relay.GlobalID`
      instead of `strawberry.ID`. This is mostly useful if all your model types inherit
      from `relay.Node` and you want to work only with `GlobalID`.

- **`DEFAULT_PK_FIELD_NAME`** (default: `"pk"`)

      Change the [CRUD mutations'](mutations.md#cud-mutations) default
      primary key field.

- **`USE_DEPRECATED_FILTERS`** (default: `False`)

      If True, [legacy filters](filters.md#legacy-filtering) are enabled. This is usefull for migrating from previous version.

- **`PAGINATION_DEFAULT_LIMIT`** (default: `100`)

      Default limit for [pagination](pagination.md) when one is not provided by the client. Can be set to `None` to set it to unlimited.

- **`ALLOW_MUTATIONS_WITHOUT_FILTERS`** (default: `False`)

      If True, [CUD mutations](mutations.md#cud-mutations) will not require a filter to be specified.
      This is useful for cases where you want to allow mutations without any filtering, but it can lead to unintended side effects if not used carefully.

These features can be enabled by adding this code to your `settings.py` file, like:

```python title="settings.py"
STRAWBERRY_DJANGO = {
    "FIELD_DESCRIPTION_FROM_HELP_TEXT": True,
    "TYPE_DESCRIPTION_FROM_MODEL_DOCSTRING": True,
    "MUTATIONS_DEFAULT_ARGUMENT_NAME": "input",
    "MUTATIONS_DEFAULT_HANDLE_ERRORS": True,
    "GENERATE_ENUMS_FROM_CHOICES": False,
    "MAP_AUTO_ID_AS_GLOBAL_ID": True,
    "DEFAULT_PK_FIELD_NAME": "id",
    "PAGINATION_DEFAULT_LIMIT": 250,
    "ALLOW_MUTATIONS_WITHOUT_FILTERS": True,
}
```
