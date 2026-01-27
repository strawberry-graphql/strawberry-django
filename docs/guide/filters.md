---
title: Filtering
---

# Filtering

It is possible to define filters for Django types, which will
be converted into `.filter(...)` queries for the ORM:

```python title="types.py"
import strawberry_django
from strawberry import auto
from typing_extensions import Self

@strawberry_django.filter_type(models.Fruit)
class FruitFilter:
    id: auto
    name: auto

@strawberry_django.type(models.Fruit, filters=FruitFilter)
class Fruit:
    ...
```

> [!TIP]
> In most cases filter fields should have `Optional` annotations and default value `strawberry.UNSET` like so:
> `foo: Optional[SomeType] = strawberry.UNSET`
> Above `auto` annotation is wrapped in `Optional` automatically.
> `UNSET` is automatically used for fields without `field` or with `strawberry_django.filter_field`.

The code above would generate following schema:

```graphql title="schema.graphql"
input FruitFilter {
  id: ID
  name: String
  AND: FruitFilter
  OR: FruitFilter
  NOT: FruitFilter
  DISTINCT: Boolean
}
```

> [!TIP]
> If you are using the [relay integration](relay.md) and working with types inheriting
> from `relay.Node` and `GlobalID` for identifying objects, you might want to set
> `MAP_AUTO_ID_AS_GLOBAL_ID=True` in your [strawberry django settings](./settings.md)
> to make sure `auto` fields gets mapped to `GlobalID` on types and filters.

## AND, OR, NOT, DISTINCT ...

To every filter `AND`, `OR`, `NOT` & `DISTINCT` fields are added to allow more complex filtering

```graphql
{
  fruits(
    filters: {
      name: "kebab"
      OR: {
        name: "raspberry"
      }
    }
  ) { ... }
}
```

## List-based AND/OR/NOT Filters

The `AND`, `OR`, and `NOT` operators can also be declared as lists, allowing for more complex combinations of conditions. This is particularly useful when you need to combine multiple conditions in a single operation.

```python title="types.py"
@strawberry_django.filter_type(models.Vegetable, lookups=True)
class VegetableFilter:
    id: auto
    name: auto
    AND: Optional[list[Self]] = strawberry.UNSET
    OR: Optional[list[Self]] = strawberry.UNSET
    NOT: Optional[list[Self]] = strawberry.UNSET
```

This enables queries like:

```graphql
{
  vegetables(
    filters: {
      AND: [{ name: { contains: "blue" } }, { name: { contains: "squash" } }]
    }
  ) {
    id
  }
}
```

The list-based filtering system differs from the single object filter in a few ways:

1. It allows combining multiple conditions in a single `AND`, `OR`, or `NOT` operation
2. The conditions in a list are evaluated together as a group
3. When using `AND`, all conditions in the list must be satisfied
4. When using `OR`, any condition in the list can be satisfied
5. When using `NOT`, none of the conditions in the list should be satisfied

This is particularly useful for complex queries where you need to have multiple conditions against the same field.

## Lookups

Lookups can be added to all fields with `lookups=True`, which will
add more options to resolve each type. For example:

```python title="types.py"
@strawberry_django.filter_type(models.Fruit, lookups=True)
class FruitFilter:
    id: auto
    name: auto
```

The code above would generate the following schema:

```graphql title="schema.graphql"
input IDBaseFilterLookup {
  exact: ID
  isNull: Boolean
  inList: [String!]
}

input StrFilterLookup {
  exact: ID
  isNull: Boolean
  inList: [String!]
  iExact: String
  contains: String
  iContains: String
  startsWith: String
  iStartsWith: String
  endsWith: String
  iEndsWith: String
  regex: String
  iRegex: String
}

input FruitFilter {
  id: IDFilterLookup
  name: StrFilterLookup
  AND: FruitFilter
  OR: FruitFilter
  NOT: FruitFilter
  DISTINCT: Boolean
}
```

Single-field lookup can be annotated with the appropriate lookup type for the field.
Use specific lookup types like `StrFilterLookup` for strings, `ComparisonFilterLookup` for numbers, etc.

```python title="types.py"
from strawberry_django import StrFilterLookup

@strawberry_django.filter_type(models.Fruit)
class FruitFilter:
    name: StrFilterLookup | None
```

> [!WARNING]
> Avoid using `FilterLookup[str]` directly. Use the specific lookup type (`StrFilterLookup`)
> instead to prevent `DuplicatedTypeName` errors. See the [Generic Lookup reference](#generic-lookup-reference)
> for the full list of available lookup types.

## Filtering over relationships

```python title="types.py"
@strawberry_django.filter_type(models.Color)
class ColorFilter:
    id: auto
    name: auto

@strawberry_django.filter_type(models.Fruit)
class FruitFilter:
    id: auto
    name: auto
    color: ColorFilter | None
```

The code above would generate following schema:

```graphql title="schema.graphql"
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

## Custom filter methods

You can define custom filter method by defining your own resolver.

```python title="types.py"
@strawberry_django.filter_type(models.Fruit)
class FruitFilter:
    name: auto
    last_name: auto

    @strawberry_django.filter_field
    def simple(self, value: str, prefix) -> Q:
        return Q(**{f"{prefix}name": value})

    @strawberry_django.filter_field
    def full_name(
        self,
        queryset: QuerySet,
        value: str,
        prefix: str
    ) -> tuple[QuerySet, Q]:
        queryset = queryset.alias(
            _fullname=Concat(
                f"{prefix}name", Value(" "), f"{prefix}last_name"
            )
        )
        return queryset, Q(**{"_fullname": value})

    @strawberry_django.filter_field
    def full_name_lookups(
        self,
        info: Info,
        queryset: QuerySet,
        value: strawberry_django.StrFilterLookup,
        prefix: str
    ) -> tuple[QuerySet, Q]:
        queryset = queryset.alias(
            _fullname=Concat(
                f"{prefix}name", Value(" "), f"{prefix}last_name"
            )
        )
        return strawberry_django.process_filters(
            filters=value,
            queryset=queryset,
            info=info,
            prefix=f"{prefix}_fullname"
        )
```

> [!WARNING]
> It is discouraged to use `queryset.filter()` directly. When using more
> complex filtering via `NOT`, `OR` & `AND` this might lead to undesired behaviour.

> [!TIP]
>
> #### process_filters
>
> As seen above `strawberry_django.process_filters` function is exposed and can be
> reused in custom methods. Above it's used to resolve fields lookups
>
> #### null values
>
> By default `null` value is ignored for all filters & lookups. This applies to custom
> filter methods as well. Those won't even be called (you don't have to check for `None`).
> This can be modified using
> `strawberry_django.filter_field(filter_none=True)`
>
> This also means that built in `exact` & `iExact` lookups cannot be used to filter for `None`
> and `isNull` have to be used explicitly.
>
> #### value resolution
>
> - `value` parameter of type `relay.GlobalID` is resolved to its `node_id` attribute
> - `value` parameter of type `Enum` is resolved to is's value
> - `value` parameter wrapped in `strawberry.Some` (from [`Maybe`](https://strawberry.rocks/docs/types/maybe#maybe) type) is unwrapped and resolved
> - above types are converted in `lists` as well
>
> resolution can modified via `strawberry_django.filter_field(resolve_value=...)`
>
> - True - always resolve
> - False - never resolve
> - UNSET (default) - resolves for filters without custom method only

The code above generates the following schema:

```graphql title="schema.graphql"
input FruitFilter {
  name: String
  lastName: String
  simple: str
  fullName: str
  fullNameLookups: StrFilterLookup
}
```

#### Resolver arguments

- `prefix` - represents the current path or position
  - **Required**
  - Important for nested filtering
  - In code bellow custom filter `name` ends up filtering `Fruit` instead of `Color` without applying `prefix`

```python title="Why prefix?"
@strawberry_django.filter_type(models.Fruit)
class FruitFilter:
    name: auto
    color: ColorFilter | None

@strawberry_django.filter_type(models.Color)
class ColorFilter:
    @strawberry_django.filter_field
    def name(self, value: str, prefix: str):
        # prefix is "fruit_set__" if unused root object is filtered instead
        if value:
            return Q(name=value)
        return Q()
```

```graphql
{
  fruits( filters: {color: {name: "blue"}} ) { ... }
}
```

- `value` - represents graphql field type
  - **Required**, but forbidden for default `filter` method
  - _must_ be annotated
  - used instead of field's return type
- `queryset` - can be used for more complex filtering
  - Optional, but **Required** for default `filter` method
  - usually used to `annotate` `QuerySet`

#### Resolver return

For custom field methods two return values are supported

- django's `Q` object
- tuple with `QuerySet` and django's `Q` object -> `tuple[QuerySet, Q]`

For default `filter` method only second variant is supported.

### What about nulls?

By default `null` values are ignored. This can be toggled as such `@strawberry_django.filter_field(filter_none=True)`

## Overriding the default `filter` method

Works similar to field filter method, but:

- is responsible for resolution of filtering for entire object
- _must_ be named `filter`
- argument `queryset` is **Required**
- argument `value` is **Forbidden**

```python title="types.py"
@strawberry_django.filter_type(models.Fruit)
class FruitFilter:
    def ordered(
        self,
        value: int,
        prefix: str,
        queryset: QuerySet,
    ):
        queryset = queryset.alias(
          _ordered_num=Count(f"{prefix}orders__id")
        )
        return queryset, Q(**{f"{prefix}_ordered_num": value})

    @strawberry_django.filter_field
    def filter(
        self,
        info: Info,
        queryset: QuerySet,
        prefix: str,
    ) -> tuple[QuerySet, list[Q]]:
        queryset = queryset.filter(
            ... # Do some query modification
        )

        return strawberry_django.process_filters(
            self,
            info=info,
            queryset=queryset,
            prefix=prefix,
            skip_object_filter_method=True
        )
```

> [!TIP]
> As seen above `strawberry_django.process_filters` function is exposed and can be
> reused in custom methods.
> For filter method `filter` `skip_object_filter_method` was used to avoid endless recursion.

## Adding filters to types

All fields and CUD mutations inherit filters from the underlying type by default.
So, if you have a field like this:

```python title="types.py"
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

```python title="schema.py"
@strawberry.type
class Query:
    fruits: list[Fruit] = strawberry_django.field(filters=FruitFilter)
```

## Generic Lookup reference

There is 7 already defined Generic Lookup `strawberry.input` classes importable from `strawberry_django`

#### `BaseFilterLookup`

- contains `exact`, `isNull` & `inList`
- used for `ID` & `bool` fields

#### `RangeLookup`

- used for `range` or `BETWEEN` filtering

#### `ComparisonFilterLookup`

- inherits `BaseFilterLookup`
- additionaly contains `gt`, `gte`, `lt`, `lte`, & `range`
- used for Numberical fields

#### `FilterLookup`

- inherits `BaseFilterLookup`
- additionally contains `iExact`, `contains`, `iContains`, `startsWith`, `iStartsWith`, `endsWith`, `iEndsWith`, `regex` & `iRegex`
- used for string based fields and as default

#### `DateFilterLookup`

- inherits `ComparisonFilterLookup`
- additionally contains `year`,`month`,`day`,`weekDay`,`isoWeekDay`,`week`,`isoYear` & `quarter`
- used for date based fields

#### `TimeFilterLookup`

- inherits `ComparisonFilterLookup`
- additionally contains `hour`,`minute`,`second`,`date` & `time`
- used for time based fields

#### `DatetimeFilterLookup`

- inherits `DateFilterLookup` & `TimeFilterLookup`
- used for timedate based fields

## Legacy filtering

The previous version of filters can be enabled via [**USE_DEPRECATED_FILTERS**](settings.md#strawberry_django)

> [!WARNING]
> If **USE_DEPRECATED_FILTERS** is not set to `True` legacy custom filtering
> methods will be _not_ be called.

When using legacy filters it is important to use legacy
`strawberry_django.filters.FilterLookup` lookups as well.
The correct version is applied for `auto`
annotated filter field (given `lookups=True` being set). Mixing old and new lookups
might lead to error `DuplicatedTypeName: Type StrFilterLookup is defined multiple times in the schema`.

While legacy filtering is enabled new filtering custom methods are
fully functional including default `filter` method.

Migration process could be composed of these steps:

- enable **USE_DEPRECATED_FILTERS**
- gradually transform custom filter field methods to new version (do not forget to use old FilterLookup if applicable)
- gradually transform default `filter` methods
- disable **USE_DEPRECATED_FILTERS** - **_This is breaking change_**
