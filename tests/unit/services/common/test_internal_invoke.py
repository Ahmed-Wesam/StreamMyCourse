"""Structured internal Lambda invoke payloads."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.common.errors import Forbidden, NotFound
from services.common.internal_invoke import run_internal_handler


def test_run_internal_handler_success_flattens_payload() -> None:
    def handler(_event: dict, *, svc: MagicMock) -> dict:
        return {"courseId": "c1", "lessonId": "l1"}

    out = run_internal_handler(handler, {}, svc=MagicMock())
    assert out == {"ok": True, "courseId": "c1", "lessonId": "l1"}


def test_run_internal_handler_maps_http_error() -> None:
    def handler(_event: dict) -> dict:
        raise Forbidden("Not allowed")

    out = run_internal_handler(handler, {})
    assert out == {
        "ok": False,
        "statusCode": 403,
        "code": "forbidden",
        "message": "Not allowed",
    }


def test_run_internal_handler_maps_not_found() -> None:
    def handler(_event: dict) -> dict:
        raise NotFound("Lesson not found")

    out = run_internal_handler(handler, {})
    assert out["ok"] is False
    assert out["statusCode"] == 404
    assert out["code"] == "not_found"


def test_run_internal_handler_maps_upload_conflict_dict() -> None:
    def handler(_event: dict) -> dict:
        return {"errorCode": "upload_conflict", "message": "Another upload started"}

    out = run_internal_handler(handler, {})
    assert out == {
        "ok": False,
        "statusCode": 409,
        "code": "upload_conflict",
        "message": "Another upload started",
    }


def test_run_internal_handler_maps_value_error() -> None:
    def handler(_event: dict) -> dict:
        raise ValueError("userSub is required")

    out = run_internal_handler(handler, {})
    assert out["statusCode"] == 400
    assert out["code"] == "invalid_request"
