---
release type: minor
---

Require `strawberry-graphql>=0.328.0`, which requires `graphql-core>=3.3.0`.

- Removed `strawberry_django.utils.IS_GQL_32` and `IS_GQL_33`.
- `StrawberryDjangoField.get_result` returns an unevaluated `QuerySet` for list fields. graphql-core fetches it while completing the list, using `async for` in async execution.
- Removed the `StrawberryDjangoField.disable_fetch_list_results` attribute.

See Strawberry's [0.328.0 breaking changes](https://strawberry.rocks/docs/breaking-changes/0.328.0) for the graphql-core 3.3 changes to error messages and schema printing.
