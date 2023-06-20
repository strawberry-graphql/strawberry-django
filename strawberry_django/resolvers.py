import functools
import inspect
from typing import Any, Callable, TypeVar, overload

from asgiref.sync import sync_to_async
from django.db import models
from django.db.models.manager import BaseManager
from graphql.pyutils import AwaitableOrValue
from strawberry.utils.inspect import in_async_context
from typing_extensions import ParamSpec

_SENTINEL = object()
_T = TypeVar("_T")
_R = TypeVar("_R")
_P = ParamSpec("_P")
_M = TypeVar("_M", bound=models.Model)


def default_qs_hook(qs: models.QuerySet[_M]) -> models.QuerySet[_M]:
    # This is what QuerySet does internally to fetch results.
    # After this, iterating over the queryset should be async safe
    qs._fetch_all()  # type: ignore
    return qs


@overload
def django_resolver(
    f: Callable[_P, _R],
    *,
    qs_hook: Callable[[models.QuerySet[_M]], Any] = default_qs_hook,
) -> Callable[_P, AwaitableOrValue[_R]]:
    ...


@overload
def django_resolver(
    f: None,
    *,
    qs_hook: Callable[[models.QuerySet[_M]], Any] = default_qs_hook,
) -> Callable[[Callable[_P, _R]], Callable[_P, AwaitableOrValue[_R]]]:
    ...


def django_resolver(
    f=None,
    *,
    qs_hook: Callable[[models.QuerySet[_M]], Any] = default_qs_hook,
):
    """Django resolver for handling both sync and async.

    This decorator is used to make sure that resolver is always called from
    sync context.  sync_to_async helper in used if function is called from
    async context. This is useful especially with Django ORM, which does not
    support async. Coroutines are not wrapped.
    """

    def wrapper(resolver):
        if inspect.iscoroutinefunction(resolver) or inspect.isasyncgenfunction(
            resolver,
        ):
            return resolver

        def sync_resolver(*args, **kwargs):
            retval = resolver(*args, **kwargs)

            if callable(retval):
                retval = retval()

            if isinstance(retval, BaseManager):
                retval = retval.all()

            if isinstance(retval, models.QuerySet):
                retval = qs_hook(retval)

            return retval

        async_resolver = sync_to_async(sync_resolver)

        @functools.wraps(resolver)
        def inner_wrapper(*args, **kwargs):
            f = async_resolver if in_async_context() else sync_resolver
            return f(*args, **kwargs)

        return inner_wrapper

    if f is not None:
        return wrapper(f)

    return wrapper


@overload
def django_getattr(
    obj: Any,
    name: str,
    *,
    qs_hook: Callable[[models.QuerySet[_M]], Any] = default_qs_hook,
) -> AwaitableOrValue[Any]:
    ...


@overload
def django_getattr(
    obj: Any,
    name: str,
    default: Any,
    *,
    qs_hook: Callable[[models.QuerySet[_M]], Any] = default_qs_hook,
) -> AwaitableOrValue[Any]:
    ...


def django_getattr(
    obj: Any,
    name: str,
    default: Any = _SENTINEL,
    *,
    qs_hook: Callable[[models.QuerySet[_M]], Any] = default_qs_hook,
):
    args = (default,) if default is not _SENTINEL else ()
    return django_resolver(getattr, qs_hook=qs_hook)(  # type: ignore
        obj,
        name,
        *args,
    )
