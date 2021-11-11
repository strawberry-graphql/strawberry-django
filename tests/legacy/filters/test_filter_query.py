from typing import List, Optional

import django_filters
import pytest
import strawberry
from django.db.models import Q
from strawberry.arguments import UNSET

import strawberry_django
from tests import models


@pytest.fixture
def execute():
    group1 = models.Group.objects.create(name="group1")
    tag1 = models.Tag.objects.create(name="tag1")
    tag2 = models.Tag.objects.create(name="tag2")
    models.User.objects.create(name="user1", group=group1, tag=tag1)
    models.User.objects.create(name="user2", tag=tag2)
    models.User.objects.create(name="user3")

    @strawberry_django.filter
    class UserFilter(django_filters.FilterSet):
        name = django_filters.CharFilter(lookup_expr="icontains")
        search = django_filters.CharFilter(method="filter_search")

        def filter_search(self, queryset, name, value):
            return queryset.filter(
                Q(name__icontains=value)
                | Q(group__name__icontains=value)
                | Q(tag__name__icontains=value)
            )

        class Meta:
            model = models.User
            fields = ["name", "search"]

    @strawberry.type
    class Query:
        @strawberry.field
        def user_ids(self, filters: Optional[UserFilter] = UNSET) -> List[int]:
            queryset = models.User.objects.all()
            queryset = strawberry_django.filters.apply(filters, queryset)
            return queryset.order_by("pk").values_list("pk", flat=True)

    schema = strawberry.Schema(query=Query)
    query = """
        query getUserIds ($filters: UserFilter) {
            userIds (filters: $filters)
        }
    """

    def execute(variable_values):
        return schema.execute_sync(query, variable_values=variable_values)

    return execute


@pytest.mark.django_db
def test_passing_no_filter(execute):
    variable_values = {}
    result = execute(variable_values)
    assert result.data
    assert result.data["userIds"] == [1, 2, 3]
    assert not result.errors


@pytest.mark.django_db
def test_passing_empty_filter(execute):
    variable_values = {"filters": {}}
    result = execute(variable_values)
    assert result.data
    assert result.data.get("userIds", None) == [1, 2, 3]
    assert not result.errors


@pytest.mark.django_db
def test_passing_none_filter(execute):
    variable_values = {"filters": None}
    result = execute(variable_values)
    assert result.data
    assert result.data.get("userIds", None) == [1, 2, 3]
    assert not result.errors


@pytest.mark.django_db
def test_lookup_char_filter(execute):
    variable_values = {"filters": {"name": "user1"}}
    result = execute(variable_values)
    assert result.data
    assert result.data.get("userIds", None) == [1]
    assert not result.errors


@pytest.mark.django_db
def test_custom_char_filter(execute):
    variable_values = {"filters": {"search": "tag2"}}
    result = execute(variable_values)
    assert result.data
    assert result.data.get("userIds", None) == [2]
    assert not result.errors

    variable_values = {"filters": {"search": "group1"}}
    result = execute(variable_values)
    assert result.data
    assert result.data.get("userIds", None) == [1]
    assert not result.errors
