---
release type: minor
---

**BREAKING CHANGE**: `auto` GeoDjango geometry fields are now output as a `DjangoGeometryType` object instead of coordinate arrays. Inputs and filters are unchanged.

`DjangoGeometryType` has `wkt`, `ewkt`, `srid`, `geomType` and `geojson`. `geojson` is a GeoJSON object, always in `EPSG:4326` as required by RFC 7946:

```graphql
query {
  locations {
    point {
      wkt
      geojson
    }
  }
}
```

```json
{
  "point": {
    "wkt": "POINT (2.2945 48.8584)",
    "geojson": { "type": "Point", "coordinates": [2.2945, 48.8584] }
  }
}
```

### Migrating

Queries that selected a geometry field directly (e.g. `point`) now need a selection (e.g. `point { geojson }`). The coordinates that used to be returned are now in `geojson.coordinates`, in `EPSG:4326`. `geojson` is a `JSON` scalar, so read `coordinates` from it on the client.

To keep the previous coordinate output:

- for every geometry field, set `STRAWBERRY_DJANGO = {"USE_GEOMETRY_SCALARS": True}`;
- for some fields only, annotate them with the geos type (e.g. `area: Polygon | None`) instead of `auto`, to migrate clients field by field.
