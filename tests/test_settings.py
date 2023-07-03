"""Tests for `strawberry_django/settings.py`."""
from django.test import override_settings

from strawberry_django import settings


def test_defaults():
    """Test defaults.

    Test that `strawberry_django_settings()` provides the default settings if they don't
    exist in the Django settings file.
    """
    assert settings.strawberry_django_settings() == settings.DEFAULT_DJANGO_SETTINGS


def test_non_defaults():
    """Test non defaults.

    Test that `strawberry_django_settings()` provides the user's settings if they are
    defined in the Django settings file.
    """
    with override_settings(
        STRAWBERRY_DJANGO=settings.StrawberryDjangoSettings(
            FIELD_DESCRIPTION_FROM_HELP_TEXT=True,
            TYPE_DESCRIPTION_FROM_MODEL_DOCSTRING=True,
            GENERATE_ENUMS_FROM_CHOICES=True,
            MUTATIONS_DEFAULT_ARGUMENT_NAME="id",
            MUTATIONS_DEFAULT_HANDLE_ERRORS=True,
        ),
    ):
        assert (
            settings.strawberry_django_settings()
            == settings.StrawberryDjangoSettings(
                FIELD_DESCRIPTION_FROM_HELP_TEXT=True,
                TYPE_DESCRIPTION_FROM_MODEL_DOCSTRING=True,
                GENERATE_ENUMS_FROM_CHOICES=True,
                MUTATIONS_DEFAULT_ARGUMENT_NAME="id",
                MUTATIONS_DEFAULT_HANDLE_ERRORS=True,
            )
        )
