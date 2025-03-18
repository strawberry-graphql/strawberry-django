from django.db import models


class Project(models.Model):
    topic = models.CharField(max_length=30)
    artist = models.CharField(max_length=30, blank=True)
    supervisor = models.CharField(max_length=30, blank=True)

    class Meta:
        constraints = (
            models.CheckConstraint(
                check=(models.Q(artist="") | models.Q(supervisor=""))
                & (~models.Q(topic="") | ~models.Q(topic="")),
                name="artist_xor_supervisor",
            ),
        )
