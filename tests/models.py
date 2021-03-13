from django.db import models

class User(models.Model):
    name = models.CharField(max_length=50)
    group = models.ForeignKey('Group', null=True, related_name='users', on_delete=models.CASCADE)
    tag = models.OneToOneField('Tag', null=True, on_delete=models.CASCADE)

class Group(models.Model):
    name = models.CharField(max_length=50)
    tags = models.ManyToManyField('Tag', null=True, related_name='groups')

class Tag(models.Model):
    name = models.CharField(max_length=50)
