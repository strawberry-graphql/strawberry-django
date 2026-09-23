---
release type: minor
---

Add `GeometryFilterLookup`, which adds spatial lookups to the filters of GeoDjango geometry fields.

When GeoDjango is installed, filters created with `lookups=True` use `GeometryFilterLookup` for geometry fields (`PointField`, `PolygonField`, `GeometryField`, etc.). It includes `exact`, `isNull` and the spatial lookups supported by every GeoDjango backend: `contains`, `disjoint`, `equals`, `intersects`, `overlaps`, `touches` and `within`.

```python
@strawberry_django.filter_type(models.Place, lookups=True)
class PlaceFilter:
    location: auto
```

```graphql
query {
  places(
    filters: { location: { within: "POLYGON((0 0, 0 10, 10 10, 10 0, 0 0))" } }
  ) {
    id
  }
}
```
