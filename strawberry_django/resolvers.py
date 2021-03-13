from django.db import models
from asgiref.sync import sync_to_async
import functools
from . import utils


# decorator which is used with async views to secure django orm calls to
# be done in sync context. django orm does not support async yet
def django_resolver(resolver=None):
    @functools.wraps(resolver)
    def wrapper(*args, **kwargs):
        if utils.is_async():
            return sync_to_async(call_resolver, thread_sensitive=True)(resolver, *args, **kwargs)
        else:
            return resolver(*args, **kwargs)
    return wrapper


def call_resolver(resolver, *args, **kwargs):
    result = resolver(*args, **kwargs)
    if isinstance(result, models.QuerySet):
        result = list(result)
    return result
