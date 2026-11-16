---
release type: minor
---

`strawberry.auto` now resolves subclasses of mapped model fields to the type of their closest mapped base
class, instead of raising `NotImplementedError`. Custom fields like the ones below no longer need to be
added to `field_type_map`:

```python
class LowercaseCharField(models.CharField): ...


class MyAutoField(models.BigAutoField): ...


class MyModel(models.Model):
    id = MyAutoField(primary_key=True)  # resolves to `ID`
    name = LowercaseCharField(max_length=50)  # resolves to `str`
```

This applies to types, inputs, filters, `ArrayField` base fields and `GeneratedField` output fields.
An entry for the subclass itself in `field_type_map` still takes precedence.
