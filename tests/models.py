from typing import TYPE_CHECKING, Optional

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models

from strawberry_django.descriptors import model_property

if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager


def validate_fruit_type(value: str):
    if "rotten" in value:
        raise ValidationError("We do not allow rotten fruits.")


class Fruit(models.Model):
    name = models.CharField(max_length=20)
    color_id: Optional[int]
    color = models.ForeignKey(
        "Color",
        null=True,
        blank=True,
        related_name="fruits",
        on_delete=models.CASCADE,
    )
    types = models.ManyToManyField("FruitType", related_name="fruits")
    sweetness = models.IntegerField(
        default=5,
        help_text="Level of sweetness, from 1 to 10",
    )

    def name_upper(self):
        return self.name.upper()

    @property
    def name_lower(self):
        return self.name.lower()

    @model_property
    def name_length(self) -> int:
        return len(self.name)


class Color(models.Model):
    fruits: "RelatedManager[Fruit]"
    name = models.CharField(max_length=20)


class FruitType(models.Model):
    name = models.CharField(max_length=20, validators=[validate_fruit_type])


class User(models.Model):
    name = models.CharField(max_length=50)
    group_id: Optional[int]
    group = models.ForeignKey(
        "Group",
        null=True,
        blank=True,
        related_name="users",
        on_delete=models.CASCADE,
    )
    tag = models.OneToOneField("Tag", null=True, on_delete=models.CASCADE)

    @property
    def group_prop(self) -> Optional["Group"]:
        return self.group

    def get_group(self) -> Optional["Group"]:
        return self.group


class Group(models.Model):
    users: "RelatedManager[User]"
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
        point = geos_fields.PointField(null=True, blank=True)
        line_string = geos_fields.LineStringField(null=True, blank=True)
        polygon = geos_fields.PolygonField(null=True, blank=True)
        multi_point = geos_fields.MultiPointField(null=True, blank=True)
        multi_line_string = geos_fields.MultiLineStringField(null=True, blank=True)
        multi_polygon = geos_fields.MultiPolygonField(null=True, blank=True)

except ImproperlyConfigured:
    GEOS_IMPORTED = False
