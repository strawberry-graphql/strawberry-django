from django.db import models


class Fruit(models.Model):
    name = models.CharField(max_length=20)
    color = models.ForeignKey("Color", null=True, related_name="fruits", on_delete=models.CASCADE)
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
    group = models.ForeignKey("Group", null=True, related_name="users", on_delete=models.CASCADE)
    tag = models.OneToOneField("Tag", null=True, on_delete=models.CASCADE)


class Group(models.Model):
    name = models.CharField(max_length=50)
    tags = models.ManyToManyField("Tag", null=True, related_name="groups")


class Tag(models.Model):
    name = models.CharField(max_length=50)
