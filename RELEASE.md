Release type: minor

Pass `Info` instead of `GraphQLResolveInfo` to callables provided in `prefetch_related` and `annotate` arguments of `strawberry_django.field`.

This is technically a breaking change because the argument type passed to these callables has changed. However, `Info` acts as a proxy for `GraphQLResolveInfo` and is compatible with the utilities typically used within prefetch or annotate functions, such as `optimize`.
