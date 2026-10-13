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


def test_get_payload_batched_response():
    response = HttpResponse(
        json.dumps([{"data": {"a": 1}}, {"data": {"b": 2}}]),
        content_type="application/json",
    )
    payload = _get_payload(None, response, _toolbar())  # type: ignore
    assert isinstance(payload, list)
    assert [r["debugToolbar"]["requestId"] for r in payload] == ["abc", "abc"]
