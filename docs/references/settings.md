# Django Settings

Certain features of this library are configured using custom [Django settings](https://docs.djangoproject.com/en/4.1/topics/settings/).

## STRAWBERRY_DJANGO

A dictionary with the following optional keys:

- **`FIELD_DESCRIPTION_FROM_HELP_TEXT`** (Default: `False`)

      If True, [GraphQL field's description](https://spec.graphql.org/draft/#sec-Descriptions) will be fetched from the corresponding Django model field's [`help_text` attribute](https://docs.djangoproject.com/en/4.1/ref/models/fields/#help-text). If a description is provided using [field customization](fields.md#field-customization), that description will be used instead.

- **`TYPE_DESCRIPTION_FROM_MODEL_DOCSTRING`** (Default: `False`)

      If True, [GraphQL type descriptions](https://spec.graphql.org/draft/#sec-Descriptions) will be fetched from the corresponding Django model's [docstring](https://docs.python.org/3/glossary.html#term-docstring). If a description is provided using the [`strawberry_django.type` decorator](types.md#types-from-django-models), that description will be used instead.

These features can be enabled by adding this code to your `settings.py` file.

```python
STRAWBERRY_DJANGO = {
    "FIELD_DESCRIPTION_FROM_HELP_TEXT": True,
    "TYPE_DESCRIPTION_FROM_MODEL_DOCSTRING": True,
}
```
