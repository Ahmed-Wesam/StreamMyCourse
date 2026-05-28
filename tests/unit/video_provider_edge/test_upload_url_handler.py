"""Video provider edge — POST /upload-url (slice 1)."""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from video_catalog_invoke import CatalogInvokeError, CatalogInvokeHttpError
from video_edge_config import VideoProviderEdgeConfig
from kinescope_http import KinescopeUploadInit
from video_provider_edge._imports import video_edge_handler

_COURSE_ID = "11111111-1111-4111-8111-111111111111"
_LESSON_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
_USER_SUB = "teacher-sub-1"
_VIDEO_KEY = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
_UPLOAD_URL = "https://uploader.kinescope.io/upload/abc123"


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


def _upload_event(**overrides: Any) -> Dict[str, Any]:
    evt: Dict[str, Any] = {
        "httpMethod": "POST",
        "path": "/upload-url",
        "requestContext": {
            "resourcePath": "/upload-url",
            "stage": "dev",
            "authorizer": {
                "claims": {"sub": _USER_SUB, "custom:role": "teacher"},
            },
        },
        "headers": {"content-type": "application/json", "Origin": "https://teacher.example.com"},
        "body": json.dumps(
            {
                "courseId": _COURSE_ID,
                "lessonId": _LESSON_ID,
                "filename": "lecture.mp4",
                "contentType": "video/mp4",
                "filesize": 1024,
            }
        ),
    }
    evt.update(overrides)
    return evt


def _parse_body(resp: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(resp["body"])


def _prepare_ok(**overrides: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "courseId": _COURSE_ID,
        "lessonId": _LESSON_ID,
        "filename": "lecture.mp4",
        "contentType": "video/mp4",
        "filesize": 1024,
        "expectedVideoKey": "",
    }
    payload.update(overrides)
    return payload


def test_upload_url_returns_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    prepare_calls: list[Dict[str, Any]] = []
    commit_calls: list[Dict[str, Any]] = []
    kinescope_calls: list[Dict[str, Any]] = []

    monkeypatch.setattr(video_edge_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(
        video_edge_handler,
        "_invoke_video_prepare_upload",
        lambda **kw: prepare_calls.append(kw) or _prepare_ok(),
    )
    monkeypatch.setattr(
        video_edge_handler,
        "_invoke_video_commit_pending_upload",
        lambda **kw: commit_calls.append(kw) or {"committed": True},
    )
    monkeypatch.setattr(
        video_edge_handler,
        "_init_kinescope_upload",
        lambda **kw: kinescope_calls.append(kw)
        or KinescopeUploadInit(
            upload_url=_UPLOAD_URL,
            video_key=_VIDEO_KEY,
            upload_method="post",
        ),
    )

    resp = video_edge_handler.lambda_handler(_upload_event(), None)

    assert resp["statusCode"] == 200
    body = _parse_body(resp)
    assert body == {
        "uploadUrl": _UPLOAD_URL,
        "videoKey": _VIDEO_KEY,
        "provider": "kinescope",
        "uploadMethod": "post",
    }
    assert prepare_calls[0]["user_sub"] == _USER_SUB
    assert prepare_calls[0]["course_id"] == _COURSE_ID
    assert commit_calls[0]["video_key"] == _VIDEO_KEY
    assert commit_calls[0]["expected_video_key"] == ""
    assert kinescope_calls[0]["filename"] == "lecture.mp4"


def test_upload_url_returns_401_without_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(video_edge_handler, "_load_config", lambda: _edge_config())
    evt = _upload_event()
    evt["requestContext"] = {"resourcePath": "/upload-url"}

    resp = video_edge_handler.lambda_handler(evt, None)
    assert resp["statusCode"] == 401
    assert _parse_body(resp)["code"] == "unauthorized"


def test_upload_url_returns_503_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        video_edge_handler,
        "_load_config",
        lambda: _edge_config(catalog_lambda_arn=None, kinescope_api_token=None),
    )

    resp = video_edge_handler.lambda_handler(_upload_event(), None)
    assert resp["statusCode"] == 503
    assert _parse_body(resp)["code"] == "video_unconfigured"


def test_upload_url_catalog_prepare_forbidden_returns_403(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(video_edge_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(
        video_edge_handler,
        "_invoke_video_prepare_upload",
        MagicMock(
            side_effect=CatalogInvokeHttpError(
                status_code=403,
                code="forbidden",
                message="Not allowed",
            )
        ),
    )

    resp = video_edge_handler.lambda_handler(_upload_event(), None)
    assert resp["statusCode"] == 403
    assert _parse_body(resp)["code"] == "forbidden"


def test_upload_url_catalog_prepare_failure_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(video_edge_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(
        video_edge_handler,
        "_invoke_video_prepare_upload",
        MagicMock(side_effect=CatalogInvokeError("catalog down")),
    )

    resp = video_edge_handler.lambda_handler(_upload_event(), None)
    assert resp["statusCode"] == 503
    assert _parse_body(resp)["code"] == "video_unconfigured"


def test_upload_url_deletes_orphan_kinescope_video_on_commit_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delete_calls: list[str] = []

    monkeypatch.setattr(video_edge_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(
        video_edge_handler,
        "_invoke_video_prepare_upload",
        lambda **kw: _prepare_ok(),
    )
    monkeypatch.setattr(
        video_edge_handler,
        "_init_kinescope_upload",
        lambda **kw: KinescopeUploadInit(
            upload_url=_UPLOAD_URL,
            video_key=_VIDEO_KEY,
            upload_method="post",
        ),
    )
    monkeypatch.setattr(
        video_edge_handler,
        "_invoke_video_commit_pending_upload",
        MagicMock(
            side_effect=CatalogInvokeHttpError(
                status_code=409,
                code="upload_conflict",
                message="Another upload started",
            )
        ),
    )
    monkeypatch.setattr(
        video_edge_handler,
        "_delete_kinescope_video",
        lambda **kw: delete_calls.append(kw["video_id"]) or True,
    )

    resp = video_edge_handler.lambda_handler(_upload_event(), None)

    assert resp["statusCode"] == 409
    assert delete_calls == [_VIDEO_KEY]


def test_upload_url_forwards_thumbnail_upload_to_catalog(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog_calls: list[Dict[str, Any]] = []
    catalog_response = {
        "statusCode": 200,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(
            {
                "uploadUrl": "https://bucket.s3.amazonaws.com/thumb",
                "thumbnailKey": f"{_COURSE_ID}/thumbnail/x.jpg",
            }
        ),
    }

    monkeypatch.setattr(video_edge_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(
        video_edge_handler,
        "_invoke_catalog_apigw",
        lambda **kw: catalog_calls.append(kw) or catalog_response,
    )
    monkeypatch.setattr(
        video_edge_handler,
        "_invoke_video_prepare_upload",
        MagicMock(side_effect=AssertionError("should not prepare video for thumbnail")),
    )

    evt = _upload_event()
    evt["body"] = json.dumps(
        {
            "courseId": _COURSE_ID,
            "filename": "cover.jpg",
            "contentType": "image/jpeg",
            "uploadKind": "thumbnail",
        }
    )

    resp = video_edge_handler.lambda_handler(evt, None)

    assert resp == catalog_response
    assert catalog_calls[0]["catalog_lambda_arn"] == "arn:aws:lambda:eu-west-1:1:function:catalog"


def test_upload_url_rejects_non_video_content_type_via_catalog_prepare(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(video_edge_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(
        video_edge_handler,
        "_invoke_video_prepare_upload",
        MagicMock(
            side_effect=CatalogInvokeHttpError(
                status_code=400,
                code="bad_request",
                message="Invalid or unsupported video content type",
            )
        ),
    )

    evt = _upload_event()
    evt["body"] = json.dumps(
        {
            "courseId": _COURSE_ID,
            "lessonId": _LESSON_ID,
            "filename": "x.bin",
            "contentType": "application/octet-stream",
        }
    )

    resp = video_edge_handler.lambda_handler(evt, None)
    assert resp["statusCode"] == 400
    assert _parse_body(resp)["code"] == "bad_request"


def test_options_upload_url_returns_204_with_cors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(video_edge_handler, "_load_config", lambda: _edge_config())
    evt = {
        "httpMethod": "OPTIONS",
        "path": "/upload-url",
        "requestContext": {"resourcePath": "/upload-url"},
        "headers": {"Origin": "https://teacher.example.com"},
    }

    resp = video_edge_handler.lambda_handler(evt, None)
    assert resp["statusCode"] == 204
    assert resp["headers"]["Access-Control-Allow-Origin"] == "https://teacher.example.com"
