# Django Model Types

Django Models can easily be converted in Strawberry Types with the `@strawberry_django.type` decorator

```python
import strawberry

@strawberry.django.type(models.Fruit)
class Fruit:
    ...
```

## Fields

By default, no fields are implemented on the new type. For details on adding fields,
see the [Fields](fields.md) documentation.

## Queryset setup

By default, a Strawberry Django type will pull data from the default manager for it's Django Model.
You can change this behavior by implementing a `get_queryset` method on the type.

```python
@strawberry.django.type(models.Fruit)
class Berry:

    def get_queryset(self, queryset, info):
        return queryset.filter(name__contains="berry")
```

The `get_queryset` method is given a Queryset to filter and
a Strawberry `Info` object, containing details about the request.

You can use the `info` parameter to limit access to items.

```python
@strawberry.django.type(models.Fruit)
class Berry:

    def get_queryset(self, queryset, info):
        if info.context['request'].user.is_staff:
            return queryset.filter(
                name__contains="berry",
            )
        return queryset.filter(
            name__contains="berry",
            is_top_secret=False,
        )
```
