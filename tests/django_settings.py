import django

SECRET_KEY = 1

ENGINE = "django.db.backends.sqlite3"
try:
    raise django.core.exceptions.ImproperlyConfigured
    from django.contrib.gis.db import models as geos_fields

    ENGINE = "django.contrib.gis.db.backends.spatialite"
except django.core.exceptions.ImproperlyConfigured:
    # If gdal is not available, use SQLite Backend
    pass

DATABASES = {
    "default": {
        "ENGINE": ENGINE,
        "NAME": ":memory:",
    }
}

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.gis",
    "tests",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 2,
        },
    }
]
