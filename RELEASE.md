---
release type: patch
---

Adds support for Django-style relationship traversal in `strawberry_django.field(field_name=...)` using `LOOKUP_SEP` (`__`). You can now flatten related objects or scalar fields without custom resolvers.

Examples:

```python
@strawberry_django.type(User)
class UserType:
    role: RoleType | None = strawberry_django.field(
        field_name="assigned_role__role",
    )

    role_name: str | None = strawberry_django.field(
        field_name="assigned_role__role__name",
    )
```

The traversal returns `None` if an intermediate relationship is `None`. Documentation and tests cover the new behavior, including optimizer query counts.
