# Relay Support

You can use the [official strawberry relay integration](https://strawberry.rocks/docs/guides/relay)
directly with django types like this:

```{.python title=types.py}
import strawberry
import strawberry_django
from strawberry import relay
from strawberry_django.relay import ListConnectionWithTotalCount


class Fruit(models.Model):
    ...


@strawberry_django.type(Fruit)
class FruitType(relay.Node):
    ...


@strawberry.type
class Query:
    some_model_conn: relay.ListConnection[FruitType] = gql.django.connection()
    some_model_conn_with_total_count: ListConnectionWithTotalCount[
        FruitType
    ] = gql.django.connection()

    @gql.django.connection(gql.relay.ListConnection[FruitType])
    def some_model_conn_with_resolver(self, root: SomeModel) -> models.QuerySet[SomeModel]:
        return SomeModel.objects.all()
```

Behind the scenes this extension is doing the following for you:

- Automatically resolve the `relay.NodeID` field using the [model's pk](https://docs.djangoproject.com/en/4.2/ref/models/fields/#django.db.models.Field.primary_key)
- Automatically generate resolves for connections that doesn't define one. For example,
  `some_model_conn` and `some_model_conn_with_total_count` will both define a custom resolver
  that returns `SomeModel.objects.all()`.
- Integrate connection resolution with all other features available in this lib. For example,
  [filters](/guide/filters), [ordering](/guide/ordering) and
  [permissioning](/guide/permissioning) can be used together with connections defined
  by strawberry django.

You can also define your own `relay.NodeID` field and your resolve, in the same way as
`some_model_conn_with_resolver` is doing. In those cases, they will not be overridden.

Also, this lib exposes a `strawberry_django.relay.ListConnectionWithTotalCount`, which works
the same way as `strawberry.relay.ListConnection` does, but also exposes a
`totalCount` attribute in the connection.

For more customization options, like changing the pagination algorithm, adding extra fields
to the `Connection`/`Edge` type, take a look at the
[official strawberry relay integration](https://strawberry.rocks/docs/guides/relay)
as those are properly explained there.
