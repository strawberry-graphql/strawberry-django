import strawberry
import strawberry_django
from django.db import models


def test_forward_reference():
    global MyBytes

    class ForwardReferenceModel(models.Model):
        string = models.CharField(max_length=50)

    @strawberry_django.type(ForwardReferenceModel, fields=[
        'string',
    ])
    class Type:
        bytes0: 'MyBytes'

    class MyBytes(bytes):
        pass

    assert [(f.name, f.type) for f in Type._type_definition.fields] == [
        ('bytes0', MyBytes),
        ('string', str),
    ]

    del MyBytes
