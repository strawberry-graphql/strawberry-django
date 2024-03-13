# Filtering

It is possible to define filters for Django types, which will
be converted into `.filter(...)` queries for the ORM:

```{.python title=types.py}
import strawberry_django
from strawberry import auto

@strawberry_django.filter(models.Fruit)
class FruitFilter:
    id: auto
    name: auto

@strawberry_django.type(models.Fruit, filters=FruitFilter)
class Fruit:
    ...
```

The code above would generate following schema:

```{.graphql title=schema.graphql}
input FruitFilter {
  id: ID
  name: String
  AND: FruitFilter
  OR: FruitFilter
  NOT: FruitFilter
}
```

!!! tip

    If you are using the [relay integration](relay.md) and working with types inheriting
    from `relay.Node` and `GlobalID` for identifying objects, you might want to set
    `MAP_AUTO_ID_AS_GLOBAL_ID=True` in your [strawberry django settings](../settings)
    to make sure `auto` fields gets mapped to `GlobalID` on types and filters.

## Lookups

Lookups can be added to all fields with `lookups=True`, which will
add more options to resolve each type. For example:

```{.python title=types.py}
@strawberry_django.filter(models.Fruit, lookups=True)
class FruitFilter:
    id: auto
    name: auto
```

The code above would generate the following schema:

```{.graphql title=schema.graphql}
input StrFilterLookup {
  exact: String
  iExact: String
  contains: String
  iContains: String
  inList: [String!]
  gt: String
  gte: String
  lt: String
  lte: String
  startsWith: String
  iStartsWith: String
  endsWith: String
  iEndsWith: String
  range: [String!]
  isNull: Boolean
  regex: String
  iRegex: String
  nExact: String
  nIExact: String
  nContains: String
  nIContains: String
  nInList: [String!]
  nGt: String
  nGte: String
  nLt: String
  nLte: String
  nStartsWith: String
  nIStartsWith: String
  nEndsWith: String
  nIEndsWith: String
  nRange: [String!]
  nIsNull: Boolean
  nRegex: String
  nIRegex: String
}

input IDFilterLookup {
  exact: String
  iExact: String
  contains: String
  iContains: String
  inList: [String!]
  gt: String
  gte: String
  lt: String
  lte: String
  startsWith: String
  iStartsWith: String
  endsWith: String
  iEndsWith: String
  range: [String!]
  isNull: Boolean
  regex: String
  iRegex: String
  nExact: String
  nIExact: String
  nContains: String
  nIContains: String
  nInList: [String!]
  nGt: String
  nGte: String
  nLt: String
  nLte: String
  nStartsWith: String
  nIStartsWith: String
  nEndsWith: String
  nIEndsWith: String
  nRange: [String!]
  nIsNull: Boolean
  nRegex: String
  nIRegex: String
}

input FruitFilter {
  id: IDFilterLookup
  name: StrFilterLookup
  AND: FruitFilter
  OR: FruitFilter
  NOT: FruitFilter
}
```

Single-field lookup can be annotated with the `FilterLookup` generic type.

```{.python title=types.py}
from strawberry_django.filters import FilterLookup

@strawberry_django.filter(models.Fruit)
class FruitFilter:
    name: FilterLookup[str]
```

## Filtering over relationships

```{.python title=types.py}
@strawberry_django.filter(models.Fruit)
class FruitFilter:
    id: auto
    name: auto
    color: "ColorFilter"

@strawberry_django.filter(models.Color)
class ColorFilter:
    id: auto
    name: auto
```

The code above would generate following schema:

```{.graphql title=schema.graphql}
input ColorFilter {
  id: ID
  name: String
  AND: ColorFilter
  OR: ColorFilter
  NOT: ColorFilter
}

input FruitFilter {
  id: ID
  name: String
  color: ColorFilter
  AND: FruitFilter
  OR: FruitFilter
  NOT: FruitFilter
}
```

## Custom filters and overriding default filtering methods

You can define custom filter methods and override default filter methods by defining your own resolver.

```{.python title=types.py}
@strawberry_django.filter(models.Fruit)
class FruitFilter:
    is_banana: bool | None

    def filter_is_banana(self, queryset):
        if self.is_banana in (None, strawberry.UNSET):
            return queryset

        if self.is_banana:
            queryset = queryset.filter(name='banana')
        else:
            queryset = queryset.exclude(name='banana')

        return queryset
```

## Custom filter expressions with Q

You can also define complex custom expression and overriding default filter method with `q_{field_name}` resolver

```{.python title=types.py}
from django.db.models import Q

@strawberry_django.filter(models.Fruit)
class FruitFilter:
    is_banana: bool | None

    def q_is_banana(self, value: bool | None) -> Q:
        result = Q()
        if self.is_banana in (None, strawberry.UNSET):
            return result

        if self.is_banana:
            result = Q(name="banana")
        else:
            result = ~Q(name="banana")

        return result
```

If you define custom methods `filter_` and `q_` both

only `filter_` works.

```{.python title=types.py}
@strawberry_django.filter(models.Fruit)
class FruitFilter:
    is_banana: bool | None

    # WORK (O)
    def filter_is_banana(self, queryset) -> QuerySet:
        return queryset.filter(name="banana")

    # NOT WORK (X)
    def q_is_banana(self, queryset) -> Q:
        return Q(name="banana")
```

!!! note

    `filter_{field_name}` custom filter not works with `AND`, `OR`, `NOT` nested filters
    but `q_{field_name}` filter is works

## Overriding the default `filter` method

For overriding the default filter logic you can provide the filter method.
Note that this completely disables the default filtering, which means your custom
method is responsible for handling _all_ filter-related operations.

```{.python title=types.py}
@strawberry_django.filter(models.Fruit)
class FruitFilter:
    is_apple: bool | None

    def filter(self, queryset):
        if self.is_apple:
            return queryset.filter(name='apple')
        return queryset.exclude(name='apple')
```

## Adding filters to types

All fields and CUD mutations inherit filters from the underlying type by default.
So, if you have a field like this:

```{.python title=types.py}
@strawberry_django.type(models.Fruit, filters=FruitFilter)
class Fruit:
    ...

@strawberry.type
class Query:
    fruits: list[Fruit] = strawberry_django.field()
```

The `fruits` field will inherit the `filters` of the type in the same way as
if it was passed to the field.

## Adding filters directly into a field

Filters added into a field override the default filters of this type.

```{.python title=schema.py}
@strawberry.type
class Query:
    fruits: list[Fruit] = strawberry_django.field(filters=FruitFilter)
```
