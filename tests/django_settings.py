from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models.manager import BaseManager
from django.db.models.query import QuerySet

for cls in [QuerySet, BaseManager, models.ForeignKey, models.ManyToManyField]:
    if not hasattr(cls, "__class_getitem__"):
        cls.__class_getitem__ = classmethod(  # type: ignore
            lambda cls, *args, **kwargs: cls,
        )

DEBUG = True
SECRET_KEY = 1
USE_TZ = True
TIME_ZONE = "UTC"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "guardian",
    "debug_toolbar",
    "strawberry_django",
]

STATIC_URL = "/static/"

ROOT_URLCONF = "tests.urls"


AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
)

ANONYMOUS_USER_NAME = None


MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "strawberry_django.middlewares.debug_toolbar.DebugToolbarMiddleware",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 2,
        },
    },
]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(levelname)s %(message)s"},
    },
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "django.db.backends": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "strawberry.execution": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}

try:
    from django.contrib.gis.db import models

    assert models  # ruff

    DATABASES["default"]["ENGINE"] = "django.contrib.gis.db.backends.spatialite"
    INSTALLED_APPS.append("django.contrib.gis")

    GEOS_IMPORTED = True

except ImproperlyConfigured:
    GEOS_IMPORTED = False


INSTALLED_APPS.extend(
    [
        "tests",
        "tests.projects",
        "tests.polymorphism",
        "tests.polymorphism_relay",
        "tests.polymorphism_custom",
        "tests.polymorphism_inheritancemanager",
        "tests.polymorphism_inheritancemanager_relay",
    ],
)
