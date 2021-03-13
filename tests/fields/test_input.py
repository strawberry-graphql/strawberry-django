import strawberry
import strawberry_django
from django.db import models


class InputFieldsModel(models.Model):
    mandatory = models.IntegerField()
    default = models.IntegerField(default=1)
    blank = models.IntegerField(blank=True)
    null = models.IntegerField(null=True)
    null_boolean = models.NullBooleanField()


def test_input_type():
    @strawberry_django.input(InputFieldsModel)
    class InputType:
        pass

    assert [(f.name, f.type, f.is_optional) for f in InputType._type_definition.fields] == [
        ('id', strawberry.ID, True),
        ('mandatory', int, False),
        ('default', int , True),
        ('blank', int, True),
        ('null', int, True),
        ('nullBoolean', bool, True),
    ]


def test_input_type_for_partial_update():
    @strawberry_django.input(InputFieldsModel, is_update=True)
    class InputType:
        pass

    assert [(f.name, f.type, f.is_optional) for f in InputType._type_definition.fields] == [
        ('id', strawberry.ID, True),
        ('mandatory', int, True),
        ('default', int , True),
        ('blank', int, True),
        ('null', int, True),
        ('nullBoolean', bool, True),
    ]

class InputParentModel(models.Model):
    foreign_key = models.ForeignKey(InputFieldsModel, on_delete=models.CASCADE)
    foreign_key_optional = models.ForeignKey(InputFieldsModel, null=True, on_delete=models.CASCADE)
    many_to_many = models.ManyToManyField(InputFieldsModel)

def test_foreign_key():
    @strawberry_django.input(InputParentModel)
    class InputType:
        pass

    assert [(f.name, f.type or f.child.type, f.is_optional) for f in InputType._type_definition.fields] == [
        ('id', strawberry.ID, True),
        ('foreignKeyId', strawberry.ID, False),
        ('foreignKeyOptionalId', strawberry.ID, True),
        ('manyToManyAdd', strawberry.ID, True),
        ('manyToManySet', strawberry.ID, True),
        ('manyToManyRemove', strawberry.ID, True),
    ]

