# Based on https://github.com/flavors/django-graphiql-debug-toolbar

import asyncio
import collections
import contextlib
import inspect
import json
import weakref
from typing import Optional

from asgiref.sync import sync_to_async
from debug_toolbar.middleware import _HTML_TYPES, get_show_toolbar
from debug_toolbar.middleware import (
    DebugToolbarMiddleware as _DebugToolbarMiddleware,
)
from debug_toolbar.panels.sql.panel import SQLPanel
from debug_toolbar.panels.templates import TemplatesPanel
from debug_toolbar.toolbar import DebugToolbar
from django.core.exceptions import SynchronousOnlyOperation
from django.core.serializers.json import DjangoJSONEncoder
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.template.loader import render_to_string
from django.utils.encoding import force_str
from strawberry.django.views import BaseView

_store_cache = weakref.WeakKeyDictionary()
_debug_toolbar_map: "weakref.WeakKeyDictionary[HttpRequest, DebugToolbar]" = (
    weakref.WeakKeyDictionary()
)

_original_store = DebugToolbar.store
_original_debug_toolbar_init = DebugToolbar.__init__
_original_store_template_info = TemplatesPanel._store_template_info


def _is_websocket(request: HttpRequest):
    return (
        request.META.get("HTTP_UPGRADE") == "websocket"
        and request.META.get("HTTP_CONNECTION") == "Upgrade"
    )


def _debug_toolbar_init(self, request, *args, **kwargs):
    _debug_toolbar_map[request] = self
    _original_debug_toolbar_init(self, request, *args, **kwargs)
    self.config["RENDER_PANELS"] = False
    self.config["SKIP_TEMPLATE_PREFIXES"] = (
        *tuple(self.config.get("SKIP_TEMPLATE_PREFIXES", [])),
        "graphql/",
    )


def _store(toolbar: DebugToolbar):
    _debug_toolbar_map[toolbar.request] = toolbar
    _original_store(toolbar)
    _store_cache[toolbar.request] = toolbar.store_id


def _store_template_info(*args, **kwargs):
    with contextlib.suppress(SynchronousOnlyOperation):
        return _original_store_template_info(*args, **kwargs)


def _get_payload(request: HttpRequest, response: HttpResponse):
    store_id = _store_cache.get(request)
    if not store_id:
        return None

    toolbar: Optional[DebugToolbar] = DebugToolbar.fetch(store_id)
    if not toolbar:
        return None

    content = force_str(response.content, encoding=response.charset)
    payload = json.loads(content, object_pairs_hook=collections.OrderedDict)
    payload["debugToolbar"] = collections.OrderedDict(
        [("panels", collections.OrderedDict())],
    )
    payload["debugToolbar"]["storeId"] = toolbar.store_id

    for p in reversed(toolbar.enabled_panels):
        if p.panel_id == "TemplatesPanel":
            continue

        title = p.title if p.has_content else None

        sub = p.nav_subtitle
        payload["debugToolbar"]["panels"][p.panel_id] = {
            "title": title() if callable(title) else title,
            "subtitle": sub() if callable(sub) else sub,
        }

    return payload


DebugToolbar.__init__ = _debug_toolbar_init
DebugToolbar.store = _store  # type: ignore
TemplatesPanel._store_template_info = _store_template_info


class DebugToolbarMiddleware(_DebugToolbarMiddleware):
    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        self._original_get_response = get_response

        if inspect.iscoroutinefunction(get_response):
            self._is_coroutine = asyncio.coroutines._is_coroutine  # type: ignore

            def _get_response(request):
                toolbar = _debug_toolbar_map.pop(request, None)
                for panel in toolbar.enabled_panels if toolbar else []:
                    if isinstance(panel, SQLPanel):
                        sql_panel = panel
                        break
                else:
                    sql_panel = None

                async def _inner_get_response():
                    if sql_panel:
                        await sync_to_async(sql_panel.enable_instrumentation)()
                    try:
                        return await self._original_get_response(request)
                    finally:
                        if sql_panel:
                            await sync_to_async(sql_panel.disable_instrumentation)()

                return asyncio.run(_inner_get_response())

            get_response = _get_response
        else:
            self._is_coroutine = None

        super().__init__(get_response)

    def __call__(self, request: HttpRequest):
        if self._is_coroutine:
            return self.__acall__(request)

        if _is_websocket(request):
            return self._original_get_response(request)

        return self.process_request(request)

    async def __acall__(self, request: HttpRequest):  # noqa: PLW3201
        if _is_websocket(request):
            return await self._original_get_response(request)

        return await sync_to_async(self.process_request, thread_sensitive=False)(
            request,
        )

    def process_request(self, request: HttpRequest):
        response = super().__call__(request)

        show_toolbar = get_show_toolbar()
        if (
            callable(show_toolbar) and not show_toolbar(request)
        ) or DebugToolbar.is_toolbar_request(request):
            return response

        content_type = response.get("Content-Type", "").split(";")[0]
        is_html = content_type in _HTML_TYPES
        is_graphiql = getattr(request, "_is_graphiql", False)

        if is_html and is_graphiql and response.status_code == 200:  # noqa: PLR2004
            template = render_to_string("strawberry_django/debug_toolbar.html")
            response.write(template)
            if "Content-Length" in response:
                response["Content-Length"] = len(response.content)

        if is_html or not is_graphiql or content_type != "application/json":
            return response

        payload = _get_payload(request, response)
        if payload is None:
            return response

        response.content = json.dumps(payload, cls=DjangoJSONEncoder)
        if "Content-Length" in response:
            response["Content-Length"] = len(response.content)

        return response

    def process_view(self, request: HttpRequest, view_func, *args, **kwargs):
        view = getattr(view_func, "view_class", None)
        request._is_graphiql = bool(view and issubclass(view, BaseView))  # type: ignore
