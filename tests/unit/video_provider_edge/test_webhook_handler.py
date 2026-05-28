"""Video provider edge — POST /webhooks/kinescope (slice 3)."""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from video_catalog_invoke import CatalogInvokeError
from video_edge_config import VideoProviderEdgeConfig
from kinescope_http import KinescopeVideoMetadata
from video_provider_edge._imports import video_edge_handler

_WEBHOOK_PATH = "/webhooks/kinescope"
_VIDEO_ID = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
_COURSE_ID = "11111111-1111-4111-8111-111111111111"
_LESSON_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
_WEBHOOK_SECRET = "expected-webhook-secret"


def _edge_config(**overrides: Any) -> VideoProviderEdgeConfig:
    base: Dict[str, Any] = {
        "deployment_environment": "dev",
        "catalog_lambda_arn": "arn:aws:lambda:eu-west-1:1:function:catalog",
        "kinescope_api_token": "kinescope-token",
        "kinescope_parent_id": "parent-id",
        "kinescope_webhook_secret": _WEBHOOK_SECRET,
        "cors_allow_origin": None,
    }
    base.update(overrides)
    return VideoProviderEdgeConfig(**base)


def _webhook_event(**overrides: Any) -> Dict[str, Any]:
    evt: Dict[str, Any] = {
        "httpMethod": "POST",
        "path": _WEBHOOK_PATH,
        "requestContext": {"resourcePath": _WEBHOOK_PATH},
        "headers": {
            "content-type": "application/json",
            "x-kinescope-webhook-secret": _WEBHOOK_SECRET,
        },
        "body": json.dumps(
            {
                "event": "media.update.status",
                "data": {"id": _VIDEO_ID, "status": "done"},
            }
        ),
    }
    evt.update(overrides)
    return evt


def _parse_body(resp: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(resp["body"])


def test_webhook_unknown_video_id_returns_200_no_op(monkeypatch: pytest.MonkeyPatch) -> None:
    invoke_calls: list[Dict[str, Any]] = []

    monkeypatch.setattr(video_edge_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(
        video_edge_handler,
        "_fetch_kinescope_metadata",
        lambda **kw: KinescopeVideoMetadata(status="done", duration_seconds=90),
    )
    monkeypatch.setattr(
        video_edge_handler,
        "_invoke_video_webhook_status",
        lambda **kw: invoke_calls.append(kw) or {"ignored": True},
    )

    resp = video_edge_handler.lambda_handler(_webhook_event(), None)

    assert resp["statusCode"] == 200
    assert _parse_body(resp) == {"ignored": True}
    assert len(invoke_calls) == 1
    assert invoke_calls[0]["provider_metadata_supplied"] is True
    assert invoke_calls[0]["provider_metadata"] == {
        "status": "done",
        "durationSeconds": 90,
    }


def test_webhook_spoofed_done_rejected_when_api_says_not_done(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invoke_mock = MagicMock()

    monkeypatch.setattr(video_edge_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(
        video_edge_handler,
        "_fetch_kinescope_metadata",
        lambda **kw: KinescopeVideoMetadata(status="processing", duration_seconds=None),
    )
    monkeypatch.setattr(video_edge_handler, "_invoke_video_webhook_status", invoke_mock)

    resp = video_edge_handler.lambda_handler(_webhook_event(), None)

    assert resp["statusCode"] == 200
    assert _parse_body(resp) == {"ignored": True, "reason": "status_mismatch"}
    invoke_mock.assert_not_called()


def test_webhook_valid_done_applies_ready_via_catalog_internal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invoke_calls: list[Dict[str, Any]] = []

    monkeypatch.setattr(video_edge_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(
        video_edge_handler,
        "_fetch_kinescope_metadata",
        lambda **kw: KinescopeVideoMetadata(status="done", duration_seconds=120),
    )
    monkeypatch.setattr(
        video_edge_handler,
        "_invoke_video_webhook_status",
        lambda **kw: invoke_calls.append(kw)
        or {
            "courseId": _COURSE_ID,
            "lessonId": _LESSON_ID,
            "videoStatus": "ready",
            "duration": 120,
        },
    )

    resp = video_edge_handler.lambda_handler(_webhook_event(), None)

    assert resp["statusCode"] == 200
    body = _parse_body(resp)
    assert body["videoStatus"] == "ready"
    assert body["duration"] == 120
    assert invoke_calls[0]["webhook_payload"]["data"]["id"] == _VIDEO_ID
    assert invoke_calls[0]["provider_metadata_supplied"] is True
    assert invoke_calls[0]["provider_metadata"]["status"] == "done"
    assert invoke_calls[0]["provider_metadata"]["durationSeconds"] == 120


def test_webhook_missing_secret_rejected_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invoke_mock = MagicMock()
    monkeypatch.setattr(video_edge_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(video_edge_handler, "_invoke_video_webhook_status", invoke_mock)

    evt = _webhook_event()
    evt["headers"] = {"content-type": "application/json"}

    resp = video_edge_handler.lambda_handler(evt, None)

    assert resp["statusCode"] == 401
    assert _parse_body(resp)["code"] == "unauthorized"
    invoke_mock.assert_not_called()


def test_webhook_catalog_invoke_failure_returns_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(video_edge_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(
        video_edge_handler,
        "_fetch_kinescope_metadata",
        lambda **kw: KinescopeVideoMetadata(status="done", duration_seconds=60),
    )
    monkeypatch.setattr(
        video_edge_handler,
        "_invoke_video_webhook_status",
        MagicMock(side_effect=CatalogInvokeError("catalog down")),
    )

    resp = video_edge_handler.lambda_handler(_webhook_event(), None)

    assert resp["statusCode"] == 500
    assert _parse_body(resp)["code"] == "internal_error"


def test_options_webhook_returns_204_with_cors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(video_edge_handler, "_load_config", lambda: _edge_config())
    evt = {
        "httpMethod": "OPTIONS",
        "path": _WEBHOOK_PATH,
        "requestContext": {"resourcePath": _WEBHOOK_PATH},
        "headers": {"Origin": "https://teacher.example.com"},
    }

    resp = video_edge_handler.lambda_handler(evt, None)
    assert resp["statusCode"] == 204
    assert resp["headers"]["Access-Control-Allow-Origin"] == "https://teacher.example.com"
