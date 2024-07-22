---
title: Django Choices Field
---

# django-choices-field

This lib provides integration for enum resolution for
[Django's TextChoices/IntegerChoices](https://docs.djangoproject.com/en/4.2/ref/models/fields/#enumeration-types)
when defining the fields using the
[django-choices-field](https://github.com/bellini666/django-choices-field) lib:

```{.python title=models.py}
from django.db import models
from django_choices_field import TextChoicesField

class Status(models.TextChoices):
    ACTIVE = "active", "Is Active"
    INACTIVE = "inactive", "Inactive"

class Company(models.Model):
    status = TextChoicesField(
        choices_enum=Status,
        default=Status.ACTIVE,
    )
```

```{.python title=types.py}
import strawberry
import strawberry_django

import .models

@strawberry_django.type(models.Company)
class Company:
    status: strawberry.auto
```

The code above would generate the following schema:

```{.graphql title=schema.graphql}
enum Status {
  ACTIVE
  INACTIVE
}

type Company {
  status: Status
}
```
