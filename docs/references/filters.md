# Filtering

```python
import strawberry
from strawberry.django import auto

@strawberry.django.filters.filter(models.Fruit)
class FruitFilter:
    id: auto
    name: auto
```

```python
@strawberry.django.type(models.Fruit, filters=FruitFilter)
class Fruit:
    ...
```

Code above generates following schema

```schema
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

Single field lookup can be annotated with `FilterLookup` generic type.

```python
from strawberry.django.filters import FilterLookup

@strawberry.django.filters.filter(models.Fruit)
class FruitFilter:
    name: FilterLookup[str]
```

## Filtering over relationship

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

```python
@strawberry.django.filters.filter(models.Fruit)
class FruitFilter:
    is_banana: bool

    def is_banana(self, queryset):
        if self.is_banana:
            return queryset.filter(name='banana')
        return queryset.exclude(name='banana')
```

## Adding filters to type

All fields and mutations are inheriting filters from type by default.

```python
@strawberry.django.type(models.Fruit, filters=FruitFilter)
class Fruit:
    ...
```

## Adding filters directly into field

Filters added into field is overriding default filters of type.

```python
@strawberry.type
class Query:
    fruit: Fruit = strawberry.django.field(filters=FruitFilter)
```
