from django.db import models

import strawberry_django
from strawberry_django import auto


def test_forward_reference():
    global MyBytes

    class ForwardReferenceModel(models.Model):
        string = models.CharField(max_length=50)

    @strawberry_django.type(ForwardReferenceModel)
    class Type:
        bytes0: "MyBytes"
        string: auto

    class MyBytes(bytes):
        pass

    assert [(f.name, f.type) for f in Type._type_definition.fields] == [
        ("bytes0", MyBytes),
        ("string", str),
    ]

    del MyBytes
