---
release type: minor
---

Geometry fields output as `DjangoGeometryType` now accept a `simplify` argument, to reduce the number of vertices of complex geometries (and so the response size) before they are output:

```graphql
query {
  regions {
    boundary(simplify: { tolerance: 0.001 }) {
      geojson
    }
  }
}
```

`tolerance` is in the units of the field's SRID (degrees for `EPSG:4326`), and `preserveTopology` (default `true`) keeps the simplified geometry valid. The geometry is simplified with GEOS, so the result is the same on every database backend.
