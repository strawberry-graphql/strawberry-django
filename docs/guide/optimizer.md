---
title: Query Optimizer
---

# Query Optimizer

## Features

The query optimizer is a must-have extension for improved performance of your schema.
What it does:

1. Call [QuerySet.select_related()](https://docs.djangoproject.com/en/4.2/ref/models/querysets/#select-related)
   on all selected foreign key relations by the query to avoid requiring an extra query to retrieve those
2. Call [QuerySet.prefetch_related()](https://docs.djangoproject.com/en/4.2/ref/models/querysets/#prefetch-related)
   on all selected many-to-one/many-to-many relations by the query to avoid requiring an extra query to retrieve those.
3. Call [QuerySet.only()](https://docs.djangoproject.com/en/4.2/ref/models/querysets/#only)
   on all selected fields to reduce the database payload and only requesting what is actually being
   selected
4. Call [QuerySet.annotate()](https://docs.djangoproject.com/en/4.2/ref/models/querysets/#annotate)
   to support any passed annotations
   of [Query Expressions](https://docs.djangoproject.com/en/4.2/ref/models/expressions/).

Those are specially useful to avoid some common GraphQL pitfalls, like the famous `n+1` issue.

## Enabling the extension

The automatic optimization can be enabled by adding the `DjangoOptimizerExtension`
to your strawberry's schema config.

```python title="schema.py"
import strawberry
from strawberry_django.optimizer import DjangoOptimizerExtension

schema = strawberry.Schema(
    Query,
    extensions=[
        # other extensions...
        DjangoOptimizerExtension,
    ]
)
```

## Usage

The optimizer will try to optimize all types automatically by introspecting it.
Consider the following example:

```python title="models.py"
class Artist(models.Model):
    name = models.CharField()


class Album(models.Model):
    name = models.CharField()
    release_date = models.DateTimeField()
    artist = models.ForeignKey("Artist", related_name="albums")


class Song(models.Model):
    name = model.CharField()
    duration = models.DecimalField()
    album = models.ForeignKey("Album", related_name="songs")
```

```python title="types.py"
from strawberry import auto
import strawberry_django

@strawberry_django.type(Artist)
class ArtistType:
    name: auto
    albums: list["AlbumType"]
    albums_count: int = strawberry_django.field(annotate=Count("albums"))


@strawberry_django.type(Album)
class AlbumType:
    name: auto
    release_date: auto
    artist: ArtistType
    songs: list["SongType"]


@strawberry_django.type(Song)
class SongType:
    name: auto
    duration: auto
    album_type: AlbumType


@strawberry.type
class Query:
    artist: Artist = strawberry_django.field()
    songs: List[SongType] = strawberry_django.field()
```

Querying for `artist` and `songs` like this:

```graphql title="schema.graphql"
query {
  artist {
    id
    name
    albums {
      id
      name
      songs {
        id
        name
      }
    }
    albumsCount
  }
  song {
    id
    album {
      id
      name
      artist {
        id
        name
        albums {
          id
          name
          release_date
        }
      }
    }
  }
}
```

Would produce an ORM query like this:

```python
# For "artist" query
Artist.objects.all().only("id", "name").prefetch_related(
    Prefetch(
        "albums",
        queryset=Album.objects.all().only("id", "name").prefetch_related(
            Prefetch(
               "songs",
               Song.objects.all().only("id", "name"),
            )
        )
    ),
).annotate(
    albums_count=Count("albums")
)

# For "songs" query
Song.objects.all().only(
    "id",
    "album",
    "album__id",
    "album__name",
    "album__release_date",  # Note about this below
    "album__artist",
    "album__artist__id",
).select_related(
    "album",
    "album__artist",
).prefetch_related(
    Prefetch(
       "album__artist__albums",
        Album.objects.all().only("id", "name", "release_date"),
    )
)
```

!!! note

    Even though `album__release_date` field was not selected here, it got selected
    in the prefetch query later. Since Django caches known objects, we have to select it here or
    else it would trigger extra queries latter.

## Optimization hints

Sometimes you will have a custom resolver which cannot be automatically optimized
by the extension. Take this for example:

```python title="models.py"
class OrderItem(models.Model):
    price = models.DecimalField()
    quantity = models.IntegerField()

    @property
    def total(self) -> decimal.Decimal:
        return self.price * self.quantity
```

```python title="types.py"
from strawberry import auto
import strawberry_django

@strawberry_django.type(models.OrderItem)
class OrderItem:
    price: auto
    quantity: auto
    total: auto
```

In this case, if only `total` is requested it would trigger an extra query for
both `price` and `quantity` because both had their value retrievals
[defered](https://docs.djangoproject.com/en/4.2/ref/models/querysets/#django.db.models.query.QuerySet.defer)
by the optimizer.

A solution in this case would be to "tell the optimizer" how to optimize that field:

```python title="types.py"
from strawberry import auto
import strawberry_django

@strawberry_django.type(models.OrderItem)
class OrderItem:
    price: auto
    quantity: auto
    total: auto = strawberry_django.field(
        only=["price", "quantity"],
    )
```

Or if you are using a custom resolver:

```python title="types.py"
import decimal

from strawberry import auto
import strawberry_django

@strawberry_django.type(models.OrderItem)
class OrderItem:
    price: auto
    quantity: auto

    @strawberry_django.field(only=["price", "quantity"])
    def total(self, root: models.OrderItem) -> decimal.Decimal:
        return root.price * root.quantity  # or root.total directly
```

The following options are accepted for optimizer hints:

- `only`: a list of fields in the same format as accepted by
  [QuerySet.only()](https://docs.djangoproject.com/en/4.2/ref/models/querysets/#only)
- `select_related`: a list of relations to join using
  [QuerySet.select_related()](https://docs.djangoproject.com/en/4.2/ref/models/querysets/#select-related)
- `prefetch_related`: a list of relations to prefetch using
  [QuerySet.prefetch_related()](https://docs.djangoproject.com/en/4.2/ref/models/querysets/#prefetch-related).
  The options here are strings or a callable in the format of `Callable[[Info], Prefetch]`
  (e.g. `prefetch_related=[lambda info: Prefetch(...)]`)
- `annotate`: a dict of expressions to annotate using
  [QuerySet.annotate()](https://docs.djangoproject.com/en/4.2/ref/models/querysets/#annotate).
  The keys of this dict are strings,
  and each value is a [Query Expression](https://docs.djangoproject.com/en/4.2/ref/models/expressions/)
  or a callable in the format of `Callable[[Info], BaseExpression]`
  (e.g. `annotate={"total": lambda info: Sum(...)}`)

## Optimization hints on model (ModelProperty)

It is also possible to include type hints directly in the models' `@property`
to allow it to be resolved with `auto`, while the GraphQL schema doesn't have
to worry about its internal logic.

For that this integration provides 2 decorators that can be used:

- `strawberry_django.model_property`: similar to `@property` but accepts optimization hints
- `strawberry_django.cached_model_property`: similar to `@cached_property` but accepts
  optimization hints

The example in the previous section could be written using `@model_property` like this:

```python title="models.py"
from strawberry_django import model_property

class OrderItem(models.Model):
    price = models.DecimalField()
    quantity = models.IntegerField()

    @model_property(only=["price", "quantity"])
    def total(self) -> decimal.Decimal:
        return self.price * self.quantity
```

```python title="types.py"
from strawberry import auto
import strawberry_django

@strawberry_django.type(models.OrderItem)
class OrderItem:
    price: auto
    quantity: auto
    total: auto
```

`total` now will be properly optimized since it points to a `@model_property`
decorated attribute, which contains the required information for optimizing it.
