---
release type: minor
---

Add `DjangoExceptionHandler`, a schema-level Strawberry exception handler for
converting Django `ValidationError`, `PermissionDenied`, and `ObjectDoesNotExist`
exceptions into `OperationInfo` results. Combined with `handle_django_errors=True`,
it also handles exceptions raised during input conversion or by sync and async field
extensions.
