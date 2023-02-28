from strawberry_django.apps import StrawberryDjangoConfig


def test_app_name() -> None:
    assert StrawberryDjangoConfig.name == "strawberry_django"


def test_verbose_name() -> None:
    assert StrawberryDjangoConfig.verbose_name == "Strawberry django"
