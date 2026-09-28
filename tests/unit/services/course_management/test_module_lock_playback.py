"""RS-8 slice 3: module_locked on playback and DRM."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any
from unittest.mock import MagicMock

import pytest

from services.common.errors import Forbidden
from services.course_management.models import Course, Lesson
from services.course_management.service import CourseManagementService
from services.course_management.video_providers.port import S3Playback


_CID = "11111111-1111-4111-8111-111111111111"
_LID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
_MID = "22222222-2222-4222-8222-222222222222"
_VKEY = f"{_CID}/lessons/{_LID}/video/v.mp4"


def _lesson(*, module_id: str = _MID) -> Lesson:
    return Lesson(
        id=_LID,
        title="L",
        order=1,
        moduleId=module_id,
        moduleOrder=0,
        videoKey=_VKEY,
        videoStatus="ready",
        duration=0,
        thumbnailKey="",
    )


def _service(
    *,
    module_locked: bool = False,
    has_access: bool = True,
) -> tuple[CourseManagementService, MagicMock, MagicMock]:
    repo = MagicMock()
    repo.get_lesson_by_id.return_value = _lesson()
    repo.get_course.return_value = Course(
        id=_CID,
        title="T",
        description="D",
        status="PUBLISHED",
        createdBy="owner-sub",
    )
    access = MagicMock()
    access.has_course_access.return_value = has_access
    module_lock = MagicMock()
    module_lock.is_module_locked_for_student.return_value = module_locked
    video_provider = MagicMock()
    video_provider.resolve_playback.return_value = S3Playback(
        provider="s3",
        playback_url="https://signed.example/get",
    )
    svc = CourseManagementService(
        repo,
        None,
        course_access=access,
        video_provider=video_provider,
        module_lock=module_lock,
        kinescope_drm_jwt_secret="secret",
        kinescope_drm_jwt_issuer="streammycourse",
        kinescope_drm_jwt_audience="kinescope",
    )
    return svc, access, module_lock


def test_get_playback_url_raises_module_locked_when_port_says_locked() -> None:
    svc, _, module_lock = _service(module_locked=True, has_access=True)
    with pytest.raises(Forbidden) as exc_info:
        svc.get_playback_url(
            _CID,
            _LID,
            cognito_sub="student-sub",
            role="student",
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "module_locked"
    module_lock.is_module_locked_for_student.assert_called_once_with(
        _CID,
        _MID,
        cognito_sub="student-sub",
        role="student",
    )


def test_get_playback_url_owner_bypass_delegates_to_port() -> None:
    svc, _, module_lock = _service(module_locked=False, has_access=True)
    out = svc.get_playback_url(
        _CID,
        _LID,
        cognito_sub="owner-sub",
        role="teacher",
    )
    assert out["provider"] == "s3"
    module_lock.is_module_locked_for_student.assert_called_once()


def test_ensure_can_view_lessons_still_raises_purchase_required() -> None:
    svc, access, _ = _service(module_locked=False, has_access=False)
    access.has_course_access.return_value = False
    with pytest.raises(Forbidden) as exc_info:
        svc.ensure_can_view_lessons_and_playback(
            _CID,
            cognito_sub="student-sub",
            role="student",
        )
    assert exc_info.value.code == "purchase_required"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _jwt(secret: str, payload: dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = (
        f"{_b64url(json.dumps(header, separators=(',', ':')).encode('utf-8'))}."
        f"{_b64url(json.dumps(payload, separators=(',', ':')).encode('utf-8'))}"
    )
    sig = hmac.new(
        secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256
    ).digest()
    return f"{signing_input}.{_b64url(sig)}"


def test_authorize_kinescope_drm_false_when_module_locked() -> None:
    repo = MagicMock()
    repo.find_lesson_by_video_key.return_value = (_CID, _LID)
    repo.get_course.return_value = Course(
        id=_CID,
        title="T",
        description="D",
        status="PUBLISHED",
        createdBy="owner-sub",
    )
    repo.get_lesson_by_id.return_value = _lesson()
    access = MagicMock()
    access.has_course_access.return_value = True
    module_lock = MagicMock()
    module_lock.is_module_locked_for_student.return_value = True
    svc = CourseManagementService(
        repo,
        None,
        course_access=access,
        module_lock=module_lock,
        kinescope_drm_jwt_secret="test-secret",
        kinescope_drm_jwt_issuer="streammycourse",
        kinescope_drm_jwt_audience="kinescope",
    )
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
    assert svc.authorize_kinescope_drm({"token": token, "videoId": "video-1"}) is False
    module_lock.is_module_locked_for_student.assert_called_once_with(
        _CID,
        _MID,
        cognito_sub="student-sub",
        role="student",
    )
