from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=100)
    main_project = models.ForeignKey(
        "Project", null=True, blank=True, on_delete=models.CASCADE
    )

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
    artist = models.CharField(max_length=30, blank=True)
    supervisor = models.CharField(max_length=30, blank=True)
    research_notes = models.TextField(blank=True)

    class Meta:
        constraints = (
            models.CheckConstraint(
                check=(models.Q(artist="") | models.Q(supervisor=""))
                & (~models.Q(topic="") | ~models.Q(topic="")),
                name="artist_xor_supervisor",
            ),
        )
