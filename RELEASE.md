---
release type: patch
---

Fixes compatibility with `strawberry-graphql>=0.296.0` by ensuring proper `Info` type resolution.

`Info` is now imported at runtime and resolver arguments include explicit type annotations.
This aligns with the updated behavior where parameter injection is strictly **type-hint based** rather than name-based.

Before, resolvers relying on implicit name-based injection could fail under newer Strawberry versions.

After this change, resolvers work correctly with the stricter type-based injection system introduced in newer releases.
