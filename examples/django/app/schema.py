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
Mutation = merge_types(
    "Mutation",
    (
        OrderMutation,
        ProductMutation,
        UserMutation,
    ),
)


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    extensions=[
        DjangoOptimizerExtension,
    ],
)
