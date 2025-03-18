import strawberry
from django.db.models import Case, When, Q, Value
from strawberry import Info
from strawberry.relay import Node

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.pagination import OffsetPaginated
from strawberry_django.relay import ListConnectionWithTotalCount
from .models import Project


@strawberry_django.interface(Project)
class ProjectType(Node):
    topic: strawberry.auto

    @classmethod
    def get_queryset(cls, qs, info: Info):
        # Graphql assumes the __typename would be affected by private name mangling
        # Therefor we have to prefix with _Project
        return qs.annotate(
            _Project__typename=Case(
                When(~Q(artist=''), then=Value('ArtProjectType')),
                When(~Q(supervisor=''), then=Value('ResearchProjectType')),
            )
        )


@strawberry_django.type(Project)
class ArtProjectType(ProjectType):
    artist: strawberry.auto


@strawberry_django.type(Project)
class ResearchProjectType(ProjectType):
    supervisor: strawberry.auto


@strawberry.type
class Query:
    projects: list[ProjectType] = strawberry_django.field()
    projects_paginated: list[ProjectType] = strawberry_django.field(pagination=True)
    projects_offset_paginated: OffsetPaginated[ProjectType] = strawberry_django.offset_paginated()
    projects_connection: ListConnectionWithTotalCount[ProjectType] = strawberry_django.connection()


schema = strawberry.Schema(
    query=Query,
    types=[ArtProjectType, ResearchProjectType],
    extensions=[DjangoOptimizerExtension],
)
