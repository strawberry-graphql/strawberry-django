import django.contrib.auth as django_auth
import pytest

import strawberry_django

from . import models, utils

UserModel = django_auth.get_user_model()


@pytest.fixture
def fruits(db):
    fruit_names = ["strawberry", "raspberry", "banana"]
    fruits = [models.Fruit.objects.create(name=name) for name in fruit_names]
    return fruits


@pytest.fixture
def tag(db):
    tag = models.Tag.objects.create(name="tag")
    return tag


@pytest.fixture
def group(db, tag):
    group = models.Group.objects.create(name="group")
    group.tags.add(tag)
    return group


@pytest.fixture
def user(db, group, tag):
    user = UserModel.objects.create_user(username="user", password="password")
    return user


@pytest.fixture
def users(db):
    return [
        models.User.objects.create(name="user1"),
        models.User.objects.create(name="user2"),
        models.User.objects.create(name="user3"),
    ]


@pytest.fixture
def groups(db):
    return [
        models.Group.objects.create(name="group1"),
        models.Group.objects.create(name="group2"),
        models.Group.objects.create(name="group3"),
    ]


@pytest.fixture(
    params=[
        strawberry_django.type,
        strawberry_django.input,
        utils.dataclass,
    ]
)
def testtype(request):
    return request.param


@pytest.fixture
def context(mocker):
    class Session(dict):
        def cycle_key(self):
            pass

        def flush(self):
            pass

    context = mocker.Mock()
    context.request.session = Session()
    django_auth.logout(context.request)
    return context
