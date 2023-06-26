from django.db import models
from strawberry import auto
from strawberry.type import get_object_definition

import strawberry_django


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

    assert [
        (f.name, f.type) for f in get_object_definition(Type, strict=True).fields
    ] == [
        ("bytes0", MyBytes),
        ("string", str),
    ]

    del MyBytes
