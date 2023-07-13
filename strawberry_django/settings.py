"""Code for interacting with Django settings."""

from typing import cast

from django.conf import settings
from typing_extensions import TypedDict


class StrawberryDjangoSettings(TypedDict):
    """Dictionary defining the shape `settings.STRAWBERRY_DJANGO` should have.

    All settings are optional and have defaults as described in their docstrings and
    defined in `DEFAULT_DJANGO_SETTINGS`.
    """

    #: If True, field descriptions will be fetched from the
    #: corresponding model field's `help_text` attribute.
    FIELD_DESCRIPTION_FROM_HELP_TEXT: bool

    #: If True, type descriptions will be fetched from the
    #: corresponding model model's docstring.
    TYPE_DESCRIPTION_FROM_MODEL_DOCSTRING: bool

    #: If True, fields with `choices` will have automatically generate
    #: an enum of possibilities instead of being exposed as `String`
    GENERATE_ENUMS_FROM_CHOICES: bool

    #: Set a custom default name for CUD mutations input type.
    MUTATIONS_DEFAULT_ARGUMENT_NAME: str

    #: If True, mutations will default to handling django errors by default
    #: when no option is passed to the field itself.
    MUTATIONS_DEFAULT_HANDLE_ERRORS: bool

    #: If True, `auto` fields that refer to model ids will be mapped to
    #: `relay.GlobalID` instead of `strawberry.ID` for types and filters.
    MAP_AUTO_ID_AS_GLOBAL_ID: bool


DEFAULT_DJANGO_SETTINGS = StrawberryDjangoSettings(
    FIELD_DESCRIPTION_FROM_HELP_TEXT=False,
    TYPE_DESCRIPTION_FROM_MODEL_DOCSTRING=False,
    GENERATE_ENUMS_FROM_CHOICES=False,
    MUTATIONS_DEFAULT_ARGUMENT_NAME="data",
    MUTATIONS_DEFAULT_HANDLE_ERRORS=False,
    MAP_AUTO_ID_AS_GLOBAL_ID=False,
)


def strawberry_django_settings() -> StrawberryDjangoSettings:
    """Get strawberry django settings.

    Return the dictionary from `settings.STRAWBERRY_DJANGO`, with defaults
    for missing keys.

    Preferred to direct access for the type hints and defaults.
    """
    defaults = DEFAULT_DJANGO_SETTINGS
    return cast(
        StrawberryDjangoSettings,
        {**defaults, **getattr(settings, "STRAWBERRY_DJANGO", {})},
    )
