from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any
from unittest.mock import MagicMock

from services.course_management.service import CourseManagementService
from services.course_management.video_webhooks import handle_kinescope_drm_auth


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _jwt(secret: str, payload: dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = f"{_b64url(json.dumps(header, separators=(',', ':')).encode('utf-8'))}.{_b64url(json.dumps(payload, separators=(',', ':')).encode('utf-8'))}"
    sig = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url(sig)}"


def _service(*, has_access: bool = True) -> CourseManagementService:
    repo = MagicMock()
    repo.find_lesson_by_video_key.return_value = (
        "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
    )
    repo.get_course.return_value = MagicMock(id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    access = MagicMock()
    access.has_course_access.return_value = has_access
    return CourseManagementService(
        repo,
        None,
        course_access=access,
        kinescope_drm_jwt_secret="test-secret",
        kinescope_drm_jwt_issuer="streammycourse",
        kinescope_drm_jwt_audience="kinescope",
    )


def _event(token: str, *, video_id: str = "video-1", use_kinescope_id: bool = False) -> dict[str, Any]:
    body: dict[str, Any] = {"token": token}
    if use_kinescope_id:
        body["id"] = video_id
    else:
        body["videoId"] = video_id
    return {
        "requestContext": {"http": {"method": "POST"}},
        "body": json.dumps(body),
    }


def test_authorize_kinescope_drm_valid_returns_true() -> None:
    svc = _service(has_access=True)
    token = _jwt(
        "test-secret",
        {
            "sub": "student-sub",
            "video_id": "video-1",
            "role": "student",
            "iss": "streammycourse",
            "aud": "kinescope",
            "iat": int(time.time()),
            "exp": int(time.time()) + 300,
        },
    )
    assert svc.authorize_kinescope_drm({"token": token, "videoId": "video-1"}) is True


def test_authorize_kinescope_drm_accepts_kinescope_id_field() -> None:
    svc = _service(has_access=True)
    token = _jwt(
        "test-secret",
        {
            "sub": "student-sub",
            "video_id": "video-1",
            "role": "student",
            "iss": "streammycourse",
            "aud": "kinescope",
            "iat": int(time.time()),
            "exp": int(time.time()) + 300,
        },
    )
    assert svc.authorize_kinescope_drm({"token": token, "id": "video-1"}) is True


def test_authorize_kinescope_drm_teacher_owner_without_subscription() -> None:
    repo = MagicMock()
    repo.find_lesson_by_video_key.return_value = (
        "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
    )
    course = MagicMock(id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", createdBy="teacher-sub")
    repo.get_course.return_value = course
    access = MagicMock()
    access.has_course_access.side_effect = (
        lambda user_sub, course_id, role, course=None: role == "teacher"
        and user_sub == "teacher-sub"
    )
    svc = CourseManagementService(
        repo,
        None,
        course_access=access,
        kinescope_drm_jwt_secret="test-secret",
        kinescope_drm_jwt_issuer="streammycourse",
        kinescope_drm_jwt_audience="kinescope",
    )
    token = _jwt(
        "test-secret",
        {
            "sub": "teacher-sub",
            "video_id": "video-1",
            "role": "teacher",
            "iss": "streammycourse",
            "aud": "kinescope",
            "iat": int(time.time()),
            "exp": int(time.time()) + 300,
        },
    )
    assert svc.authorize_kinescope_drm({"token": token, "videoId": "video-1"}) is True
    access.has_course_access.assert_called_with(
        "teacher-sub",
        "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "teacher",
        course=course,
    )


def test_authorize_kinescope_drm_invalid_jwt_returns_false() -> None:
    svc = _service(has_access=True)
    assert svc.authorize_kinescope_drm({"token": "bad.jwt.token", "videoId": "video-1"}) is False


def test_authorize_kinescope_drm_expired_jwt_returns_false() -> None:
    svc = _service(has_access=True)
    token = _jwt(
        "test-secret",
        {
            "sub": "student-sub",
            "video_id": "video-1",
            "iss": "streammycourse",
            "aud": "kinescope",
            "iat": int(time.time()) - 900,
            "exp": int(time.time()) - 300,
        },
    )
    assert svc.authorize_kinescope_drm({"token": token, "videoId": "video-1"}) is False


def test_authorize_kinescope_drm_mismatched_video_returns_false() -> None:
    svc = _service(has_access=True)
    token = _jwt(
        "test-secret",
        {
            "sub": "student-sub",
            "video_id": "video-2",
            "iss": "streammycourse",
            "aud": "kinescope",
            "iat": int(time.time()),
            "exp": int(time.time()) + 300,
        },
    )
    assert svc.authorize_kinescope_drm({"token": token, "videoId": "video-1"}) is False


def test_authorize_kinescope_drm_no_access_returns_false() -> None:
    svc = _service(has_access=False)
    token = _jwt(
        "test-secret",
        {
            "sub": "student-sub",
            "video_id": "video-1",
            "iss": "streammycourse",
            "aud": "kinescope",
            "iat": int(time.time()),
            "exp": int(time.time()) + 300,
        },
    )
    assert svc.authorize_kinescope_drm({"token": token, "videoId": "video-1"}) is False


def test_webhook_drm_auth_returns_200_when_authorized_kinescope_payload() -> None:
    svc = MagicMock()
    svc.authorize_kinescope_drm.return_value = True
    resp = handle_kinescope_drm_auth(
        _event("valid.jwt.token", use_kinescope_id=True),
        origin="*",
        svc=svc,
    )
    assert resp["statusCode"] == 200
    svc.authorize_kinescope_drm.assert_called_once()
    call_payload = svc.authorize_kinescope_drm.call_args[0][0]
    assert call_payload.get("id") == "video-1"


def test_webhook_drm_auth_returns_200_when_authorized() -> None:
    svc = MagicMock()
    svc.authorize_kinescope_drm.return_value = True
    resp = handle_kinescope_drm_auth(_event("valid.jwt.token"), origin="*", svc=svc)
    assert resp["statusCode"] == 200


def test_webhook_drm_auth_returns_403_when_denied() -> None:
    svc = MagicMock()
    svc.authorize_kinescope_drm.return_value = False
    resp = handle_kinescope_drm_auth(_event("bad.jwt.token"), origin="*", svc=svc)
    assert resp["statusCode"] == 403
