---
release type: patch
---

Fix `StrFilterLookup` so it can be used without a type parameter (e.g., `name: StrFilterLookup | None`). Previously this raised `TypeError: "StrFilterLookup" is generic, but no type has been passed` at schema build time.
