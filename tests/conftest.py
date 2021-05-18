import pytest
import strawberry
import strawberry_django
from . import models, types, utils

@pytest.fixture
def fruits(db):
    fruit_names = ['strawberry', 'raspberry', 'banana']
    fruits = [ models.Fruit.objects.create(name=name) for name in fruit_names ]
    return fruits

@pytest.fixture
def tag(db):
    tag = models.Tag.objects.create(name='tag')
    return tag

@pytest.fixture
def group(db, tag):
    group = models.Group.objects.create(name='group')
    group.tags.add(tag)
    return group

@pytest.fixture
def user(db, group, tag):
    user = models.User.objects.create(name='user', group=group, tag=tag)
    return user

@pytest.fixture
def users(db):
    return [
        models.User.objects.create(name='user1'),
        models.User.objects.create(name='user2'),
        models.User.objects.create(name='user3'),
    ]

@pytest.fixture
def groups(db):
    return [
        models.Group.objects.create(name='group1'),
        models.Group.objects.create(name='group2'),
        models.Group.objects.create(name='group3'),
    ]

@pytest.fixture
def schema():
    Query = strawberry_django.queries(types.User, types.Group, types.Tag)
    schema = strawberry.Schema(query=Query)
    return schema

@pytest.fixture(params=[
    strawberry_django.type,
    strawberry_django.input,
    utils.dataclass,
])
def testtype(request):
    return request.param
