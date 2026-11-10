---
release type: patch
---

Validate the type of a `GlobalID` given to a CUD mutation against the mutation's model.

Before, an id for an object of another type was resolved to that object. Updating or
deleting with it raised an error that included the `repr` of that object, and
using it for a related field in a nested input raised an `AssertionError`.

Now the type is checked before anything is retrieved in update and delete mutations,
and a related object resolved from a `GlobalID` must be an instance of the field's
model. Otherwise, the model's `DoesNotExist` error is raised, the same error as for an
object that doesn't exist, which `handle_django_errors=True` returns as an
`OperationInfo`:

```json
{
  "updateIssue": {
    "__typename": "OperationInfo",
    "messages": [
      {
        "kind": "ERROR",
        "field": null,
        "message": "Issue matching query does not exist."
      }
    ]
  }
}
```
