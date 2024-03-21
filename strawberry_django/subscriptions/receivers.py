import channels.layers
from asgiref.sync import async_to_sync

from .utils import get_group, get_msg


def refresh_subscription_receiver(instance):
    group = get_group(instance)
    msg = get_msg(instance)

    channel_layer = channels.layers.get_channel_layer()
    async_to_sync(channel_layer.group_send)(group=group, message=msg)
