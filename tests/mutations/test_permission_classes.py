import pytest
import strawberry
from strawberry.permission import BasePermission

from strawberry_django import mutations
from tests import utils
from tests.types import Fruit, FruitInput, FruitPartialInput


class PermissionClass(BasePermission):
    message = "Permission Denied"

    def has_permission(self, source, info, **kwargs):
        return False


@strawberry.type
class Mutation:
    create_fruits: list[Fruit] = mutations.create(
        FruitInput,
        permission_classes=[PermissionClass],
    )
    update_fruits: list[Fruit] = mutations.update(
        FruitPartialInput,
        permission_classes=[PermissionClass],
    )
    delete_fruits: list[Fruit] = mutations.delete(permission_classes=[PermissionClass])


@pytest.fixture
def mutation(db):
    return utils.generate_query(mutation=Mutation)


def test_create(mutation):
    result = mutation('{ createFruits(data: { name: "strawberry" }) { id name } }')
    assert "Permission Denied" in str(result.errors)


def test_update(mutation):
    result = mutation('{ updateFruits(data: { name: "strawberry" }) { id name } }')
    assert "Permission Denied" in str(result.errors)


def test_delete(mutation):
    result = mutation("{ deleteFruits { id name } }")
    assert "Permission Denied" in str(result.errors)
