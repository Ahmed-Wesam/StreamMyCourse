"""Unit tests for Kinescope webhook HTTP adapter security."""

from __future__ import annotations

from unittest.mock import MagicMock

from services.course_management.video_webhooks import handle_kinescope_webhook


def _event(*, secret_header: str = "", query_token: str = "") -> dict:
    headers = {}
    if secret_header:
        headers["x-kinescope-webhook-secret"] = secret_header
    qs = {"token": query_token} if query_token else None
    return {
        "requestContext": {"http": {"method": "POST"}},
        "headers": headers,
        "queryStringParameters": qs,
        "body": '{"event":"media.update.status","data":{"id":"v1","status":"done"}}',
    }


def test_webhook_rejects_missing_secret_when_configured() -> None:
    svc = MagicMock()
    resp = handle_kinescope_webhook(
        _event(),
        origin="*",
        svc=svc,
        webhook_secret="expected-secret",
    )
    assert resp["statusCode"] == 401
    svc.handle_kinescope_media_status.assert_not_called()


def test_webhook_accepts_matching_header_secret() -> None:
    svc = MagicMock()
    svc.handle_kinescope_media_status.return_value = {"ignored": True}
    resp = handle_kinescope_webhook(
        _event(secret_header="expected-secret"),
        origin="*",
        svc=svc,
        webhook_secret="expected-secret",
    )
    assert resp["statusCode"] == 200
    svc.handle_kinescope_media_status.assert_called_once()


def test_webhook_accepts_matching_query_token() -> None:
    svc = MagicMock()
    svc.handle_kinescope_media_status.return_value = {"ignored": True}
    resp = handle_kinescope_webhook(
        _event(query_token="expected-secret"),
        origin="*",
        svc=svc,
        webhook_secret="expected-secret",
    )
    assert resp["statusCode"] == 200
