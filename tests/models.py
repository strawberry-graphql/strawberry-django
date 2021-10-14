from django.db import models


class Fruit(models.Model):
    name = models.CharField(max_length=20)
    color = models.ForeignKey(
        "Color", null=True, related_name="fruits", on_delete=models.CASCADE
    )
    types = models.ManyToManyField("FruitType", related_name="fruits")

    def name_upper(self):
        return self.name.upper()

    @property
    def name_lower(self):
        return self.name.lower()


class Color(models.Model):
    name = models.CharField(max_length=20)


class FruitType(models.Model):
    name = models.CharField(max_length=20)


# TODO: remove later
