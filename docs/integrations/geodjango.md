---
title: GeoDjango
---

# GeoDjango

Strawberry Django provides built-in support for
[GeoDjango](https://docs.djangoproject.com/en/stable/ref/contrib/gis/) fields,
automatically mapping them to GraphQL scalar types.

## Supported Field Types

| Django Field           | GraphQL Scalar    | Description                        | Input format                               | Output format |
| ---------------------- | ----------------- | ---------------------------------- | ------------------------------------------ | ------------- |
| `PointField`           | `Point`           | A point as `(x, y)` or `(x, y, z)` | Coordinates, WKT, EWKT, HEXEWKB or GeoJSON | Coordinates   |
| `LineStringField`      | `LineString`      | Multiple points forming a line     | Coordinates, WKT, EWKT, HEXEWKB or GeoJSON | Coordinates   |
| `PolygonField`         | `Polygon`         | One or more LinearRings            | Coordinates, WKT, EWKT, HEXEWKB or GeoJSON | Coordinates   |
| `MultiPointField`      | `MultiPoint`      | Collection of Points               | Coordinates, WKT, EWKT, HEXEWKB or GeoJSON | Coordinates   |
| `MultiLineStringField` | `MultiLineString` | Collection of LineStrings          | Coordinates, WKT, EWKT, HEXEWKB or GeoJSON | Coordinates   |
| `MultiPolygonField`    | `MultiPolygon`    | Collection of Polygons             | Coordinates, WKT, EWKT, HEXEWKB or GeoJSON | Coordinates   |
| `GeometryField`        | `Geometry`        | Any geometry type                  | WKT, EWKT, HEXEWKB or GeoJSON              | Coordinates   |

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

### Input

All geometry scalars accept the standard formats supported by
[`GEOSGeometry`](https://docs.djangoproject.com/en/stable/ref/contrib/gis/geos/#django.contrib.gis.geos.GEOSGeometry):
WKT, EWKT, HEXEWKB and GeoJSON. GeoJSON can be given either as a string or as an
object:

```graphql
point: "POINT(2.2945 48.8584)"                            # WKT
point: "SRID=4326;POINT(2.2945 48.8584)"                  # EWKT
point: "0101000000..."                                    # HEXEWKB
point: "{\"type\": \"Point\", \"coordinates\": [2.2945, 48.8584]}"  # GeoJSON string
point: { type: "Point", coordinates: [2.2945, 48.8584] }  # GeoJSON object
```

GeoJSON objects can also be passed through variables, so geometries coming from
other GeoJSON sources can be sent as they are:

```json
{ "data": { "point": { "type": "Point", "coordinates": [2.2945, 48.8584] } } }
```

Only GeoJSON geometries are accepted, not `Feature` or `FeatureCollection` objects.
The geometry type must match the scalar: for example, a `Point` field doesn't accept a
`POLYGON(...)`. The `Geometry` scalar accepts any geometry type.

The geometry-specific scalars (`Point`, `LineString`, `LinearRing`, `Polygon`,
`MultiPoint`, `MultiLineString` and `MultiPolygon`) also accept nested coordinate
arrays:

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

The `Geometry` scalar doesn't accept coordinate arrays, since they don't say which
kind of geometry they are.

#### SRID

- WKT, HEXEWKB and coordinate arrays have no SRID, so the SRID of the model field
  is used.
- GeoJSON is always in `EPSG:4326`.
- EWKT uses the SRID it declares.

When the SRID of the input differs from the SRID of the model field, the geometry
is transformed to the field's SRID when saved or used in a lookup.

### Output

All geometry scalars are output as coordinate arrays, as shown above
(e.g. `[2.2945, 48.8584]` for a point).

> [!WARNING]
> `Geometry` values are output as coordinate arrays as well, so the output doesn't
> say which kind of geometry it is, and a queried `Geometry` value can't be sent
> back as input as is.

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
> Lookup values use the `Geometry` scalar whatever the type of the field, so they
> accept any geometry type in WKT, EWKT, HEXEWKB or GeoJSON (see [Input](#input)),
> but not coordinate arrays. For example, filter a `PointField` with
> `"POINT(1 2)"`, not `[1, 2]`.

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
