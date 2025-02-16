from typing import Any, ClassVar, Generic, TypeVar

import factory
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from factory.declarations import Iterator, LazyFunction, Sequence, SubFactory
from factory.faker import Faker

from .models import Favorite, Issue, Milestone, Project, Tag

_T = TypeVar("_T")
User = get_user_model()


class _BaseFactory(factory.django.DjangoModelFactory, Generic[_T]):
    Meta: ClassVar[Any]

    @classmethod
    def create(cls, **kwargs) -> _T:
        return super().create(**kwargs)

    @classmethod
    def create_batch(cls, size: int, **kwargs) -> list[_T]:
        return super().create_batch(size, **kwargs)


class GroupFactory(_BaseFactory[Group]):
    class Meta:
        model = Group

    name = Sequence(lambda n: f"Group {n}")


class UserFactory(_BaseFactory["User"]):
    class Meta:
        model = User

    is_active = True
    first_name = Faker("first_name")
    last_name = Faker("last_name")
    username = Sequence(lambda n: f"user-{n}")
    email = Faker("email")
    password = LazyFunction(lambda: make_password("foobar"))


class StaffUserFactory(UserFactory):
    is_staff = True


class SuperuserUserFactory(UserFactory):
    is_superuser = True


class ProjectFactory(_BaseFactory[Project]):
    class Meta:
        model = Project

    name = Sequence(lambda n: f"Project {n}")
    due_date = Faker("future_date")


class MilestoneFactory(_BaseFactory[Milestone]):
    class Meta:
        model = Milestone

    name = Sequence(lambda n: f"Milestone {n}")
    due_date = Faker("future_date")
    project = SubFactory(ProjectFactory)


class FavoriteFactory(_BaseFactory[Favorite]):
    class Meta:
        model = Favorite

    name = Sequence(lambda n: f"Favorite {n}")


class IssueFactory(_BaseFactory[Issue]):
    class Meta:
        model = Issue

    name = Sequence(lambda n: f"Issue {n}")
    kind = Iterator(Issue.Kind)
    milestone = SubFactory(MilestoneFactory)
    priority = Faker("pyint", min_value=0, max_value=5)


class TagFactory(_BaseFactory[Tag]):
    class Meta:
        model = Tag

    name = Sequence(lambda n: f"Tag {n}")
