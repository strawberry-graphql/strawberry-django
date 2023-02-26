import functools
import inspect

from asgiref.sync import sync_to_async
from django.db import models

from . import utils


def django_resolver(resolver):
    """Django resolver for handling both sync and async.

    This decorator is used to make sure that resolver is always called from
    sync context.  sync_to_async helper in used if function is called from
    async context. This is useful especially with Django ORM, which does not
    support async. Coroutines are not wrapped.
    """
    if inspect.iscoroutinefunction(resolver) or inspect.isasyncgenfunction(resolver):
        return resolver

    @functools.wraps(resolver)
    def wrapper(*args, **kwargs):
        if utils.is_async():
            return call_sync_resolver(resolver, *args, **kwargs)

        return resolver(*args, **kwargs)

    return wrapper


def sync_to_async_thread_sensitive(func):
    # django 3.0 defaults to thread_sensitive=False
    return sync_to_async(func, thread_sensitive=True)


@sync_to_async_thread_sensitive
def call_sync_resolver(resolver, *args, **kwargs):
    """Safe resolve a sync resolver.

    This function executes resolver function in sync context and ensures
    that querysets are executed.
    """
    result = resolver(*args, **kwargs)
    return list(result) if isinstance(result, models.QuerySet) else result
