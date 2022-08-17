"""
Code for interacting with Django settings.
"""
from typing import TypedDict

from django.conf import settings


class StrawberryDjangoSettings(TypedDict):
    """
    Dictionary defining the shape `settings.STRAWBERRY_DJANGO` should have.

    All settings are optional and have defaults as described in their docstrings and
    defined in `DEFAULT_DJANGO_SETTINGS`.
    """

    FIELD_DESCRIPTION_FROM_HELP_TEXT: bool
    """(Default: False) If True, field descriptions will be fetched from the
    corresponding model field's `help_text` attribute."""

    TYPE_DESCRIPTION_FROM_MODEL_DOCSTRING: bool
    """(Default: False) If True, type descriptions will be fetched from the
    corresponding model's docstring."""


DEFAULT_DJANGO_SETTINGS = StrawberryDjangoSettings(
    FIELD_DESCRIPTION_FROM_HELP_TEXT=False,
    TYPE_DESCRIPTION_FROM_MODEL_DOCSTRING=False,
)


def strawberry_django_settings() -> StrawberryDjangoSettings:
    """
    Return the dictionary from `settings.STRAWBERRY_DJANGO`, with defaults for missing
    keys.

    Preferred to direct access for the type hints and defaults.
    """
    defaults = DEFAULT_DJANGO_SETTINGS
    customized = {**defaults, **getattr(settings, "STRAWBERRY_DJANGO", {})}
    return customized
