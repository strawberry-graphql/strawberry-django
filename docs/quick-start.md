# Quick Start

In this Quick-Start, we will:

- Set up a basic pair of models with a relation between them.
- Add them to a graphql schema and serve the graph API.
- Query the graph API for model contents.

For a more advanced example of a similar setup including a set of mutations and more queries, please check the [example app](https://github.com/strawberry-graphql/strawberry-graphql-django/tree/main/examples/django).

## Installation

```sh
poetry add strawberry-graphql-django
poetry add django-choices-field  # Not required but recommended
```

(Not using poetry yet? `pip install strawberry-graphql-django` works fine too.)

## Define your application models

We'll build an example database of fruit and their colours.

!!! tip

    You'll notice that for `Fruit.category`, we use `TextChoicesField` instead of `TextField(choices=...)`.
    This allows strawberry-django to automatically use an enum in the graphQL schema, instead of
    a string which would be the default behaviour for TextField.

    See the [choices-field integration](./integrations/choices-field.md) for more information.

```{.python title=models.py}
from django.db import models
from django_choices_field import TextChoicesField

class FruitCategory(models.TextChoices):
    CITRUS = "citrus", "Citrus"
    BERRY = "berry", "Berry"

class Fruit(models.Model):
    """A tasty treat"""

    name = models.CharField(max_length=20, help_text="The name of the fruit variety")
    category = TextChoicesField(choices_enum=FruitCategory, help_text="The category of the fruit")
    color = models.ForeignKey(
        "Color",
        on_delete=models.CASCADE,
        related_name="fruits",
        blank=True,
        null=True,
        help_text="The color of this kind of fruit",
    )

class Color(models.Model):
    """The hue of your tasty treat"""

    name = models.CharField(
        max_length=20,
        help_text="The color name",
    )
```

You'll need to make migrations then migrate:

```sh
python manage.py makemigrations
python manage.py migrate
```

Now use the django shell, the admin, the loaddata command or whatever tool you like to load some fruits and colors. I've loaded a red strawberry (predictable, right?!) ready for later.

## Define types

Before creating queries, you have to define a `type` for each model. A `type` is a fundamental unit of the [schema](https://strawberry.rocks/docs/types/schema)
which describes the shape of the data that can be queried from the GraphQL server. Types can represent scalar values (like String, Int, Boolean, Float, and ID), enums, or complex objects that consist of many fields.

!!! tip

    A key feature of `strawberry-graphql-django` is that it provides helpers to create types from django models,
    by automatically inferring types (and even documentation!!) from the model fields.

    See the [fields guide](./guide/fields.md) for more information.

```{.python title=types.py}
import strawberry_django
from strawberry import auto

from . import models

@strawberry_django.type(models.Fruit)
class Fruit:
    id: auto
    name: auto
    category: auto
    color: "Color"  # Strawberry will understand that this refers to the "Color" type that's defined below

@strawberry_django.type(models.Color)
class Color:
    id: auto
    name: auto
    fruits: list[Fruit] # This tells strawberry about the ForeignKey to the Fruit model and how to represent the Fruit instances on that relation
```

## Build the queries and schema

Next we want to assemble the [schema](https://strawberry.rocks/docs/types/schema) from its building block types.

!!! warning

    You'll notice a familiar statement, `fruits: list[Fruit]`. We already used this statement in the previous step in `types.py`.
    Seeing it twice can be a point of confusion when you're first getting to grips with graph and strawberry.

    The purpose here is similar but subtly different. Previously, the syntax defined that it was possible to make a query that **traverses** within the graph, from a Color to a list of Fruits.
    Here, the usage defines a [**root** query](https://strawberry.rocks/docs/general/queries) (a bit like an entrypoint into the graph).

!!! tip

    We add the `DjangoOptimizerExtension` here. Don't worry about why for now, but you're almost certain to want it.

    See the [optimizer guide](./guide/optimizer.md) for more information.

```{.python title=schema.py}
import strawberry
from strawberry_django.optimizer import DjangoOptimizerExtension

from .types import Fruit

@strawberry.type
class Query:
    fruits: list[Fruit] = strawberry_django.field()

schema = strawberry.Schema(
    query=Query,
    extensions=[
        DjangoOptimizerExtension,
    ],
)
```

## Serving the API

Now we're showing off. This isn't enabled by default, since existing django applications will likely
have model docstrings and help text that aren't user-oriented. But if you're starting clean (or overhauling
existing dosctrings and helptext), setting up the following is super useful for your API users.

If you don't set these true, you can always provide user-oriented descriptions. See the

```{.python title=settings.py}
STRAWBERRY_DJANGO = {
    "FIELD_DESCRIPTION_FROM_HELP_TEXT": True,
    "TYPE_DESCRIPTION_FROM_MODEL_DOCSTRING": True,
}
```

```{.python title=urls.py}
from django.urls import include, path
from strawberry.django.views import AsyncGraphQLView

from .schema import schema

urlpatterns = [
    path('graphql', AsyncGraphQLView.as_view(schema=schema)),
]
```

This generates following schema:

```{.graphql title=schema.graphql}
enum FruitCategory {
  CITRUS
  BERRY
}

"""
A tasty treat
"""
type Fruit {
  id: ID!
  name: String!
  category: FruitCategory!
  color: Color
}

type Color {
  id: ID!
  """
  field description
  """
  name: String!
  fruits: [Fruit!]
}

type Query {
  fruits: [Fruit!]!
}
```

## Using the API

Start your server with:

```sh
python manage.py runserver
```

Then visit [localhost:8000/graphql](http://localhost:8000/graphql) in your browser. You should see the graphql explorer being served by django.
Using the interactive query tool, you can query for the fruits you added earlier:

<div style="width: 100%;">
    <img src="../images/graphiql-with-fruit.png" style="width: 100%;" />
</div>

## Next steps

1. [Defining more Django Types](./guide/types.md)
2. [Define Fields inside those Types](./guide/fields.md)
3. [Serve your API using ASGI or WSGI](./guide/views.md)
4. [Define filters for your fields](./guide/filters.md)
5. [Define orderings for your fields](./guide/ordering.md)
6. [Define pagination for your fields](./guide/pagination.md)
7. [Define queries for your schema](./guide/queries.md)
8. [Define mutations for your schema](./guide/mutations.md)
9. [Define subscriptions for your schema](./guide/subscriptions.md)
10. [Enable the Query Optimizer extension for performance improvement](./guide/optimizer.md)
11. [Use the relay integration for advanced pagination and model refetching](./guide/relay.md)
12. [Protect your fields using the Permission Extension](./guide/permissions.md)
13. [Write unit tests for your schema](./guide/unit-testing.md)
