import pytest
import strawberry_django
from django.db import models
import django_filters


class Related(models.Model):
    pass


class FilterModel(models.Model):
    reverse_related = models.ForeignKey(Related, on_delete=models.CASCADE)
    one_related = models.OneToOneField(Related, on_delete=models.CASCADE)
    many_related = models.ManyToManyField(Related)
    boolean = models.BooleanField()
    char = models.CharField(max_length=50)
    date = models.DateField()
    date_time = models.DateTimeField()
    decimal = models.DecimalField(decimal_places=2)
    float = models.FloatField()
    integer = models.IntegerField()
    time = models.TimeField()
    uuid = models.UUIDField()


@strawberry_django.filter
class Filter(django_filters.FilterSet):
    class Meta:
        model = FilterModel
        exclude = ()


@pytest.mark.django_db
def test_should_accept_string_formatted_inputs():
    qs = FilterModel.objects.all()
    related = Related.objects.create()

    # Should accept string formatted inputs
    filter_instance = Filter(**{
        "reverse_related": f"{related.pk}",
        "one_related": f"{related.pk}",
        "many_related": [related.pk],
        "boolean": "true",
        "char": "Some Text",
        "date": "2021-01-01",
        "date_time": "2021-01-01T00:09:00",
        "decimal": "1.01",
        "float": "1.239058",
        "integer": "5231",
        "time": "00:09:00",
        "uuid": "6c9d3505-93c2-4d6c-af70-7a1b46a8bcb9",
    })
    strawberry_django.apply_filter(filter_instance, qs)


@pytest.mark.django_db
def test_should_accept_native_inputs():
    qs = FilterModel.objects.all()
    related = Related.objects.create()

    filter_instance = Filter(**{
        "reverse_related": related.pk,
        "one_related": related.pk,
        "boolean": True,
        "decimal": 1.01,
        "float": 1.239058,
        "integer": 5231,
    })
    strawberry_django.apply_filter(filter_instance, qs)


@pytest.mark.django_db
def test_should_raise_filterset_error_for_invalid_input():
    qs = FilterModel.objects.all()

    # Should raise for invalid field
    filter_instance = Filter(**{
        "date_time": "2021-25-29T00:09:00",
    })
    with pytest.raises(strawberry_django.FilterSetError):
        strawberry_django.apply_filter(filter_instance, qs)
