import pytest
from django.contrib import auth as django_auth


UserModel = django_auth.get_user_model()


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


@pytest.fixture
def user(db, group, tag):
    user = UserModel.objects.create_user(username="user", password="password")
    return user
