import strawberry
from django.db import models
from strawberry import BasePermission, auto

import strawberry_django


class FieldAttributeModel(models.Model):
    field = models.CharField(max_length=50)


def test_default_django_name():
    @strawberry_django.type(FieldAttributeModel)
    class Type:
        field: auto
        field2: auto = strawberry_django.field(field_name="field")

    assert [(f.name, f.django_name) for f in Type._type_definition.fields] == [
        ("field", "field"),
        ("field2", "field"),
    ]


def test_field_permission_classes():
    class TestPermission(BasePermission):
        pass

    @strawberry_django.type(FieldAttributeModel)
    class Type:
        field: auto = strawberry.field(permission_classes=[TestPermission])

        @strawberry.field(permission_classes=[TestPermission])
        def custom_resolved_field(self) -> str:
            return self.field

    assert sorted(
        [(f.name, f.permission_classes) for f in Type._type_definition.fields],
    ) == sorted(
        [
            ("field", [TestPermission]),
            ("custom_resolved_field", [TestPermission]),
        ],
    )
