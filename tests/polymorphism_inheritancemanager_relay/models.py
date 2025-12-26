from django.db import models
from model_utils.managers import InheritanceManager

from strawberry_django.descriptors import model_property


class Company(models.Model):
    name = models.CharField(max_length=100)
    main_project = models.ForeignKey("Project", on_delete=models.CASCADE, null=True)

    class Meta:
        ordering = ("name",)


class Project(models.Model):
    company = models.ForeignKey(
        Company,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="projects",
    )
    topic = models.CharField(max_length=30)

    base_objects = InheritanceManager()
    objects = InheritanceManager()

    class Meta:
        base_manager_name = "base_objects"


class ProjectNote(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    title = models.CharField(max_length=100)


class ArtProject(Project):
    artist = models.CharField(max_length=30)
    art_style = models.CharField(max_length=30)

    @model_property(only=("art_style",))
    def art_style_upper(self) -> str:
        return self.art_style.upper()


class ArtProjectNote(models.Model):
    art_project = models.ForeignKey(
        ArtProject,
        on_delete=models.CASCADE,
        related_name="art_notes",
    )
    title = models.CharField(max_length=100)


class ArtProjectNoteDetails(models.Model):
    art_project_note = models.ForeignKey(
        ArtProjectNote,
        on_delete=models.CASCADE,
        related_name="details",
    )
    text = models.CharField(max_length=100)


class ResearchProject(Project):
    supervisor = models.CharField(max_length=30)
    research_notes = models.TextField()


class TechnicalProject(Project):
    timeline = models.CharField(max_length=30)

    class Meta:  # pyright: ignore [reportIncompatibleVariableOverride]
        abstract = True


class SoftwareProject(TechnicalProject):
    repository = models.CharField(max_length=255)


class EngineeringProject(TechnicalProject):
    lead_engineer = models.CharField(max_length=255)


class AppProject(TechnicalProject):
    repository = models.CharField(max_length=255)


class AndroidProject(AppProject):
    android_version = models.CharField(max_length=15)


class IOSProject(AppProject):
    ios_version = models.CharField(max_length=15)


class CompanyProjectLink(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="project_links"
    )
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="company_links"
    )
    label = models.CharField(max_length=100, blank=True, default="")
