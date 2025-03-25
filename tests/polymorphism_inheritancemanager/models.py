from django.db import models
from model_utils.managers import InheritanceManager


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


class ArtProject(Project):
    artist = models.CharField(max_length=30)
    art_style = models.CharField(max_length=30)


class ResearchProject(Project):
    supervisor = models.CharField(max_length=30)
    research_notes = models.TextField()


# This model exists, but there is no corresponding GraphQL type on purpose.
# This is used in tests to make sure that this project is not selected
class ConstructionProject(Project):
    building_type = models.CharField(max_length=30)
