import strawberry

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension
from strawberry_django.relay import DjangoListConnection

from .models import (
    AndroidProject,
    AppProject,
    ArtProject,
    ArtProjectNote,
    ArtProjectNoteDetails,
    Company,
    EngineeringProject,
    IOSProject,
    Project,
    ProjectNote,
    ResearchProject,
    SoftwareProject,
    TechnicalProject,
)


@strawberry_django.interface(Project)
class ProjectType(strawberry.relay.Node):
    topic: strawberry.auto
    notes: DjangoListConnection["ProjectNoteType"] = strawberry_django.connection()

    @strawberry_django.field(only=("topic",))
    def topic_upper(self) -> str:
        return self.topic.upper()


@strawberry_django.type(ProjectNote)
class ProjectNoteType(strawberry.relay.Node):
    project: ProjectType
    title: strawberry.auto


@strawberry_django.type(ArtProject)
class ArtProjectType(ProjectType):
    artist: strawberry.auto
    art_style_upper: strawberry.auto

    art_notes: DjangoListConnection["ArtProjectNoteType"] = (
        strawberry_django.connection()
    )

    @strawberry_django.field(only=("artist",))
    def artist_upper(self) -> str:
        return self.artist.upper()


@strawberry_django.type(ArtProjectNote)
class ArtProjectNoteType(strawberry.relay.Node):
    art_project: "ArtProjectType"
    title: strawberry.auto

    details: DjangoListConnection["ArtProjectNoteDetailsType"] = (
        strawberry_django.connection()
    )


@strawberry_django.type(ArtProjectNoteDetails)
class ArtProjectNoteDetailsType(strawberry.relay.Node):
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


@strawberry_django.type(Company)
class CompanyType(strawberry.relay.Node):
    name: strawberry.auto
    projects: DjangoListConnection[ProjectType] = strawberry_django.connection()
    main_project: ProjectType | None


@strawberry.type
class Query:
    companies: DjangoListConnection[CompanyType] = strawberry_django.connection()
    projects: DjangoListConnection[ProjectType] = strawberry_django.connection()


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
