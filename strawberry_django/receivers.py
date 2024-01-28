import contextlib.suppress

from django.db.models.signals import post_save
from django.dispatch import receiver

from strawberry_django.subscriptions.receivers import refresh_subscription_receiver


@receiver(post_save)
def strawberry_django__refresh_subscription(sender, instance, **kwargs):
    """Refresh subscriptions for every subscribed model upon a post_save."""
    with contextlib.suppress(AttributeError):
        # We take a very greedy approach to post_save signals.
        # Since there are many post_save signals going around in Django,
        # of which many can fail if they are not models as we use them in our apps.
        # That's why we don't let AttributeErrors fail our method.
        refresh_subscription_receiver(instance)
