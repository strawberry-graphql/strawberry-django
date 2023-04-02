from django.core.exceptions import ImproperlyConfigured
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


class User(models.Model):
    name = models.CharField(max_length=50)
    group = models.ForeignKey(
        "Group", null=True, related_name="users", on_delete=models.CASCADE
    )
    tag = models.OneToOneField("Tag", null=True, on_delete=models.CASCADE)

    @property
    def group_prop(self) -> "Group":
        return self.group

    def get_group(self) -> "Group":
        return self.group


class Group(models.Model):
    name = models.CharField(max_length=50)
    tags = models.ManyToManyField("Tag", null=True, related_name="groups")


class Tag(models.Model):
    name = models.CharField(max_length=50)


class Book(models.Model):
    """Model with lots of extra metadata."""

    title = models.CharField(
        max_length=20,
        blank=False,
        null=False,
        help_text="The name by which the book is known.",
    )


try:
    from django.contrib.gis.db import models as geos_fields

    GEOS_IMPORTED = True

    class GeosFieldsModel(models.Model):
        point = geos_fields.PointField(null=True)
        line_string = geos_fields.LineStringField(null=True)
        polygon = geos_fields.PolygonField(null=True)
        multi_point = geos_fields.MultiPointField(null=True)
        multi_line_string = geos_fields.MultiLineStringField(null=True)
        multi_polygon = geos_fields.MultiPolygonField(null=True)

except ImproperlyConfigured:
    GEOS_IMPORTED = False
