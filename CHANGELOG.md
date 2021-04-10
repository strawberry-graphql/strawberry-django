# Changelog

## v0.1.3

Add support for django-filter. Now it is possible to convert FilterSet class to input type and apply filters to queryset following way.

```python
@strawberry_django.filter
class UserFilter(django_filters.FilterSet):
    class Meta:
        model = models.User
        fields = ["id", "name"]

def resolver(filters: UserFilter):
    queryset = models.User.objects.all()
    return strawberry_django.filters.apply(filters, queryset)
```

## v0.1.2

Changes:
* rename `is_update` parameter to `partial` in `strawberry_django.input`. Old parameter`is_update` has been deprecated and it will be removed in v0.2.
* update minimum supported `strawberry-graphql` version to v0.53
* fix example Django App
* add LICENSE file
* internal code cleanup

## v0.1.1

This release fixes
* type and default value overriding (#14)
* foreign key handling in partial update (#16)

## v0.1.0

First release
