from functools import _make_key

from django.core.cache import caches
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from strawberry.extensions.base_extension import Extension


class DjangoCacheBase(Extension):
    def __init__(self, cache_name="default", timeout=DEFAULT_TIMEOUT, hash_fn=None):
        self.cache = caches[cache_name]
        self.timeout = timeout
        # Use same key generating function as functools.lru_cache as default
        self.hash_fn = hash_fn or _make_key

    def execute_cached(self, func, *args, **kwargs):
        hash_key = self.hash_fn(args, kwargs, False)
        cache_result = self.cache.get(hash_key)
        if cache_result is not None:
            return cache_result
        func_result = func(*args, **kwargs)
        self.cache.set(hash_key, func_result, timeout=self.timeout)
        return func_result
