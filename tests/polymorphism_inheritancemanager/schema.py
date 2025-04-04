from typing import Optional

import strawberry

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.pagination import OffsetPaginated

from .models import (
    AndroidProject,
    AppProject,
    ArtProject,
    Company,
    EngineeringProject,
    IOSProject,
    Project,
    ResearchProject,
    SoftwareProject,
    TechnicalProject,
)


@strawberry_django.interface(Project)
class ProjectType:
    topic: strawberry.auto


@strawberry_django.type(ArtProject)
class ArtProjectType(ProjectType):
    artist: strawberry.auto


@strawberry_django.type(ResearchProject)
class ResearchProjectType(ProjectType):
    supervisor: strawberry.auto


@strawberry_django.interface(TechnicalProject)
class TechnicalProjectType(ProjectType):
    timeline: strawberry.auto


@strawberry_django.type(SoftwareProject)
class SoftwareProjectType(TechnicalProjectType):
    repository: strawberry.auto


@strawberry_django.type(EngineeringProject)
class EngineeringProjectType(TechnicalProjectType):
    lead_engineer: strawberry.auto


@strawberry_django.interface(AppProject)
class AppProjectType(TechnicalProjectType):
    repository: strawberry.auto


@strawberry_django.type(AndroidProject)
class AndroidProjectType(AppProjectType):
    android_version: strawberry.auto


@strawberry_django.type(IOSProject)
class IOSProjectType(AppProjectType):
    ios_version: strawberry.auto


@strawberry_django.type(Company)
class CompanyType:
    name: strawberry.auto
    projects: list[ProjectType]
    main_project: Optional[ProjectType]


@strawberry.type
class Query:
    companies: list[CompanyType] = strawberry_django.field()
    projects: list[ProjectType] = strawberry_django.field()
    projects_paginated: list[ProjectType] = strawberry_django.field(pagination=True)
    projects_offset_paginated: OffsetPaginated[ProjectType] = (
        strawberry_django.offset_paginated()
    )


schema = strawberry.Schema(
    query=Query,
    types=[
        ArtProjectType,
        ResearchProjectType,
        TechnicalProjectType,
        EngineeringProjectType,
        SoftwareProjectType,
        AppProjectType,
        IOSProjectType,
        AndroidProjectType,
    ],
    extensions=[DjangoOptimizerExtension],
)
