from typing import Any, ClassVar, Generic, List, Type, TypeVar, cast

import factory
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser, Group

from .models import Favorite, Issue, Milestone, Project, Tag

_T = TypeVar("_T")
User = cast(Type[AbstractUser], get_user_model())


class _BaseFactory(Generic[_T], factory.django.DjangoModelFactory):
    Meta: ClassVar[Any]

    @classmethod
    def create(cls, **kwargs) -> _T:
        return super().create(**kwargs)

    @classmethod
    def create_batch(cls, size: int, **kwargs) -> List[_T]:
        return super().create_batch(size, **kwargs)


class GroupFactory(_BaseFactory[Group]):
    class Meta:
        model = Group

    name = factory.Sequence(lambda n: f"Group {n}")


class UserFactory(_BaseFactory["User"]):
    class Meta:
        model = User

    is_active = True
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    username = factory.Sequence(lambda n: f"user-{n}")
    email = factory.Faker("email")
    password = factory.LazyFunction(lambda: make_password("foobar"))


class StaffUserFactory(UserFactory):
    is_staff = True


class SuperuserUserFactory(UserFactory):
    is_superuser = True


class ProjectFactory(_BaseFactory[Project]):
    class Meta:
        model = Project

    name = factory.Sequence(lambda n: f"Project {n}")
    due_date = factory.Faker("future_date")


class MilestoneFactory(_BaseFactory[Milestone]):
    class Meta:
        model = Milestone

    name = factory.Sequence(lambda n: f"Milestone {n}")
    due_date = factory.Faker("future_date")
    project = factory.SubFactory(ProjectFactory)


class FavoriteFactory(_BaseFactory[Favorite]):
    class Meta:
        model = Favorite

    name = factory.Sequence(lambda n: f"Favorite {n}")


class IssueFactory(_BaseFactory[Issue]):
    class Meta:
        model = Issue

    name = factory.Sequence(lambda n: f"Issue {n}")
    kind = factory.Iterator(Issue.Kind)
    milestone = factory.SubFactory(MilestoneFactory)
    priority = factory.Faker("pyint", min_value=0, max_value=5)


class TagFactory(_BaseFactory[Tag]):
    class Meta:
        model = Tag

    name = factory.Sequence(lambda n: f"Tag {n}")
