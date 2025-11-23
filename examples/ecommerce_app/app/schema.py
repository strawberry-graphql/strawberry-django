"""Root GraphQL schema merging all app-specific schemas.

This module demonstrates the modular schema pattern where each Django app
defines its own queries and mutations, which are then merged into a single
root schema using strawberry.tools.merge_types.

Benefits of this approach:
- Clear separation of concerns
- Easy to add/remove features
- Schemas stay focused and maintainable
- Each app is self-contained
"""

import strawberry
from app.order.schema import Mutation as OrderMutation
from app.order.schema import Query as OrderQuery
from app.product.schema import Mutation as ProductMutation
from app.product.schema import Query as ProductQuery
from app.user.schema import Mutation as UserMutation
from app.user.schema import Query as UserQuery
from strawberry.tools import merge_types

from strawberry_django.optimizer import DjangoOptimizerExtension

Query = merge_types(
    "Query",
    (
        OrderQuery,
        ProductQuery,
        UserQuery,
    ),
)
"""Root Query type combining all app-specific queries.

Available queries:
- User queries: user, users, me
- Product queries: product, products, productsConn
- Order queries: ordersConn, myOrders, myCart
"""

Mutation = merge_types(
    "Mutation",
    (
        OrderMutation,
        ProductMutation,
        UserMutation,
    ),
)
"""Root Mutation type combining all app-specific mutations.

Available mutations:
- User mutations: login, logout
- Cart mutations: cartAddItem, cartUpdateItem, cartRemoveItem, cartCheckout
"""


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    extensions=[
        DjangoOptimizerExtension,
    ],
)
"""Main GraphQL schema with DjangoOptimizerExtension.

The DjangoOptimizerExtension automatically optimizes database queries by:
- Analyzing the GraphQL query and selecting only needed fields
- Using select_related() for foreign keys
- Using prefetch_related() for many-to-many and reverse foreign keys
- Respecting optimization hints from @model_property and field decorators
"""
