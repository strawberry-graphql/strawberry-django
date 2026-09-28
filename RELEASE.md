---
release type: minor
---

All GeoDjango geometry scalars now accept WKT, EWKT, HEXEWKB and GeoJSON (as a string or an object) as input.

Before, the geometry-specific scalars (`Point`, `LineString`, `LinearRing`, `Polygon`, `MultiPoint`, `MultiLineString` and `MultiPolygon`) only accepted coordinate arrays, and the `Geometry` scalar, also used by the spatial filter lookups, only accepted strings. Coordinate arrays keep working, so this is not a breaking change.

```graphql
mutation {
  createLocation(
    data: {
      point: "SRID=4326;POINT(2.2945 48.8584)"
      area: {
        type: "Polygon"
        coordinates: [[[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]]
      }
    }
  ) {
    id
  }
}
```

The geometry type must match the scalar (e.g. a `Point` doesn't accept a `POLYGON`), and geometries with a different SRID are transformed to the field's SRID.
