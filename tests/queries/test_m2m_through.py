import strawberry
from django.db import models
from strawberry import auto

import strawberry_django


class MemberModel(models.Model):
    name = models.CharField(max_length=50)


class ProjectModel(models.Model):
    name = models.CharField(max_length=50)
    members = models.ManyToManyField(MemberModel, through="MembershipModel")


class MembershipModel(models.Model):
    project = models.ForeignKey(ProjectModel, on_delete=models.CASCADE)
    member = models.ForeignKey(MemberModel, on_delete=models.CASCADE)


@strawberry_django.type(ProjectModel)
class Project:
    name: auto
    membership: list["Membership"] = strawberry_django.field(
        field_name="membershipmodel_set",
    )


@strawberry_django.type(MemberModel)
class Member:
    name: auto
    membership: list["Membership"] = strawberry_django.field(
        field_name="membershipmodel_set",
    )


@strawberry_django.type(MembershipModel)
class Membership:
    project: Project
    member: Member


@strawberry.type
class Query:
    projects: list[Project] | None = strawberry_django.field()


schema = strawberry.Schema(query=Query)


def test_query(db):
    project = ProjectModel.objects.create(name="my project")
    member = MemberModel.objects.create(name="my member")
    MembershipModel.objects.create(project=project, member=member)

    result = schema.execute_sync("{ projects { membership { member { name } } } }")
    assert not result.errors
    assert result.data == {
        "projects": [
            {
                "membership": [
                    {
                        "member": {"name": "my member"},
                    },
                ],
            },
        ],
    }
