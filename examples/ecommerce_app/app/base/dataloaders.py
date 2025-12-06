from __future__ import annotations

import dataclasses

from app.product.models import Brand
from app.user.models import User
from asgiref.sync import sync_to_async
from strawberry.dataloader import DataLoader


async def load_brands(keys: list[int]) -> list[Brand | None]:
    """Batch load brands by their IDs."""
    brands = await sync_to_async(list)(Brand.objects.filter(id__in=keys))

    # Return results in the same order as keys
    brand_map = {brand.id: brand for brand in brands}
    return [brand_map.get(key) for key in keys]


async def load_users(keys: list[int]) -> list[User | None]:
    """Batch load users by their IDs."""
    users = await sync_to_async(list)(User.objects.filter(id__in=keys))

    # Return results in the same order as keys
    user_map = {user.id: user for user in users}
    return [user_map.get(key) for key in keys]


@dataclasses.dataclass
class DataLoaders:
    """Container for all dataloaders in the application.

    DataLoaders help solve the N+1 query problem by batching and caching database queries.
    Each loader is instantiated once per request and shared across all resolvers.
    """

    brand_loader: DataLoader[int, Brand | None] = dataclasses.field(
        default_factory=lambda: DataLoader(load_fn=load_brands)
    )
    user_loader: DataLoader[int, User | None] = dataclasses.field(
        default_factory=lambda: DataLoader(load_fn=load_users)
    )
