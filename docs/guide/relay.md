# Relay Support

You can use the [official strawberry relay integration](https://strawberry.rocks/docs/guides/relay)
directly with django types like this:

```{.python title=types.py}
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
    def fruit_with_custom_resolver(self) -> List[SomeModel]:
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

!!! tip

    If you are only working with types inheriting from `relay.Node` and `GlobalID`
    for identifying objects, you might want to set `MAP_AUTO_ID_AS_GLOBAL_ID=True`
    in your [strawberry django settings](../settings) to make sure `auto` fields gets
    mapped to `GlobalID` on types and filters.

Also, this lib exposes a `strawberry_django.relay.ListConnectionWithTotalCount`, which works
the same way as `strawberry.relay.ListConnection` does, but also exposes a
`totalCount` attribute in the connection.

For more customization options, like changing the pagination algorithm, adding extra fields
to the `Connection`/`Edge` type, take a look at the
[official strawberry relay integration](https://strawberry.rocks/docs/guides/relay)
as those are properly explained there.
