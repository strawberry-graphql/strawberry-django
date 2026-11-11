from typing import cast

import strawberry
from django.db.models import Prefetch, Value

import strawberry_django
from strawberry_django.optimizer import DjangoOptimizerExtension, optimize
from strawberry_django.pagination import OffsetPaginated

from .models import (
    AndroidProject,
    AppProject,
    ArtProject,
    ArtProjectTag,
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
class ProjectType:
    topic: strawberry.auto
    notes: list["ProjectNoteType"]

    @strawberry_django.field
    def initial_label(self) -> str:
        return self.preexisting_label  # pyright: ignore[reportAttributeAccessIssue]

    @strawberry_django.field(annotate={"optimizer_label": Value("optimized")})
    def computed_label(self) -> str:
        return self.optimizer_label  # pyright: ignore[reportAttributeAccessIssue]

    @strawberry_django.field(only=("topic",))
    def topic_upper(self) -> str:
        return self.topic.upper()


@strawberry_django.type(ArtProject)
class ArtProjectType(ProjectType):
    artist: strawberry.auto
    art_style_upper: strawberry.auto
    tags: list["ArtProjectTagType"]

    @strawberry_django.field(only=("artist",))
    def artist_upper(self) -> str:
        return self.artist.upper()

    @strawberry_django.field(
        prefetch_related=[
            Prefetch(
                "tags",
                queryset=ArtProjectTag.objects.filter(name="included"),
                to_attr="_filtered_tags",
            ),
            "_filtered_tags__project",
        ]
    )
    def filtered_tags_to_attr(self) -> list["ArtProjectTagType"]:
        return self._filtered_tags  # pyright: ignore[reportAttributeAccessIssue]


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


@strawberry_django.type(ProjectNote)
class ProjectNoteType:
    text: strawberry.auto


@strawberry_django.type(ArtProjectTag)
class ArtProjectTagType:
    name: strawberry.auto


@strawberry_django.type(Company)
class CompanyType:
    name: strawberry.auto
    projects: list[ProjectType]
    main_project: ProjectType | None


@strawberry.type
class Query:
    companies: list[CompanyType] = strawberry_django.field()
    projects: list[ProjectType] = strawberry_django.field()

    @strawberry_django.field
    def cloned_projects(self, info: strawberry.Info) -> list[ProjectType]:
        queryset = optimize(Project.objects.all(), info=info)
        return cast("list[ProjectType]", queryset.filter(topic="First"))

    @strawberry_django.field
    def iterated_projects(self, info: strawberry.Info) -> list[ProjectType]:
        queryset = optimize(Project.objects.all(), info=info)
        queryset = queryset.filter(topic__in=["First", "Second"])
        return cast("list[ProjectType]", list(queryset.iterator(chunk_size=2)))

    @strawberry_django.field
    async def aiterated_projects(self, info: strawberry.Info) -> list[ProjectType]:
        queryset = optimize(Project.objects.all(), info=info)
        queryset = queryset.filter(topic__in=["First", "Second"])
        return cast(
            "list[ProjectType]",
            [project async for project in queryset.aiterator(chunk_size=2)],
        )

    @strawberry_django.field
    def filtered_prefetched_projects(self, info: strawberry.Info) -> list[ProjectType]:
        queryset = optimize(Project.objects.all(), info=info)
        queryset = queryset.prefetch_related(None).prefetch_related(
            "artproject__tags__project",
            Prefetch(
                "artproject__tags",
                queryset=ArtProjectTag.objects.filter(name="included"),
            ),
        )
        return cast("list[ProjectType]", list(queryset))

    @strawberry_django.field
    def filtered_prefetched_multilevel_projects(
        self, info: strawberry.Info
    ) -> list[ProjectType]:
        queryset = optimize(Project.objects.all(), info=info)
        queryset = queryset.prefetch_related(None).prefetch_related(
            "appproject__notes",
            Prefetch(
                "appproject__androidproject__notes",
                queryset=ProjectNote.objects.filter(text="included"),
            ),
        )
        return cast("list[ProjectType]", list(queryset))

    @strawberry_django.field
    def annotated_projects(self) -> list[ProjectType]:
        return cast(
            "list[ProjectType]",
            Project.objects.annotate(preexisting_label=Value("initial")),
        )

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
