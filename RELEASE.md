---
release type: patch
---

Document how to restrict which objects can be related in CUD mutations. Related objects referenced
by a `GlobalID` (e.g. `NodeInput`) are resolved through their type's `get_queryset`, so restricting
it to the objects the current user can access also prevents relating any other object, while
related objects referenced by a `strawberry.ID` are retrieved from the model's default manager.
