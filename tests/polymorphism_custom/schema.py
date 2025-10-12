from typing import Any

import strawberry
from graphql import GraphQLAbstractType, GraphQLResolveInfo
from strawberry import Info
from strawberry.relay import Node

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.pagination import OffsetPaginated
from strawberry_django.relay import DjangoListConnection

from .models import Company, Project


@strawberry_django.interface(Project)
class ProjectType(Node):
    topic: strawberry.auto

    @classmethod
    def resolve_type(
        cls, value: Any, info: GraphQLResolveInfo, parent_type: GraphQLAbstractType
    ) -> str:
        if not isinstance(value, Project):
            raise TypeError
        if value.artist:
            return "ArtProjectType"
        if value.supervisor:
            return "ResearchProjectType"
        raise TypeError

    @classmethod
    def get_queryset(cls, qs, info: Info):
        return qs


@strawberry_django.type(Project)
class ArtProjectType(ProjectType):
    artist: strawberry.auto


@strawberry_django.type(Project)
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
    projects_connection: DjangoListConnection[ProjectType] = (
        strawberry_django.connection()
    )


schema = strawberry.Schema(
    query=Query,
    types=[ArtProjectType, ResearchProjectType],
    extensions=[DjangoOptimizerExtension],
)
