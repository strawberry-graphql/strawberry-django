from django.db import models
from polymorphic.models import PolymorphicModel


class Company(models.Model):
    name = models.CharField(max_length=100)


class Project(PolymorphicModel):
    company = models.ForeignKey(
        Company,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="projects",
    )
    topic = models.CharField(max_length=30)


class ArtProject(Project):
    artist = models.CharField(max_length=30)
    art_style = models.CharField(max_length=30)


class ResearchProject(Project):
    supervisor = models.CharField(max_length=30)
    research_notes = models.TextField()
