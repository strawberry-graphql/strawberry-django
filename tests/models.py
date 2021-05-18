from django.db import models

class Fruit(models.Model):
    name = models.CharField(max_length=20)
    color = models.ForeignKey('Color', null=True, related_name='fruits', on_delete=models.CASCADE)
    types = models.ManyToManyField('FruitType', related_name='fruits')

class Color(models.Model):
    name = models.CharField(max_length=20)

class FruitType(models.Model):
    name = models.CharField(max_length=20)

# TODO: remove later
from .legacy.models import *
