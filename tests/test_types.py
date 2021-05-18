import strawberry
import strawberry_django
from .models import User
from .types import Fruit
from . import utils

def test_type_instance():
    @strawberry_django.type(User, fields=['id', 'name'])
    class UserType:
        pass
    user = UserType(1, 'user')
    assert user.id == 1
    assert user.name == 'user'


def test_input_instance():
    @strawberry_django.input(User, fields=['id', 'name'])
    class InputType:
        pass
    user = InputType(1, 'user')
    assert user.id == 1
    assert user.name == 'user'
