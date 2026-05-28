"""Video provider edge — PUT /courses/{courseId}/lessons/{lessonId}/video-ready (slice 2)."""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from video_catalog_invoke import CatalogInvokeError
from video_edge_config import VideoProviderEdgeConfig
from kinescope_http import KinescopeVideoMetadata
from video_provider_edge._imports import video_edge_handler

_COURSE_ID = "11111111-1111-4111-8111-111111111111"
_LESSON_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
_USER_SUB = "teacher-sub-1"
_VIDEO_KEY = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
_VIDEO_READY_PATH = f"/courses/{_COURSE_ID}/lessons/{_LESSON_ID}/video-ready"


def _edge_config(**overrides: Any) -> VideoProviderEdgeConfig:
    base: Dict[str, Any] = {
        "deployment_environment": "dev",
        "catalog_lambda_arn": "arn:aws:lambda:eu-west-1:1:function:catalog",
        "kinescope_api_token": "kinescope-token",
        "kinescope_parent_id": "parent-id",
        "kinescope_webhook_secret": None,
        "cors_allow_origin": None,
    }
    base.update(overrides)
    return VideoProviderEdgeConfig(**base)


def _mark_ready_event(**overrides: Any) -> Dict[str, Any]:
    evt: Dict[str, Any] = {
        "httpMethod": "PUT",
        "path": _VIDEO_READY_PATH,
        "requestContext": {
            "resourcePath": _VIDEO_READY_PATH,
            "stage": "dev",
            "authorizer": {
                "claims": {"sub": _USER_SUB, "custom:role": "teacher"},
            },
        },
        "headers": {"content-type": "application/json", "Origin": "https://teacher.example.com"},
        "body": "{}",
    }
    evt.update(overrides)
    return evt


def _parse_body(resp: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(resp["body"])


def test_mark_ready_dev_bypass_when_metadata_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepare_calls: list[Dict[str, Any]] = []
    apply_calls: list[Dict[str, Any]] = []
    fetch_calls: list[Dict[str, Any]] = []

    monkeypatch.setattr(video_edge_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(
        video_edge_handler,
        "_invoke_video_prepare_mark_ready",
        lambda **kw: prepare_calls.append(kw)
        or {"courseId": _COURSE_ID, "lessonId": _LESSON_ID, "videoKey": _VIDEO_KEY},
    )
    monkeypatch.setattr(
        video_edge_handler,
        "_fetch_kinescope_metadata",
        lambda **kw: fetch_calls.append(kw) or None,
    )
    monkeypatch.setattr(
        video_edge_handler,
        "_invoke_video_apply_mark_ready",
        lambda **kw: apply_calls.append(kw)
        or {"lessonId": _LESSON_ID, "videoStatus": "ready"},
    )

    resp = video_edge_handler.lambda_handler(_mark_ready_event(), None)

    assert resp["statusCode"] == 200
    assert _parse_body(resp) == {"lessonId": _LESSON_ID, "videoStatus": "ready"}
    assert prepare_calls[0]["user_sub"] == _USER_SUB
    assert prepare_calls[0]["course_id"] == _COURSE_ID
    assert fetch_calls[0]["video_id"] == _VIDEO_KEY
    assert apply_calls[0]["video_key"] == _VIDEO_KEY
    assert apply_calls[0]["provider_metadata"] is None
    assert apply_calls[0]["provider_metadata_supplied"] is False


def test_mark_ready_uses_literal_path_when_resource_path_is_template(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepare_calls: list[Dict[str, Any]] = []

    monkeypatch.setattr(video_edge_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(
        video_edge_handler,
        "_invoke_video_prepare_mark_ready",
        lambda **kw: prepare_calls.append(kw)
        or {"courseId": _COURSE_ID, "lessonId": _LESSON_ID, "videoKey": _VIDEO_KEY},
    )
    monkeypatch.setattr(
        video_edge_handler,
        "_invoke_video_apply_mark_ready",
        lambda **kw: {"lessonId": _LESSON_ID, "videoStatus": "ready"},
    )
    monkeypatch.setattr(
        video_edge_handler,
        "_fetch_kinescope_metadata",
        lambda **kw: None,
    )

    evt = _mark_ready_event()
    evt["requestContext"] = {
        "resourcePath": "/courses/{courseId}/lessons/{lessonId}/video-ready",
        "stage": "dev",
        "authorizer": {"claims": {"sub": _USER_SUB, "custom:role": "teacher"}},
    }
    evt["path"] = _VIDEO_READY_PATH

    resp = video_edge_handler.lambda_handler(evt, None)

    assert resp["statusCode"] == 200
    assert prepare_calls[0]["course_id"] == _COURSE_ID
    assert prepare_calls[0]["lesson_id"] == _LESSON_ID


def test_mark_ready_prod_passes_verified_metadata_to_catalog(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metadata = KinescopeVideoMetadata(status="done", duration_seconds=90)
    apply_calls: list[Dict[str, Any]] = []

    monkeypatch.setattr(
        video_edge_handler,
        "_load_config",
        lambda: _edge_config(deployment_environment="prod"),
    )
    monkeypatch.setattr(
        video_edge_handler,
        "_invoke_video_prepare_mark_ready",
        lambda **kw: {"courseId": _COURSE_ID, "lessonId": _LESSON_ID, "videoKey": _VIDEO_KEY},
    )
    monkeypatch.setattr(
        video_edge_handler,
        "_fetch_kinescope_metadata",
        lambda **kw: metadata,
    )
    monkeypatch.setattr(
        video_edge_handler,
        "_invoke_video_apply_mark_ready",
        lambda **kw: apply_calls.append(kw)
        or {"lessonId": _LESSON_ID, "videoStatus": "ready", "duration": 90},
    )

    resp = video_edge_handler.lambda_handler(_mark_ready_event(), None)

    assert resp["statusCode"] == 200
    assert apply_calls[0]["video_key"] == _VIDEO_KEY
    assert apply_calls[0]["provider_metadata"] == {"status": "done", "durationSeconds": 90}
    assert apply_calls[0]["provider_metadata_supplied"] is True


def test_mark_ready_prod_rejects_when_still_processing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        video_edge_handler,
        "_load_config",
        lambda: _edge_config(deployment_environment="prod"),
    )
    monkeypatch.setattr(
        video_edge_handler,
        "_invoke_video_prepare_mark_ready",
        lambda **kw: {"courseId": _COURSE_ID, "lessonId": _LESSON_ID, "videoKey": _VIDEO_KEY},
    )
    monkeypatch.setattr(
        video_edge_handler,
        "_fetch_kinescope_metadata",
        lambda **kw: KinescopeVideoMetadata(status="pending", duration_seconds=None),
    )
    apply_mock = MagicMock()
    monkeypatch.setattr(video_edge_handler, "_invoke_video_apply_mark_ready", apply_mock)

    resp = video_edge_handler.lambda_handler(_mark_ready_event(), None)

    assert resp["statusCode"] == 400
    assert _parse_body(resp)["code"] == "video_not_ready"
    apply_mock.assert_not_called()


def test_mark_ready_returns_401_without_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(video_edge_handler, "_load_config", lambda: _edge_config())
    evt = _mark_ready_event()
    evt["requestContext"] = {"resourcePath": _VIDEO_READY_PATH}

    resp = video_edge_handler.lambda_handler(evt, None)
    assert resp["statusCode"] == 401
    assert _parse_body(resp)["code"] == "unauthorized"


def test_mark_ready_catalog_failure_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(video_edge_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(
        video_edge_handler,
        "_invoke_video_prepare_mark_ready",
        MagicMock(side_effect=CatalogInvokeError("catalog down")),
    )

    resp = video_edge_handler.lambda_handler(_mark_ready_event(), None)
    assert resp["statusCode"] == 503
    assert _parse_body(resp)["code"] == "video_unconfigured"
