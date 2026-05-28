"""Catalog invoke response parsing for video provider edge."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from video_catalog_invoke import CatalogInvokeHttpError, _invoke_catalog_internal


def test_invoke_catalog_internal_unwraps_success_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"ok": True, "courseId": "c1", "expectedVideoKey": ""}
    client = MagicMock()
    client.invoke.return_value = {
        "StatusCode": 200,
        "Payload": MagicMock(read=lambda: json.dumps(payload).encode("utf-8")),
    }
    monkeypatch.setattr("video_catalog_invoke.boto3.client", lambda _name: client)

    out = _invoke_catalog_internal(
        internal="video.prepare_upload",
        user_sub="sub",
        catalog_lambda_arn="arn:aws:lambda:eu-west-1:1:function:catalog",
    )
    assert out == {"courseId": "c1", "expectedVideoKey": ""}


def test_invoke_catalog_internal_raises_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "ok": False,
        "statusCode": 403,
        "code": "forbidden",
        "message": "Not allowed",
    }
    client = MagicMock()
    client.invoke.return_value = {
        "StatusCode": 200,
        "Payload": MagicMock(read=lambda: json.dumps(payload).encode("utf-8")),
    }
    monkeypatch.setattr("video_catalog_invoke.boto3.client", lambda _name: client)

    with pytest.raises(CatalogInvokeHttpError) as exc_info:
        _invoke_catalog_internal(
            internal="video.prepare_upload",
            user_sub="sub",
            catalog_lambda_arn="arn:aws:lambda:eu-west-1:1:function:catalog",
        )

    err = exc_info.value
    assert err.status_code == 403
    assert err.code == "forbidden"
    assert err.message == "Not allowed"
