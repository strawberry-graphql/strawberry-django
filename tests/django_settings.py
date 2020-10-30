SECRET_KEY = 1

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:"
    }
}

INSTALLED_APPS = [
    'strawberry_django',
    'tests.app'
]
