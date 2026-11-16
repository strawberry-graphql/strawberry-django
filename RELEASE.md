---
release type: patch
---

Raise a clear `TypeError` when a mutation with `handle_django_errors=True` returns a type that
can't be part of its payload union with `OperationInfo`, such as a scalar (e.g. `bool`), an enum
or an input type. Previously, creating the schema raised a generic union error or an
`AssertionError`, or, for enums, generated a payload union without the returned type.
