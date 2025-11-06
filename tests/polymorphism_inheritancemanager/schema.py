import strawberry

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.pagination import OffsetPaginated

from .models import (
    AndroidProject,
    AppProject,
    ArtProject,
    ArtProjectNote,
    ArtProjectNoteDetails,
    Company,
    CompanyProjectLink,
    EngineeringProject,
    IOSProject,
    Project,
    ProjectNote,
    ResearchProject,
    SoftwareProject,
    TechnicalProject,
)


@strawberry_django.interface(Project)
class ProjectType:
    topic: strawberry.auto
    notes: list["ProjectNoteType"] = strawberry_django.field()

    @strawberry_django.field(only=("topic",))
    def topic_upper(self) -> str:
        return self.topic.upper()


@strawberry_django.type(ProjectNote)
class ProjectNoteType:
    project: ProjectType
    title: strawberry.auto


@strawberry_django.type(ArtProject)
class ArtProjectType(ProjectType):
    artist: strawberry.auto
    art_style_upper: strawberry.auto

    art_notes: list["ArtProjectNoteType"] = strawberry_django.field()

    @strawberry_django.field(only=("artist",))
    def artist_upper(self) -> str:
        return self.artist.upper()


@strawberry_django.type(ArtProjectNote)
class ArtProjectNoteType:
    art_project: "ArtProjectType"
    title: strawberry.auto

    details: list["ArtProjectNoteDetailsType"] = strawberry_django.field()


@strawberry_django.type(ArtProjectNoteDetails)
class ArtProjectNoteDetailsType:
    art_project_note: ArtProjectNoteType
    text: strawberry.auto


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


@strawberry_django.type(CompanyProjectLink)
class CompanyProjectLinkType:
    company: "CompanyType"
    project: ProjectType
    label: strawberry.auto


@strawberry_django.type(Company)
class CompanyType:
    name: strawberry.auto
    projects: list[ProjectType]
    main_project: ProjectType | None
    project_links: list["CompanyProjectLinkType"] = strawberry_django.field()


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
