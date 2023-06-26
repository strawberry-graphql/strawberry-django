from functools import _make_key
from typing import Callable, Dict, Hashable, Optional, Tuple, cast

from django.core.cache import caches
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from strawberry.extensions import SchemaExtension
from strawberry.types import ExecutionContext


class DjangoCacheBase(SchemaExtension):
    """Base for a Cache that uses Django built in cache instead of an in memory cache.

    Arguments:
    ---------
    `cache_name: str`
        Name of the Django Cache to use, defaults to 'default'

    `timeout: Optional[int]`
        How long to hold items in the cache. See the Django Cache docs for details
        https://docs.djangoproject.com/en/4.0/topics/cache/

    `hash_fn: Optional[Callable[[Tuple, Dict], str]]`
        A function to use to generate the cache keys
        Defaults to the same key generator as functools.lru_cache
        WARNING! The default function does NOT work with memcached
        and will generate warnings
    """

    def __init__(
        self,
        cache_name: str = "default",
        timeout: Optional[int] = None,
        hash_fn: Optional[Callable[[Tuple, Dict], Hashable]] = None,
        *,
        execution_context: Optional[ExecutionContext] = None,
    ):
        super().__init__(execution_context=cast(ExecutionContext, execution_context))

        self.cache = caches[cache_name]
        self.timeout = timeout or DEFAULT_TIMEOUT
        # Use same key generating function as functools.lru_cache as default
        self.hash_fn = hash_fn or (lambda args, kwargs: _make_key(args, kwargs, False))

    def execute_cached(self, func, *args, **kwargs):
        hash_key = cast(str, self.hash_fn(args, kwargs))
        cache_result = self.cache.get(hash_key)
        if cache_result is not None:
            return cache_result

        func_result = func(*args, **kwargs)
        self.cache.set(hash_key, func_result, timeout=self.timeout)
        return func_result
