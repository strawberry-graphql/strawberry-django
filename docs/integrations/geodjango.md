---
title: GeoDjango
---

# GeoDjango

Strawberry Django provides built-in support for
[GeoDjango](https://docs.djangoproject.com/en/stable/ref/contrib/gis/) fields,
automatically mapping them to GraphQL types: geometries are output as a
`DjangoGeometryType` object and are input as GraphQL scalars.

## Supported Field Types

| Django Field           | Input Scalar      | Description                        | Input format                               | Output type          |
| ---------------------- | ----------------- | ---------------------------------- | ------------------------------------------ | -------------------- |
| `PointField`           | `Point`           | A point as `(x, y)` or `(x, y, z)` | Coordinates, WKT, EWKT, HEXEWKB or GeoJSON | `DjangoGeometryType` |
| `LineStringField`      | `LineString`      | Multiple points forming a line     | Coordinates, WKT, EWKT, HEXEWKB or GeoJSON | `DjangoGeometryType` |
| `PolygonField`         | `Polygon`         | One or more LinearRings            | Coordinates, WKT, EWKT, HEXEWKB or GeoJSON | `DjangoGeometryType` |
| `MultiPointField`      | `MultiPoint`      | Collection of Points               | Coordinates, WKT, EWKT, HEXEWKB or GeoJSON | `DjangoGeometryType` |
| `MultiLineStringField` | `MultiLineString` | Collection of LineStrings          | Coordinates, WKT, EWKT, HEXEWKB or GeoJSON | `DjangoGeometryType` |
| `MultiPolygonField`    | `MultiPolygon`    | Collection of Polygons             | Coordinates, WKT, EWKT, HEXEWKB or GeoJSON | `DjangoGeometryType` |
| `GeometryField`        | `Geometry`        | Any geometry type                  | WKT, EWKT, HEXEWKB or GeoJSON              | `DjangoGeometryType` |

There is also a `LinearRing` scalar with the same input formats. Django has no
`LinearRingField`, so it's only used when annotating `geos.LinearRing` directly.

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
    point: auto  # Output as DjangoGeometryType
    area: auto  # Output as DjangoGeometryType


@strawberry_django.input(models.Location)
class LocationInput:
    name: auto
    point: auto  # Input as the Point scalar
    area: auto  # Input as the Polygon scalar


# Annotating geos types directly uses the scalars, also for output
# (see "Keeping the coordinate output" below)
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
`POLYGON(...)`. The `Geometry` scalar accepts any geometry type. Since GeoJSON
and WKB have no LinearRing type, the `LinearRing` scalar also accepts a closed
LineString in those formats.

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

Geometries are output as a `DjangoGeometryType` object:

| Field      | Type      | Description                                                  |
| ---------- | --------- | ------------------------------------------------------------ |
| `wkt`      | `String!` | WKT, in the SRID of the field                                |
| `ewkt`     | `String!` | EWKT, in the SRID of the field (includes the SRID)           |
| `srid`     | `Int`     | The SRID of the field                                        |
| `geomType` | `String!` | The kind of geometry, e.g. `Point` or `Polygon`              |
| `geojson`  | `JSON!`   | A GeoJSON geometry object, always in `EPSG:4326` (see below) |

```graphql
query {
  locations {
    point {
      wkt
      srid
      geojson
    }
  }
}
```

```json
{
  "point": {
    "wkt": "POINT (2.2945 48.8584)",
    "srid": 4326,
    "geojson": { "type": "Point", "coordinates": [2.2945, 48.8584] }
  }
}
```

GeoJSON ([RFC 7946](https://datatracker.ietf.org/doc/html/rfc7946)) is always in
`EPSG:4326` (`[longitude, latitude]`), so `geojson` is transformed to `EPSG:4326`
when the field uses another SRID. A geometry without an SRID is output as is.
`geojson` is a `JSON` scalar, so pick its parts, such as `coordinates`, on the
client.

### Keeping the coordinate output

Before `DjangoGeometryType`, geometries were output as coordinate arrays through
the input scalars (e.g. `[2.2945, 48.8584]` for a point). To keep that output:

- for every geometry field, set the
  [`USE_GEOMETRY_SCALARS`](../guide/settings.md#strawberry_django) setting to `True`:

  ```python
  STRAWBERRY_DJANGO = {"USE_GEOMETRY_SCALARS": True}
  ```

- for some fields only, annotate them with the geos type instead of `auto`. This lets
  you migrate clients field by field:

  ```python
  from django.contrib.gis.geos import Polygon


  @strawberry_django.type(models.Location)
  class Location:
      point: auto  # DjangoGeometryType
      area: Polygon | None  # coordinate output
  ```

The same coordinates are available in the new type as `geojson.coordinates`, in
`EPSG:4326`.

> [!WARNING]
> With the coordinate output, `Geometry` values don't say which kind of geometry
> they are, and a queried `Geometry` value can't be sent back as input as is.

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
