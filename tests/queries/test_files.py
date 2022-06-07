from typing import List

import pytest
import strawberry
from django.db import models
from strawberry import auto

import strawberry_django

from .. import utils


class FileModel(models.Model):
    file = models.FileField()
    image = models.ImageField()


@strawberry_django.type(FileModel)
class File:
    file: auto
    image: auto


@strawberry.type
class Query:
    files: List[File] = strawberry_django.field()


@pytest.fixture
def query(db):
    return utils.generate_query(Query)


@pytest.fixture
def instance(mocker):
    mocker.patch(
        "django.core.files.images.ImageFile._get_image_dimensions"
    ).return_value = [800, 600]
    mocker.patch("os.stat")().st_size = 10
    return FileModel.objects.create(file="file", image="image")


def test_file(query, instance):
    result = query("{ files { file { name size url } } }")
    assert not result.errors
    assert result.data["files"] == [
        {
            "file": {
                "name": "file",
                "size": 10,
                "url": "/file",
            }
        },
    ]


def test_image(query, instance):
    result = query("{ files { image { name size url width height } } }")
    assert not result.errors
    assert result.data["files"] == [
        {
            "image": {
                "name": "image",
                "size": 10,
                "url": "/image",
                "width": 800,
                "height": 600,
            }
        },
    ]
