import strawberry
from django.db.models import Case, Q, Value, When
from strawberry import Info
from strawberry.relay import Node

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.pagination import OffsetPaginated
from strawberry_django.relay import ListConnectionWithTotalCount

from .models import Company, CustomPolyProject


@strawberry_django.interface(CustomPolyProject)
class ProjectType(Node):
    topic: strawberry.auto

    @classmethod
    def get_queryset(cls, qs, info: Info):
        # Graphql assumes the __typename would be affected by private name mangling
        # Therefor we have to prefix with _CustomPolyProject
        return qs.annotate(**{
            f"_{qs.model._meta.object_name}__typename": Case(
                When(~Q(artist=""), then=Value("ArtProjectType")),
                When(~Q(supervisor=""), then=Value("ResearchProjectType")),
            )
        })


@strawberry_django.type(CustomPolyProject)
class ArtProjectType(ProjectType):
    artist: strawberry.auto


@strawberry_django.type(CustomPolyProject)
class ResearchProjectType(ProjectType):
    supervisor: strawberry.auto


@strawberry_django.type(Company)
class CompanyType:
    name: strawberry.auto
    main_project: ProjectType | None
    projects: list[ProjectType]


@strawberry.type
class Query:
    companies: list[CompanyType] = strawberry_django.field()
    projects: list[ProjectType] = strawberry_django.field()
    projects_paginated: list[ProjectType] = strawberry_django.field(pagination=True)
    projects_offset_paginated: OffsetPaginated[ProjectType] = (
        strawberry_django.offset_paginated()
    )
    projects_connection: ListConnectionWithTotalCount[ProjectType] = (
        strawberry_django.connection()
    )


schema = strawberry.Schema(
    query=Query,
    types=[ArtProjectType, ResearchProjectType],
    extensions=[DjangoOptimizerExtension],
)
