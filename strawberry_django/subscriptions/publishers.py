from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from django.core.exceptions import ValidationError
from django.db.models import Model
from strawberry.relay.types import GlobalID
from strawberry.relay.utils import from_base64
from strawberry.types import Info

from strawberry_django.auth.utils import get_current_user

from .utils import get_group, get_msg, get_msg_type


class ModelInstanceSubscribePublisher:
    """Publishing updated instances to graphql subscriptions.

    It expects to be called with the Info context from strawberry django,
    the instance pk and the model.

    It can be used like so:
    ```
    publisher = ModelInstanceSubscribePublisher(info=info, pk=pk, model=model)
    async for msg in publisher.await_messages():
        yield msg
    ```

    """

    def __init__(self, info: Info, pk: GlobalID, model: Model):
        self.info = info
        self.pk = pk
        self.model = model

        self.ws = info.context["ws"]
        self.channel_layer = self.ws.channel_layer

    async def verify_logged_in(self):
        user = get_current_user(self.info)

        if user.is_anonymous:
            raise ValidationError("Anynomous users are not allowed to subscribe.")

    async def verify_return_type(self):
        return_type = self.info.return_type.__name__
        requested_type = self.decode_global_id_type()

        if return_type != requested_type:
            msg = (
                f"Requested GlobalID of type {return_type} instead of {requested_type}"
            )
            raise TypeError(msg)

    def get_queryset(self):
        return self.model.objects.all()

    def get_instance(self, pk):
        return self.get_queryset().get(pk=pk)

    def decode_global_id_type(self):
        global_id_type, _ = from_base64(self.pk)
        return global_id_type

    def decode_pk(self):
        _, pk = from_base64(self.pk)
        return pk

    @database_sync_to_async
    def set_instance(self):
        pk = self.decode_pk()
        instance = self.get_instance(pk)
        self.instance = instance

    @sync_to_async
    def refresh_instance(self):
        self.instance.refresh_from_db()
        return self.instance

    @property
    def group(self):
        return get_group(self.instance)

    @property
    def msg_type(self):
        return get_msg_type(self.instance)

    @property
    def msg(self):
        return get_msg(self.instance)

    async def subscribe(self):
        await self.channel_layer.group_add(self.group, self.ws.channel_name)

    async def send_message(self):
        await self.channel_layer.group_send(group=self.group, message=self.msg)

    async def send_initial_message(self):
        await self.send_message()

    async def await_messages(self):
        await self.verify_logged_in()
        await self.verify_return_type()
        await self.set_instance()
        await self.subscribe()
        await self.send_initial_message()

        async with self.ws.listen_to_channel(
            type=self.msg_type, groups=[self.group]
        ) as channel_messages:
            async for _ in channel_messages:
                yield await self.refresh_instance()
