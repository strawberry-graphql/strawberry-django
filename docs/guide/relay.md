---
title: Relay
---

# Relay Support

You can use the [official strawberry relay integration](https://strawberry.rocks/docs/guides/relay)
directly with django types like this:

```python title="types.py"
import strawberry
import strawberry_django
from strawberry_django.relay import ListConnectionWithTotalCount


class Fruit(models.Model):
    ...


@strawberry_django.type(Fruit)
class FruitType(relay.Node):
    ...


@strawberry.type
class Query:
    # Option 1: Default relay without totalCount
    # This is the default strawberry relay behaviour.
    # NOTE: you need to use strawberry_django.connection() - not the default strawberry.relay.connection()
    fruit: strawberry.relay.ListConnection[FruitType] = strawberry_django.connection()

    # Option 2: Strawberry django also comes with ListConnectionWithTotalCount
    # this will allow you to get total-count on your query.
    fruit_with_total_count: ListConnectionWithTotalCount[
        FruitType
    ] = strawberry_django.connection()

    # Option 3: You can manually create resolver by your method manually.
    @strawberry_django.connection(ListConnectionWithTotalCount[FruitType])
    def fruit_with_custom_resolver(self) -> list[SomeModel]:
        return Fruit.objects.all()
```

Behind the scenes this extension is doing the following for you:

- Automatically resolve the `relay.NodeID` field using the [model's pk](https://docs.djangoproject.com/en/4.2/ref/models/fields/#django.db.models.Field.primary_key)
- Automatically generate resolves for connections that doesn't define one. For example,
  `some_model_conn` and `some_model_conn_with_total_count` will both define a custom resolver
  automatically that returns `SomeModel.objects.all()`.
- Integrate connection resolution with all other features available in this lib. For example,
  [filters](filters.md), [ordering](ordering.md) and
  [permissions](permissions.md) can be used together with connections defined
  by strawberry django.

You can also define your own `relay.NodeID` field and your resolve, in the same way as
`some_model_conn_with_resolver` is doing. In those cases, they will not be overridden.

> [!TIP]
> If you are only working with types inheriting from `relay.Node` and `GlobalID`
> for identifying objects, you might want to set `MAP_AUTO_ID_AS_GLOBAL_ID=True`
> in your [strawberry django settings](./settings.md) to make sure `auto` fields gets
> mapped to `GlobalID` on types and filters.

Also, this lib exposes a `strawberry_django.relay.ListConnectionWithTotalCount`, which works
the same way as `strawberry.relay.ListConnection` does, but also exposes a
`totalCount` attribute in the connection.

For more customization options, like changing the pagination algorithm, adding extra fields
to the `Connection`/`Edge` type, take a look at the
[official strawberry relay integration](https://strawberry.rocks/docs/guides/relay)
as those are properly explained there.

## Cursor based connections

As an alternative to the default `ListConnection`, `DjangoCursorConnection` is also available.
It supports pagination through a Django `QuerySet` via "true" cursors.
`ListConnection` uses slicing to achieve pagination, which can negatively affect performance for huge datasets,
because large page numbers require a large `OFFSET` in SQL.
Instead `DjangoCursorConnection` can use range queries such as `Q(due_date__gte=...)` for pagination. In combination
with an Index, this makes for more efficient queries.

`DjangoCursorConnection` requires a _strictly_ ordered `QuerySet`, that is, no two entries in the `QuerySet`
must be considered equal by its ordering. `order_by('due_date')` for example is not strictly ordered, because two
items could have the same due date. `DjangoCursorConnection` will automatically resolve such situations by 
also ordering by the primary key.

When the order for the connection is configurable by the user (for example via
[`@strawberry_django.order`](./ordering.md)) then cursors created by `DjangoCursorConnection` will not be compatible
between different orders.

The drawback of cursor based pagination is that users cannot jump to a particular page immediately. Therefor
cursor based pagination is better suited for things like an infinitely scrollable list.

Otherwise `DjangoCursorConnection` behaves like other connection classes:
```python
@strawberry.type
class Query:
    fruit: DjangoCursorConnection[FruitType] = strawberry_django.connection()

    @strawberry_django.connection(DjangoCursorConnection[FruitType])
    def fruit_with_custom_resolver(self) -> list[Fruit]:
      return Fruit.objects.all()
```
