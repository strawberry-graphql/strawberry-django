from django.core.exceptions import ImproperlyConfigured


SECRET_KEY = 1

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 2,
        },
    }
]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

try:
    from django.contrib.gis.db import models  # noqa

    DATABASES["default"]["ENGINE"] = "django.contrib.gis.db.backends.spatialite"
    INSTALLED_APPS.append("django.contrib.gis")

    GEOS_IMPORTED = True

except ImproperlyConfigured:
    GEOS_IMPORTED = False


INSTALLED_APPS.append("tests")
