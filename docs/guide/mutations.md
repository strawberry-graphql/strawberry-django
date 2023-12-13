# Mutations

## Getting started

Mutations can be defined the same way as
[strawberry's mutations](https://strawberry.rocks/docs/general/mutations), but instead of
using `@strawberry.mutation`, use `@strawberry_django.mutation`.

Here are the differences between those:

- Strawberry Django's mutation will be sure that the mutation is executed in an async safe
  environment, meaning that if you are running ASGI and you define a `sync` resolver, it will
  automatically be wrapped in a `sync_to_async` call.
- It will better integrate with the [permissioning integration](../permissions)
- It has an option to automatically handle common django errors and return them
  in a standardized way (more on that below)

## Django errors handling

When defining a mutation you can pass `handle_django_errors=True` to make it handle
common django errors, such as `ValidationError`, `PermissionDenied` and `ObjectDoesNotExist`:

```{.python title=types.py}
@strawberry_django.type
class Mutation:
    @strawberry_django.mutation(handle_django_errors=True)
    def create_fruit(self, name: str, color: str) -> Fruit:
        if not is_valid_color(color):
            raise ValidationError("The color is not valid")

        # Creation can also raise ValidationError, if the `name` is
        # larger than its allowed `max_length` for example.
        fruit = models.Fruit.objects.create(name=name)
        return cast(Fruit, fruit)
```

The code above would generate following schema:

```{.graphql title=schema.graphql}
enum OperationMessageKind {
  INFO
  WARNING
  ERROR
  PERMISSION
  VALIDATION
}

type OperationInfo {
  """List of messages returned by the operation."""
  messages: [OperationMessage!]!
}

type OperationMessage {
  """The kind of this message."""
  kind: OperationMessageKind!

  """The error message."""
  message: String!

  """
  The field that caused the error, or `null` if it isn't associated with any particular field.
  """
  field: String

  """The error code, or `null` if no error code was set."""
  code: String
}

type Fruit {
  name: String!
  color: String!
}

union CreateFruitPayload = Fruit | OperationInfo

mutation {
  createFruit(
    name: String!
    color: String!
  ): CreateFruitPayload!
}
```

!!! tip

    If all or most of your mutations use this behaviour, you can change the
    default behaviour for `handle_django_errors` by setting
    `MUTATIONS_DEFAULT_HANDLE_ERRORS=True`  in your [strawberry django settings](../settings)

## Input mutations

Those are defined using `@strawberry_django.input_mutation` and act the same way as
the `@strawberry_django.mutation`, the only difference being that it injects
an [InputMutationExtension](https://strawberry.rocks/docs/general/mutations#the-input-mutation-extension)
in the field, which converts its arguments in a new type (check the extension's docs
for more information).

## CUD mutations

The following CUD mutations are provided by this lib:

- `strawberry_django.mutations.create`: Will create the model using the data from the given input
- `strawberry_django.mutations.update`: Will update the model using the data from the given input
- `strawberry_django.mutations.delete`: Will delete the model using the id from the given input

A basic example would be:

```{.python title=types.py}
from strawberry import auto
from strawberry_django import mutations, NodeInput
from strawberry.relay import Node



@strawberry_django.type(SomeModel)
class SomeModelType(Node):
    name: auto

@strawberry_django.input(SomeModel)
class SomeModelInput:
    name: auto


@strawberry_django.partial(SomeModel)
class SomeModelInputPartial(NodeInput):
    name: auto

@strawberry_django.type
class Mutation:
    create_model: SomeModelType = mutations.create(SomeModelInput)
    update_model: SomeModelType = mutations.update(SomeModelInputPartial)
    delete_model: SomeModelType = mutations.delete(NodeInput)
```

Some things to note here:

- Those CUD mutations accept the same arguments as `@strawberry_django.mutation`
  accepts. This allows you to pass `handle_django_errors=True` to it for example.
- The mutation will receive the type in an argument named `"data"` by default.
  To change it to `"info"` for example, you can change it by passing
  `argument_name="info"` to the mutation, or set `MUTATIONS_DEFAULT_ARGUMENT_NAME="info"`
  in your [strawberry django settings](../settings) to make it the default when not provided.
- Take note that inputs using `partial` will _not_ automatically mark non-auto fields optional
  and instead will respect explicit type annotations;
  see [partial input types](./types.md#input-types) documentation for examples.
- I's also possible to update or delete model by using unique identifier other than id by providing `key_attr` property :

```{.python}
@strawberry_django.partial(SomeModel)
class SomeModelInputPartial:
    unique_field: strawberry.auto

@strawberry_django.type
class Mutation:
    update_model: SomeModelType = mutations.update(
        SomeModelInputPartial,
        key_attr="unique_field",
    )
    delete_model: SomeModelType = mutations.delete(
        SomeModelInputPartial,
        key_attr="unique_field",
    )
```

## Filtering

!!! danger

    This is totally discouraged as it allows for any issue with the filters
    to be able to alter your whole model collection.

    **You have been warned!**

Filters can be added to update and delete mutations. More information in the
[filtering](filters.md) section.

```{.python title=schema.py}
import strawberry_django

@strawberry_django.type
class Mutation:
    updateFruits: List[Fruit] = strawberry_django.mutations.update(FruitPartialInput, filters=FruitFilter)
    deleteFruits: List[Fruit] = strawberry_django.mutations.delete(filters=FruitFilter)

schema = strawberry.Schema(mutation=Mutation)
```
