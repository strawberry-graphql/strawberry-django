---
title: GeoDjango
---

# GeoDjango

Strawberry Django provides built-in support for
[GeoDjango](https://docs.djangoproject.com/en/stable/ref/contrib/gis/) fields,
automatically mapping them to GraphQL scalar types.

## Supported Field Types

| Django Field           | GraphQL Scalar    | Description                        | Input format                  | Output format |
| ---------------------- | ----------------- | ---------------------------------- | ----------------------------- | ------------- |
| `PointField`           | `Point`           | A point as `(x, y)` or `(x, y, z)` | Coordinates                   | Coordinates   |
| `LineStringField`      | `LineString`      | Multiple points forming a line     | Coordinates                   | Coordinates   |
| `PolygonField`         | `Polygon`         | One or more LinearRings            | Coordinates                   | Coordinates   |
| `MultiPointField`      | `MultiPoint`      | Collection of Points               | Coordinates                   | Coordinates   |
| `MultiLineStringField` | `MultiLineString` | Collection of LineStrings          | Coordinates                   | Coordinates   |
| `MultiPolygonField`    | `MultiPolygon`    | Collection of Polygons             | Coordinates                   | Coordinates   |
| `GeometryField`        | `Geometry`        | Any geometry type                  | WKT, EWKT, HEXEWKB or GeoJSON | Coordinates   |

See [GraphQL Data Format](#graphql-data-format) for details.

## Usage

Define your model and type as usual—geographic fields are handled automatically:

```python
# models.py
from django.contrib.gis.db import models


class Location(models.Model):
    name = models.CharField(max_length=100)
    point = models.PointField()
    area = models.PolygonField(null=True, blank=True)
```

```python
# types.py
import strawberry_django
from strawberry import auto
from django.contrib.gis.geos import Point, Polygon

from . import models


@strawberry_django.type(models.Location)
class Location:
    id: auto
    name: auto
    point: auto  # Automatically uses Point scalar
    area: auto  # Automatically uses Polygon scalar


@strawberry_django.input(models.Location)
class LocationInput:
    name: auto
    point: auto
    area: auto


# You can also use geos types directly in annotations
@strawberry_django.type(models.Location)
class LocationExplicit:
    id: auto
    name: auto
    point: Point
    area: Polygon | None
```

## GraphQL Data Format

### Geometry-specific scalars

`Point`, `LineString`, `LinearRing`, `Polygon`, `MultiPoint`, `MultiLineString`
and `MultiPolygon` are both read and written as nested coordinate arrays:

```graphql
# Point: [x, y] or [x, y, z]
point: [2.2945, 48.8584]

# LineString: array of points
lineString: [[0, 0], [1, 1], [2, 0]]

# Polygon: array of rings (first is exterior, rest are holes)
polygon: [[[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]]]

# Multi* types: arrays of the corresponding type
multiPoint: [[0, 0], [1, 1]]
multiPolygon: [[[[0, 0], [1, 0], [1, 1], [0, 0]]]]
```

These scalars don't accept WKT or GeoJSON strings.

### `Geometry` scalar

The `Geometry` scalar accepts a string in any format supported by
[`GEOSGeometry`](https://docs.djangoproject.com/en/stable/ref/contrib/gis/geos/#django.contrib.gis.geos.GEOSGeometry):

```graphql
geometry: "POINT(2.2945 48.8584)"                        # WKT
geometry: "SRID=4326;POINT(2.2945 48.8584)"              # EWKT
geometry: "{\"type\": \"Point\", \"coordinates\": [2.2945, 48.8584]}"  # GeoJSON
```

When no SRID is given, the SRID of the model field is used.

> [!WARNING]
> `Geometry` values are **output** as coordinate arrays, the same way as the
> geometry-specific scalars (e.g. `[2.2945, 48.8584]`). So a queried value can't
> be sent back as input as is, and the output doesn't say which kind of geometry
> it is.

## Spatial Queries

### Spatial lookups

Filters defined with `lookups=True` get spatial lookups for geometry fields
through [`GeometryFilterLookup`](../guide/filters.md#geometryfilterlookup):

```python
# types.py
@strawberry_django.filter_type(models.Location, lookups=True)
class LocationFilter:
    name: auto
    point: auto
    area: auto


@strawberry_django.type(models.Location, filters=LocationFilter)
class Location:
    id: auto
    name: auto
    point: auto
```

```graphql
query {
  locations(
    filters: { point: { within: "POLYGON((0 0, 0 10, 10 10, 10 0, 0 0))" } }
  ) {
    id
    name
  }
}
```

The available lookups are `exact`, `isNull`, `contains`, `disjoint`, `equals`,
`intersects`, `overlaps`, `touches` and `within`. Only lookups supported by every
GeoDjango backend are included.

> [!NOTE]
> Lookup values always use the [`Geometry` scalar](#geometry-scalar) format
> (WKT, EWKT, HEXEWKB or GeoJSON), whatever the type of the field. For example,
> filter a `PointField` with `"POINT(1 2)"`, not `[1, 2]`.

### Custom spatial queries

For anything not covered by the lookups above, such as distance queries,
implement custom resolvers:

```python
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D


@strawberry.type
class Query:
    @strawberry_django.field
    def locations_near(
        self, latitude: float, longitude: float, radius_km: float
    ) -> list[Location]:
        point = Point(longitude, latitude, srid=4326)
        return models.Location.objects.filter(
            point__distance_lte=(point, D(km=radius_km))
        )
```

For GeoDjango setup and troubleshooting, see the
[GeoDjango documentation](https://docs.djangoproject.com/en/stable/ref/contrib/gis/install/).
