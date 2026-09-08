---
release type: patch
---

Permission extensions are now fully compatible with `strawberry-graphql >= 0.326.0`, which enforces strict type uniqueness for custom schema directives during schema construction.

Previously, `DjangoPermissionExtension.schema_directive` created a new anonymous `AutoDirective` class on every extension instantiation without caching it on the underlying class.
When the same permission extension (e.g. `IsSuperuser()`, `IsAuthenticated()`, or custom subclasses) was attached to multiple fields, Strawberry raised a `ValueError` reporting duplicate directive definitions for the same directive name.

The generated `AutoDirective` class is now cached on `self.__class__` via `__dict__.get()`:

```python
@functools.cached_property
def schema_directive(self) -> object:
    key = "__strawberry_directive_type__"
    directive_class = self.__class__.__dict__.get(key)

    if directive_class is None:

        @schema_directive(
            name=self.__class__.__name__,
            locations=self.SCHEMA_DIRECTIVE_LOCATIONS,
            description=self.SCHEMA_DIRECTIVE_DESCRIPTION,
            repeatable=True,
        )
        class AutoDirective: ...

        directive_class = AutoDirective
        setattr(self.__class__, key, directive_class)

    return directive_class()
```

This ensures a single, reusable schema directive type is created per extension class, eliminating duplicate directive collisions while preserving full isolation across subclasses and maintaining backward compatibility with older Strawberry versions.
