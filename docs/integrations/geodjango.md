---
title: GeoDjango
---

# GeoDjango

Strawberry Django provides built-in support for
[GeoDjango](https://docs.djangoproject.com/en/stable/ref/contrib/gis/) fields,
automatically mapping them to GraphQL scalar types.

## Supported Field Types

| Django Field           | GraphQL Scalar    | Description                        |
| ---------------------- | ----------------- | ---------------------------------- |
| `PointField`           | `Point`           | A point as `(x, y)` or `(x, y, z)` |
| `LineStringField`      | `LineString`      | Multiple points forming a line     |
| `PolygonField`         | `Polygon`         | One or more LinearRings            |
| `MultiPointField`      | `MultiPoint`      | Collection of Points               |
| `MultiLineStringField` | `MultiLineString` | Collection of LineStrings          |
| `MultiPolygonField`    | `MultiPolygon`    | Collection of Polygons             |
| `GeometryField`        | `Geometry`        | Any geometry type                  |

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

from . import models

@strawberry_django.type(models.Location)
class Location:
    id: auto
    name: auto
    point: auto  # Automatically uses Point scalar
    area: auto   # Automatically uses Polygon scalar

@strawberry_django.input(models.Location)
class LocationInput:
    name: auto
    point: auto
    area: auto
```

## GraphQL Data Format

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

## Spatial Queries

For spatial filtering (distance, contains, etc.), implement custom resolvers:

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
