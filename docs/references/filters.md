# Filtering

```python
import strawberry
from strawberry import auto

@strawberry.django.filters.filter(models.Fruit)
class FruitFilter:
    id: auto
    name: auto

@strawberry.django.type(models.Fruit, filters=FruitFilter)
class Fruit:
    ...
```

The code above generates the following schema:

```graphql
input FruitFilter {
  id: ID
  name: String
}
```

## Lookups

Lookups can be added to all fields with `lookups=True`.

```python
@strawberry.django.filters.filter(models.Fruit, lookups=True)
class FruitFilter:
    id: auto
    name: auto
```

Single-field lookup can be annotated with the `FilterLookup` generic type.

```python
from strawberry.django.filters import FilterLookup

@strawberry.django.filters.filter(models.Fruit)
class FruitFilter:
    name: FilterLookup[str]
```

## Filtering over relationships

```python
@strawberry.django.filters.filter(models.Fruit)
class FruitFilter:
    id: auto
    name: auto
    colors: 'ColorFilter'

@strawberry.django.filters.filter(models.Color)
class ColorFilter:
    id: auto
    name: auto
    fruits: FruitFilter
```

## Custom filters and overriding default filtering method

You can define custom filter methods and override default filter methods by defining your own resolver.
Note that this completely disables the default filtering, which means your custom
method is responsible for handling _all_ filter-related operations.

```python
@strawberry.django.filters.filter(models.Fruit)
class FruitFilter:
    is_banana: bool | None

    def filter_is_banana(self, queryset):
        if self.is_banana is None:
            return queryset
        if self.is_banana:
            return queryset.filter(name='banana')
        return queryset.exclude(name='banana')
```

## Adding filters to types

All fields and mutations inherit filters from type by default.

```python
@strawberry.django.type(models.Fruit, filters=FruitFilter)
class Fruit:
    ...
```

## Adding filters directly into a field

Filters added into a field override the default filters of this type.

```python
@strawberry.type
class Query:
    fruit: Fruit = strawberry.django.field(filters=FruitFilter)
```
