from django.db import models
from model_utils.managers import InheritanceManager


class Project(models.Model):
    topic = models.CharField(max_length=30)
    dependencies = models.ManyToManyField(
        "self", symmetrical=False, related_name="dependants", blank=True
    )

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


class SoftwareProject(Project):
    repository = models.CharField(max_length=255)


class EngineeringProject(Project):
    lead_engineer = models.CharField(max_length=255)
