import json
from types import SimpleNamespace

from django.http import HttpResponse

from strawberry_django.middlewares.debug_toolbar import _get_payload  # ruff: ignore[import-private-name]


def _toolbar():
    return SimpleNamespace(request_id="abc", enabled_panels=[])


def test_get_payload_single_response():
    response = HttpResponse(b'{"data": {"a": 1}}', content_type="application/json")
    payload = _get_payload(None, response, _toolbar())  # type: ignore
    assert payload["debugToolbar"]["requestId"] == "abc"  # type: ignore


def _run_postprocess(monkeypatch, body: bytes):
    from debug_toolbar.middleware import DebugToolbarMiddleware as Base

    from strawberry_django.middlewares.debug_toolbar import DebugToolbarMiddleware

    monkeypatch.setattr(
        Base, "_postprocess", lambda self, request, response, toolbar: response
    )
    request = SimpleNamespace(body=body, _is_graphiql=True)
    response = HttpResponse(b'[{"data": {"a": 1}}]', content_type="application/json")
    middleware = DebugToolbarMiddleware.__new__(DebugToolbarMiddleware)
    return middleware._postprocess(request, response, _toolbar())  # type: ignore


def test_batched_introspection_request_gets_no_payload(monkeypatch):
    body = json.dumps([{"operationName": "IntrospectionQuery", "query": "{ a }"}])
    response = _run_postprocess(monkeypatch, body.encode())
    assert b"debugToolbar" not in response.content


def test_batched_request_with_other_operation_gets_payload(monkeypatch):
    body = json.dumps([{"operationName": "IntrospectionQuery"}, {"operationName": "Q"}])
    response = _run_postprocess(monkeypatch, body.encode())
    assert b"debugToolbar" in response.content


def test_get_payload_batched_response():
    response = HttpResponse(
        json.dumps([{"data": {"a": 1}}, {"data": {"b": 2}}]),
        content_type="application/json",
    )
    payload = _get_payload(None, response, _toolbar())  # type: ignore
    assert isinstance(payload, list)
    assert [r["debugToolbar"]["requestId"] for r in payload] == ["abc", "abc"]
