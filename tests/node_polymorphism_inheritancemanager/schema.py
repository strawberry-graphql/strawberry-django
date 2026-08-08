import strawberry
from strawberry.relay import Node

import strawberry_django
from strawberry_django import ListInput, NodeInput
from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.relay import DjangoListConnection

from .models import (
    ArtProject,
    EngineeringProject,
    Project,
    ResearchProject,
    SoftwareProject,
)


@strawberry_django.interface(Project)
class ProjectType(Node):
    topic: strawberry.auto
    dependencies: DjangoListConnection["ProjectType"] = strawberry_django.connection()
    dependants: DjangoListConnection["ProjectType"] = strawberry_django.connection()


@strawberry_django.partial(Project)
class ProjectInputPartial(NodeInput):
    topic: strawberry.auto = strawberry_django.field()
    dependencies: ListInput[NodeInput] | None = strawberry_django.field()
    dependants: ListInput[NodeInput] | None = strawberry_django.field()


@strawberry_django.type(ArtProject)
class ArtProjectType(ProjectType):
    artist: strawberry.auto
    art_style: strawberry.auto


@strawberry_django.type(ResearchProject)
class ResearchProjectType(ProjectType):
    supervisor: strawberry.auto


@strawberry_django.type(SoftwareProject)
class SoftwareProjectType(ProjectType):
    repository: strawberry.auto


@strawberry_django.type(EngineeringProject)
class EngineeringProjectType(ProjectType):
    lead_engineer: strawberry.auto


@strawberry.type
class Query:
    node: Node = strawberry.relay.node()
    projects: DjangoListConnection[ProjectType] = strawberry_django.field()


@strawberry.type
class Mutation:
    update_art_project: ArtProjectType = strawberry_django.mutations.update(
        ProjectInputPartial
    )


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    types=[
        ArtProjectType,
        ResearchProjectType,
        EngineeringProjectType,
        SoftwareProjectType,
    ],
    extensions=[DjangoOptimizerExtension],
)
