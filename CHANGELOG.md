# Changelog

## v0.3rc1

This release adds couple of new features and contains few improvements. This also cleans deprecated API like `fields` parameter from `straberry.django.type`, `TypeRegister` and few other items which have been deprecated in v0.2.0.

New features
* add user registeration mutation (#45, @NeoLight1010)
* add permissions to django mutations (#53, @wellzenon)

Improvements
* fix detecting `auto` annotations when postponed evaluation is used (#73, @illia-v)
* updated the way event loop is detected in `is_async` (#72, @g-as)
* fix return type of field (#64)

Fixes
* fix a bug related to creating users with unhashed passwords (#62, @illia-v)
* fix filtering in `get_queryset` of types with enabled pagination (#60, @illia-v)

Cleanup
* Clean deprecated API (#69)


## v0.2.5

This release adds support for latest `strawberry-graphql`

Depencies
* update minimum required `strawberry-graphql` to v0.69.0


## v0.2.4

Depencies
* Use `strawberry-graphql` earlier than v0.69, which introduced many backward incompatible changes.


## v0.2.3

Improvements
* fix error moessage of NotImplementedError exception (@star2000)
* remove pk argument on model relations (#40, @g-as)

Fixes
* fix breaking changes in `strawberry-graphql` (#42)

Depencies
* update minimum required `strawberry-graphql` to v0.68.2


## v0.2.2

New features
* add `strawberry.django.mutation` type
* add support for model properties and methods
* add support for `strawberry.django` namespace

Improvements
* improve error message of FieldDoesNotExist exception, list all available fields
* update README.md examples to use django namespace
* integrate to `strawberry-graphql` v0.64.4

Depencies
* update minimum required `strawberry-graphql` to v0.64.4


## v0.2.1

Fixes
* fix relation and reverse relation field name resolution (#32)


## v0.2.0

This release adds new class oriented API where all fields are defined in class body. This release also adds basic support for filtering, ordering and pagination. See more information about new API from docs folder.

Example above shows how the new API looks like.

```python
import strawberry_django
from strawberry_django import auto
from . import models

@strawberry_django.type(models.Color)
class Color:
    name: auto

@strawberry_django.type(models.Fruit)
class Fruit:
    name: auto
    color: Color
```

Old API is deprecated and it will removed in v0.3. The biggest breaking change is `fields` parameter which is deprecated. `TypeRegister` is not used anymore in new API. Types and relationships are annotated and defined directly in class body of output and input types.


## v0.1.5

Bug fixes:
* fix m2m relationship setting (#28)


## v0.1.4

Fix the AttributeError in the projects which do not have django-filter package installed.


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
