import strawberry
from strawberry.relay import ListConnection

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension

from .models import ArtProject, Project, ResearchProject


@strawberry_django.interface(Project)
class ProjectType(strawberry.relay.Node):
    topic: strawberry.auto


@strawberry_django.type(ArtProject)
class ArtProjectType(ProjectType):
    artist: strawberry.auto


@strawberry_django.type(ResearchProject)
class ResearchProjectType(ProjectType):
    supervisor: strawberry.auto


@strawberry.type
class Query:
    projects: ListConnection[ProjectType] = strawberry_django.connection()


schema = strawberry.Schema(
    query=Query,
    types=[ArtProjectType, ResearchProjectType],
    extensions=[DjangoOptimizerExtension],
)
