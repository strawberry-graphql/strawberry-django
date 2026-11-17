---
release type: minor
---

**Behavior change:** Create mutations now prepare, validate and persist one model
instance, preserving changes made by `Model.clean()` and running `pre_save_hook`
for every item in a batched create. Custom managers or querysets must expose
`insert(instance) -> instance` to run insertion logic on the prepared instance.
The resolver calls this method when callable, otherwise it inserts the instance
with `instance.save(force_insert=True, using=manager.db)`.

The resolver no longer dispatches through `Manager.create(**kwargs)` overrides.
Move any custom creation logic needed by these mutations into `insert(instance)`.
