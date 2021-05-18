# Filtering

```python
import strawberry_django
from strawberry_django import auto

@strawberry_django.filters.filter(models.Fruit)
class FruitFilter:
    id: auto
    name: auto
```

```python
@strawberry_django.type(models.Fruit, filters=FruitFilter)
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
@strawberry_django.filters.filter(models.Fruit, lookups=True)
class FruitFilter:
    id: auto
    name: auto
```

Single field lookup can be annotated with `FilterLookup` generic type.

```python
from strawberry_django.filters import FilterLookup

@strawberry_django.filters.filter(models.Fruit)
class FruitFilter:
    name: FilterLookup[str]
```

## Filtering over relationship

```python
@strawberry_django.filters.filter(models.Fruit)
class FruitFilter:
    id: auto
    name: auto
    colors: 'ColorFilter'

@strawberry_django.filters.filter(models.Color)
class ColorFilter:
    id: auto
    name: auto
    fruits: FruitFilter
```

## Overriding default filtering method

TODO


## Adding filters to type

All fields and mutations are inheriting filters from type by default.

```python
@strawberry_django.type(models.Fruit, filters=FruitFilter)
class Fruit:
    ...
```


## Adding filters directly into field

Filters added into field is overriding default filters of type.

```python
@strawberry.type
class Query:
    fruit: Fruit = strawberry_django.field(filters=FruitFilter)
```
