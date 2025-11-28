---
title: Permissions
---

# Permissions

This integration exposes field extensions to use
[Django's Permission System](https://docs.djangoproject.com/en/4.2/topics/auth/default/)
for checking permissions on GraphQL fields.

It supports protecting any field for cases like:

- The user is authenticated
- The user is a superuser
- The user or a group they belong to has a given permission
- The user or the group they belong to has a given permission to the resolved value
- The user or the group they belong to has a given permission to the parent of the field
- etc

## How it works

```mermaid
graph TD
  A[Extension Check for Permissions] --> B;
  B[User Passes Checks] -->|Yes| BF[Return Resolved Value];
  B -->|No| C;
  C[Can return 'OperationInfo'?] -->|Yes| CF[Return 'OperationInfo'];
  C -->|No| D;
  D[Field is Optional] -->|Yes| DF[Return 'None'];
  D -->|No| E;
  E[Field is a 'List'] -->|Yes| EF[Return an empty 'List'];
  E -->|No| F;
  F[Field is a relay 'Connection'] -->|Yes| FF[Return an empty relay 'Connection'];
  F -->|No| GF[Raises 'PermissionDenied' error];
```

## Basic Example

```python title="types.py"
import strawberry_django
from strawberry_django.permissions import (
    IsAuthenticated,
    HasPerm,
    HasSourcePerm,
    HasRetvalPerm,
)


@strawberry_django.type
class SomeType:
    login_required_field: RetType = strawberry_django.field(
        # will check if the user is authenticated
        extensions=[IsAuthenticated()],
    )
    perm_required_field: OtherType = strawberry_django.field(
        # will check if the user has `"some_app.some_perm"` permission
        extensions=[HasPerm("some_app.some_perm")],
    )
    obj_perm_required_field: OtherType = strawberry_django.field(
        # will check the permission for the resolved value
        extensions=[HasRetvalPerm("some_app.some_perm")],
    )
```

## Available Permission Extensions

### IsAuthenticated

Checks if the user is authenticated and active.

```python
from strawberry_django.permissions import IsAuthenticated

@strawberry_django.field(extensions=[IsAuthenticated()])
def protected_field(self) -> str:
    return "secret"
```

**Parameters:**

- `message: str` - Custom error message (default: "User is not authenticated.")
- `fail_silently: bool` - If `True`, return `None`/empty instead of raising error (default: `True`)

### IsStaff

Checks if the user is a staff member (`user.is_staff`).

```python
from strawberry_django.permissions import IsStaff

@strawberry_django.field(extensions=[IsStaff()])
def admin_field(self) -> str:
    return "admin only"
```

**Parameters:**

- `message: str` - Custom error message (default: "User is not a staff member.")
- `fail_silently: bool` - If `True`, return `None`/empty instead of raising error (default: `True`)

### IsSuperuser

Checks if the user is a superuser (`user.is_superuser`).

```python
from strawberry_django.permissions import IsSuperuser

@strawberry_django.field(extensions=[IsSuperuser()])
def superuser_field(self) -> str:
    return "superuser only"
```

**Parameters:**

- `message: str` - Custom error message (default: "User is not a superuser.")
- `fail_silently: bool` - If `True`, return `None`/empty instead of raising error (default: `True`)

### HasPerm

Checks if the user has global (model-level) permissions.

```python
from strawberry_django.permissions import HasPerm

@strawberry_django.field(extensions=[HasPerm("app.add_model")])
def create_something(self) -> Model:
    ...
```

**Parameters:**

| Parameter        | Type               | Default                          | Description                                                   |
| ---------------- | ------------------ | -------------------------------- | ------------------------------------------------------------- |
| `perms`          | `str \| list[str]` | required                         | Permission(s) to check (e.g., `"app.permission"`)             |
| `any_perm`       | `bool`             | `True`                           | If `True`, user needs ANY of the perms; if `False`, needs ALL |
| `with_anonymous` | `bool`             | `True`                           | If `True`, anonymous users automatically fail (optimization)  |
| `with_superuser` | `bool`             | `False`                          | If `True`, superusers bypass permission checks                |
| `message`        | `str`              | `"You don't have permission..."` | Custom error message                                          |
| `fail_silently`  | `bool`             | `True`                           | If `True`, return `None`/empty instead of raising error       |

**Examples:**

```python
# Require ALL permissions
@strawberry_django.field(
    extensions=[HasPerm(["app.view_model", "app.change_model"], any_perm=False)]
)
def sensitive_field(self) -> str:
    ...

# Allow superusers to bypass
@strawberry_django.field(
    extensions=[HasPerm("app.special_permission", with_superuser=True)]
)
def special_field(self) -> str:
    ...

# Raise error instead of returning None
@strawberry_django.field(
    extensions=[HasPerm("app.required_permission", fail_silently=False)]
)
def required_field(self) -> str:
    ...
```

### HasSourcePerm

Checks if the user has permission for the **parent/source object** of the field.

This is useful when you want to check permissions on the object that contains the field, not the field's return value.

```python
from strawberry_django.permissions import HasSourcePerm

@strawberry_django.type(models.Document)
class DocumentType:
    id: auto
    title: auto

    # Only show content if user has view permission on THIS document
    @strawberry_django.field(extensions=[HasSourcePerm("documents.view_document")])
    def content(self) -> str:
        return self.content
```

**Parameters:** Same as `HasPerm`

### HasRetvalPerm

Checks if the user has permission for the **resolved/returned value**.

This is useful for:

- Checking object-level permissions on query results
- Filtering lists to only include objects the user can access

```python
from strawberry_django.permissions import HasRetvalPerm

@strawberry.type
class Query:
    # Returns only documents the user has permission to view
    @strawberry_django.field(extensions=[HasRetvalPerm("documents.view_document")])
    def documents(self) -> list[DocumentType]:
        return models.Document.objects.all()

    # Returns document only if user has permission, else None
    @strawberry_django.field(extensions=[HasRetvalPerm("documents.view_document")])
    def document(self, id: int) -> DocumentType | None:
        return models.Document.objects.get(pk=id)
```

**Parameters:** Same as `HasPerm`

**List Filtering:** When used on a field returning a list, `HasRetvalPerm` automatically filters out objects the user doesn't have permission for, rather than failing the entire query.

## Object-Level Permissions

`HasSourcePerm` and `HasRetvalPerm` require an authentication backend that supports object permissions. This library works out of the box with [django-guardian](https://django-guardian.readthedocs.io/en/stable/).

See the [django-guardian integration](../integrations/guardian.md) for setup instructions.

## No Permission Handling

When permission checks fail, the following is returned (in priority order):

1. `OperationInfo`/`OperationMessage` if those types are allowed in the return type
2. `null` if the field is optional (e.g., `String` or `[String]`)
3. An empty list if the field is a list (e.g., `[String]!`)
4. An empty `Connection` if the return type is a relay connection
5. Otherwise, a `PermissionDenied` error is raised

To always raise an error instead, set `fail_silently=False`:

```python
@strawberry_django.field(
    extensions=[IsAuthenticated(fail_silently=False)]
)
def must_be_authenticated(self) -> str:
    ...
```

## Combining Multiple Permissions

You can apply multiple permission extensions to a single field:

```python
@strawberry_django.field(
    extensions=[
        IsAuthenticated(),
        HasPerm("app.special_permission"),
    ]
)
def protected_field(self) -> str:
    ...
```

All extensions must pass for the field to resolve.

## Custom Error Messages

All permission extensions accept a `message` parameter:

```python
@strawberry_django.field(
    extensions=[
        IsAuthenticated(message="Please log in to view this content"),
        HasPerm("premium.access", message="This requires a premium subscription"),
    ]
)
def premium_content(self) -> str:
    ...
```

## Custom Permission Extensions

Create custom permission logic by subclassing `DjangoPermissionExtension`:

```python
from strawberry_django.permissions import DjangoPermissionExtension, DjangoNoPermission

class IsVerifiedEmail(DjangoPermissionExtension):
    DEFAULT_ERROR_MESSAGE = "Email verification required."

    def resolve_for_user(
        self,
        resolver,
        user,
        *,
        info,
        source,
    ):
        if not user or not user.is_authenticated:
            raise DjangoNoPermission

        if not getattr(user, 'email_verified', False):
            raise DjangoNoPermission

        return resolver()
```

Usage:

```python
@strawberry_django.field(extensions=[IsVerifiedEmail()])
def verified_only_field(self) -> str:
    ...
```

## Schema Directives

Permission extensions automatically add schema directives to your GraphQL schema, making permissions visible in introspection. This can be turned off:

```python
@strawberry_django.field(
    extensions=[HasPerm("app.permission", use_directives=False)]
)
def field_without_directive(self) -> str:
    ...
```

## See Also

- [django-guardian Integration](../integrations/guardian.md) - Object-level permissions
- [Authentication](./authentication.md) - User authentication
- [Error Handling](./error-handling.md) - Handling permission errors
