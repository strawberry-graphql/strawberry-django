---
release type: minor
---

Add a `with_global_perms` argument to `HasSourcePerm` and `HasRetvalPerm`, mirroring the `accept_global_perms` option
of django-guardian's `get_objects_for_user`.

By default, a user with a global (model-level) permission passes object permission checks for every object, as
before. With `with_global_perms=False`, only the permissions assigned for the objects themselves (e.g. through
django-guardian, directly or through the user's groups) are considered, both when checking a single object and
when filtering lists, connections and paginated results.

```python
@strawberry.type
class Query:
    projects: list[ProjectType] = strawberry_django.field(
        extensions=[HasRetvalPerm("projects.view_project", with_global_perms=False)],
    )
```

`strawberry_django.utils.query.filter_for_user` also accepts the new argument.
