---
title: django-guardian
---

# django-guardian

This lib provides integration for per-object-permissions using
[django-guardian](https://django-guardian.readthedocs.io/en/stable/).

## Installation

First, install django-guardian:

```bash
pip install django-guardian
```

Or with the strawberry-django extras:

```bash
pip install strawberry-graphql-django
pip install django-guardian
```

## Configuration

Add guardian to your Django settings:

```python title="settings.py"
INSTALLED_APPS = [
    # ...
    'guardian',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',  # Default backend
    'guardian.backends.ObjectPermissionBackend',   # Guardian backend
]

# Optional: Configure anonymous user handling
ANONYMOUS_USER_NAME = None  # Set to a username string to enable anonymous user permissions
```

Run migrations to create guardian's permission tables:

```bash
python manage.py migrate guardian
```

## Usage with Permission Extensions

Once configured, you can use `HasSourcePerm` and `HasRetvalPerm` to check object-level permissions:

```python title="types.py"
import strawberry_django
from strawberry_django.permissions import (
    HasPerm,
    HasSourcePerm,
    HasRetvalPerm,
)
from . import models

@strawberry_django.type(models.Document)
class DocumentType:
    id: auto
    title: auto
    content: auto

    # Check object permission on the resolved document
    @strawberry_django.field(extensions=[HasRetvalPerm("documents.view_document")])
    def secret_content(self) -> str:
        return self.secret_content
```

```python title="schema.py"
import strawberry
import strawberry_django
from strawberry_django.permissions import HasRetvalPerm, HasSourcePerm

@strawberry.type
class Query:
    # Filter documents to only those the user has permission to view
    @strawberry_django.field(extensions=[HasRetvalPerm("documents.view_document")])
    def documents(self) -> list[DocumentType]:
        return models.Document.objects.all()

    # Check permission on parent object
    @strawberry_django.field(extensions=[HasSourcePerm("documents.view_document")])
    def document_metadata(self, document: DocumentType) -> MetadataType:
        return document.metadata
```

## Permission Extension Parameters

The permission extensions accept several parameters for fine-grained control:

### HasPerm / HasSourcePerm / HasRetvalPerm

```python
HasRetvalPerm(
    perms="app.permission",         # Required: permission string or list of permissions
    any_perm=True,                  # If True, user needs ANY of the perms; if False, needs ALL
    with_anonymous=True,            # If True, skip permission check for anonymous users (faster)
    with_superuser=False,           # If True, superusers bypass permission checks
    fail_silently=True,             # If True, return None/empty instead of raising error
)
```

### Example: Multiple Permissions

```python
@strawberry_django.field(
    extensions=[
        HasRetvalPerm(
            ["documents.view_document", "documents.edit_document"],
            any_perm=False,  # User must have BOTH permissions
        )
    ]
)
def sensitive_document(self, id: strawberry.ID) -> DocumentType:
    return models.Document.objects.get(pk=id)
```

### Example: Superuser Bypass

```python
@strawberry_django.field(
    extensions=[
        HasRetvalPerm(
            "documents.view_document",
            with_superuser=True,  # Superusers can access without the specific permission
        )
    ]
)
def document(self, id: strawberry.ID) -> DocumentType:
    return models.Document.objects.get(pk=id)
```

## Assigning Object Permissions

Use django-guardian's utilities to assign permissions:

```python
from guardian.shortcuts import assign_perm, remove_perm, get_objects_for_user

# Assign permission to a user for a specific object
document = Document.objects.get(pk=1)
assign_perm('documents.view_document', user, document)

# Remove permission
remove_perm('documents.view_document', user, document)

# Get all objects a user has permission for
user_documents = get_objects_for_user(user, 'documents.view_document')
```

## How List Filtering Works

When using `HasRetvalPerm` on a field that returns a list, the extension automatically filters the results:

```python
@strawberry_django.field(extensions=[HasRetvalPerm("documents.view_document")])
def documents(self) -> list[DocumentType]:
    # Returns all documents, but the extension filters to only those
    # the user has 'view_document' permission for
    return models.Document.objects.all()
```

The filtering happens after the queryset is evaluated, so for better performance with large datasets, consider filtering at the database level:

```python
from guardian.shortcuts import get_objects_for_user

@strawberry_django.field
def my_documents(self, info: Info) -> list[DocumentType]:
    user = info.context.request.user
    return get_objects_for_user(user, 'documents.view_document')
```

## Global vs Object Permissions

- **Global permissions** (`HasPerm`): Checks if user has a permission at the model level (e.g., can create any document)
- **Object permissions** (`HasSourcePerm`, `HasRetvalPerm`): Checks if user has a permission for a specific object instance

```python
@strawberry.type
class Mutation:
    # Global permission: Can user create ANY document?
    @strawberry.mutation(extensions=[HasPerm("documents.add_document")])
    def create_document(self, title: str) -> DocumentType:
        return Document.objects.create(title=title)

    # Object permission: Can user edit THIS specific document?
    @strawberry.mutation(extensions=[HasSourcePerm("documents.change_document")])
    def update_document(self, document: DocumentType, title: str) -> DocumentType:
        document.title = title
        document.save()
        return document
```

## Troubleshooting

### Permissions Not Working

1. **Check AUTHENTICATION_BACKENDS**: Ensure `guardian.backends.ObjectPermissionBackend` is in your settings
2. **Run migrations**: Make sure `python manage.py migrate guardian` was executed
3. **Verify permission assignment**: Use Django shell to check if permissions are correctly assigned

```python
from guardian.shortcuts import get_perms
get_perms(user, document)  # Returns list of permission codenames
```

### Anonymous User Issues

If you need anonymous users to have permissions, configure `ANONYMOUS_USER_NAME` in settings and use:

```python
HasRetvalPerm("app.perm", with_anonymous=False)  # Don't skip check for anonymous users
```

## See Also

- [Permissions Guide](../guide/permissions.md) - Full permissions documentation
- [django-guardian documentation](https://django-guardian.readthedocs.io/en/stable/)
