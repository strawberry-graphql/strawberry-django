import strawberry

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension

from .models import ArtProject, Project, ResearchProject


@strawberry_django.interface(Project)
class ProjectType:
    topic: strawberry.auto


@strawberry_django.type(ArtProject)
class ArtProjectType(ProjectType):
    artist: strawberry.auto


@strawberry_django.type(ResearchProject)
class ResearchProjectType(ProjectType):
    supervisor: strawberry.auto


@strawberry.type
class Query:
    projects: list[ProjectType] = strawberry_django.field()


schema = strawberry.Schema(
    query=Query,
    types=[ArtProjectType, ResearchProjectType],
    extensions=[DjangoOptimizerExtension],
)
