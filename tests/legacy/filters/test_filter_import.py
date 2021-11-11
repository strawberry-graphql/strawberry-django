import django_filters
import pytest

import strawberry_django
from strawberry_django.legacy.filters import DummyDjangoFilters


@pytest.fixture
def django_filters_mock(mocker):
    return mocker.patch(
        "strawberry_django.legacy.filters.django_filters", DummyDjangoFilters()
    )


def test_filter_with_dummy_filters_raises_error(django_filters_mock):
    with pytest.raises(ModuleNotFoundError):

        @strawberry_django.filter
        class Filter(django_filters.FilterSet):
            pass


def test_apply_filter_with_dummy_filters_raises_error(django_filters_mock):
    class filter_instance:
        filterset_class = "dummy"

    with pytest.raises(ModuleNotFoundError):
        strawberry_django.filters.apply(filter_instance, None)


def test_get_field_type_with_dummy_filters_raises_error(django_filters_mock):
    with pytest.raises(ModuleNotFoundError):
        strawberry_django.filters.get_field_type()


def test_set_field_type_with_dummy_filters_raises_error(django_filters_mock):
    with pytest.raises(ModuleNotFoundError):
        strawberry_django.filters.set_field_type()
