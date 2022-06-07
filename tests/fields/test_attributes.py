from django.db import models
from strawberry import auto

import strawberry_django


class FieldAttributeModel(models.Model):
    field = models.CharField(max_length=50)


def test_default_django_name():
    @strawberry_django.type(FieldAttributeModel)
    class Type:
        field: auto
        field2 = strawberry_django.field(field_name="field")

    assert [(f.name, f.django_name) for f in Type._type_definition.fields] == [
        ("field", "field"),
        ("field2", "field"),
    ]
