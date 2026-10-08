---
release type: minor
---

Filter and order methods, declared with `@strawberry_django.filter_field` or `@strawberry_django.order_field`, no longer use Strawberry's field resolver. The method is now stored in the field's `filter_order_resolver` attribute instead of `base_resolver`, as input fields aren't resolved. This prepares for Strawberry raising an error for input types with fields that have resolvers (strawberry-graphql/strawberry#4682).

Code that reads `base_resolver` on these fields should use `filter_order_resolver` instead.

strawberry-graphql 0.330.3 or newer is now required, as class and static methods used as filter or order methods are bound with Strawberry's `StrawberryResolver.bind`, like Strawberry does for resolvers.
