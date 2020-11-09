from django.db import models

class User(models.Model):
    name = models.CharField(max_length=50)
    age = models.IntegerField(default=10)
    groups = models.ManyToManyField('Group', related_name='users', related_query_name='user')

class Group(models.Model):
    name = models.CharField(max_length=50)
    admin = models.ForeignKey(User, related_name='admin_groups', on_delete=models.SET_NULL)

class DataModel(models.Model):
    boolean = models.BooleanField()
    char = models.CharField(max_length=50)
    integer = models.IntegerField()
    text = models.TextField()
    mandatory = models.CharField(max_length=50)
    optional = models.IntegerField(blank=True)
    nullable = models.IntegerField(null=True)
    hasdefault = models.IntegerField(default=1)
    relation = models.ManyToManyField(User)

class UnknownField(models.Field):
    pass

class UnknownFieldModel(models.Model):
    unknown = UnknownField()
