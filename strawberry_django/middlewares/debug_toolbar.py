# Based on https://github.com/flavors/django-graphiql-debug-toolbar

import collections
import json

from debug_toolbar.middleware import (
    DebugToolbarMiddleware as _DebugToolbarMiddleware,
)
from debug_toolbar.toolbar import DebugToolbar
from django.core.serializers.json import DjangoJSONEncoder
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.template.loader import render_to_string
from django.utils.encoding import force_str
from strawberry.django.views import BaseView
from typing_extensions import override

_HTML_TYPES = {"text/html", "application/xhtml+xml"}


def _get_payload(
    request: HttpRequest,
    response: HttpResponse,
    toolbar: DebugToolbar,
) -> dict | None:
    if not toolbar.request_id:
        return None

    content = force_str(response.content, encoding=response.charset)
    payload = json.loads(content, object_pairs_hook=collections.OrderedDict)
    payload["debugToolbar"] = collections.OrderedDict(
        [("panels", collections.OrderedDict())],
    )
    payload["debugToolbar"]["requestId"] = toolbar.request_id

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


class DebugToolbarMiddleware(_DebugToolbarMiddleware):
    def process_view(self, request: HttpRequest, view_func, *args, **kwargs):
        view = getattr(view_func, "view_class", None)
        request._is_graphiql = bool(view and issubclass(view, BaseView))  # type: ignore

    @override
    def _postprocess(
        self,
        request: HttpRequest,
        response: HttpResponse,
        toolbar: DebugToolbar,
    ) -> HttpResponse:
        response = super()._postprocess(request, response, toolbar)

        if response.streaming:
            return response

        content_type = response.get("Content-Type", "").split(";")[0]
        is_html = content_type in _HTML_TYPES
        is_graphiql = getattr(request, "_is_graphiql", False)

        if is_html and is_graphiql and response.status_code == 200:  # noqa: PLR2004
            template = render_to_string("strawberry_django/debug_toolbar.html")
            response.write(template)
            if "Content-Length" in response:  # type: ignore
                response["Content-Length"] = len(response.content)

        if is_html or not is_graphiql or content_type != "application/json":
            return response

        try:
            operation_name = json.loads(request.body).get("operationName")
        except Exception:  # noqa: BLE001
            operation_name = None

        # Do not return the payload for introspection queries, otherwise IDEs such as
        # apollo sandbox that query the introspection all the time will remove older
        # results from the history.
        payload = (
            _get_payload(request, response, toolbar)
            if operation_name != "IntrospectionQuery"
            else None
        )
        if payload is None:
            return response

        response.content = json.dumps(payload, cls=DjangoJSONEncoder)  # type: ignore
        if "Content-Length" in response:  # type: ignore
            response["Content-Length"] = len(response.content)

        return response
