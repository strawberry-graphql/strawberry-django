---
release type: patch
---

Honor the `DEFAULT_PK_FIELD_NAME` setting (and per-field `key_attr`) when
resolving existing instances in mutation inputs. Previously `_parse_pk` read the
input value under `key_attr` but always looked the instance up by `pk=`, so
relation inputs and bare-id updates that reference an object by a configured
non-pk field raised `DoesNotExist` or matched the wrong row. Filters already
honored the setting; mutations now do too. The default `pk`-based path is
unchanged.
