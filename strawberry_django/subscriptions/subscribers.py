from typing import Any, AsyncGenerator

from django.db.models import Model
from strawberry.relay.types import GlobalID
from strawberry.types import Info

from .publishers import ModelInstanceSubscribePublisher


async def model_subscriber(
    info: Info, pk: GlobalID, model: Model
) -> AsyncGenerator[Any, None]:
    """Connect your model changes to the subscription workflow.

    It can be used like to:

    ```
    from strawberry_django.subscriptions.subscribers import Subscription, AsyncGenerator, Info,\
        model_subscriber, subscription

    class Subscription:
        @subscription
        async def company(self, info: Info, pk: str) -> AsyncGenerator[MyModelType, None]:
            async for i in model_subscriber(info=info, pk=pk, model=MyModel):
                yield i
    ```

    Where you replace `MyModel` and `MyModelType` by your Model and strawberry ModelType.

    """
    publisher = ModelInstanceSubscribePublisher(info=info, pk=pk, model=model)
    async for msg in publisher.await_messages():
        yield msg
