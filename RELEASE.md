---
release type: patch
---

Fix the auto-generated federation `resolve_reference` ignoring scalar mappings. When an entity is resolved through `_entities`, key fields typed with a custom scalar (including `StrawberryConfig.scalar_map` overrides) now go through that scalar's `parse_value`, and enum keys are converted to their value before the model lookup.
