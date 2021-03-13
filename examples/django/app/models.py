from django.db import models

class User(models.Model):
    name = models.CharField(max_length=50)
    groups = models.ManyToManyField('Group', related_name='users')

class Group(models.Model):
    name = models.CharField(max_length=50)
