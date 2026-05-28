"""Unit tests for Kinescope media.update.status handling (edge-verified metadata)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.common.errors import BadRequest
from services.course_management.service import CourseManagementService
from services.course_management.video_providers.kinescope_adapter import KinescopeVideoMetadata


def _svc(repo: MagicMock | None = None, *, api_token: str = "kin-token") -> CourseManagementService:
    repo = repo or MagicMock()
    return CourseManagementService(
        repo,
        None,
        course_access=MagicMock(),
        kinescope_api_token=api_token,
    )


def _verified(
    *,
    status: str = "done",
    duration_seconds: int | None = 120,
) -> dict[str, object]:
    return {
        "verified_metadata": KinescopeVideoMetadata(
            status=status, duration_seconds=duration_seconds
        ),
        "verified_metadata_supplied": True,
    }


def test_done_sets_lesson_ready() -> None:
    repo = MagicMock()
    repo.find_lesson_by_video_key.return_value = ("course-1", "lesson-1")
    svc = _svc(repo)
    verified = _verified()

    out = svc.handle_kinescope_media_status(
        {
            "event": "media.update.status",
            "data": {"id": "vid-abc", "status": "done"},
        },
        verified_metadata=verified["verified_metadata"],  # type: ignore[arg-type]
        verified_metadata_supplied=bool(verified["verified_metadata_supplied"]),
    )

    repo.set_lesson_video_status.assert_called_once_with(
        course_id="course-1", lesson_id="lesson-1", status="ready"
    )
    repo.set_lesson_duration.assert_called_once_with("course-1", "lesson-1", 120)
    assert out == {
        "courseId": "course-1",
        "lessonId": "lesson-1",
        "videoStatus": "ready",
        "duration": 120,
    }


def test_done_without_duration_still_marks_ready() -> None:
    repo = MagicMock()
    repo.find_lesson_by_video_key.return_value = ("course-1", "lesson-1")
    svc = _svc(repo)
    verified = _verified(duration_seconds=None)

    out = svc.handle_kinescope_media_status(
        {
            "event": "media.update.status",
            "data": {"id": "vid-abc", "status": "done"},
        },
        verified_metadata=verified["verified_metadata"],  # type: ignore[arg-type]
        verified_metadata_supplied=bool(verified["verified_metadata_supplied"]),
    )

    repo.set_lesson_video_status.assert_called_once_with(
        course_id="course-1", lesson_id="lesson-1", status="ready"
    )
    repo.set_lesson_duration.assert_not_called()
    assert out["videoStatus"] == "ready"
    assert "duration" not in out


def test_done_rejected_without_edge_verified_metadata() -> None:
    repo = MagicMock()
    repo.find_lesson_by_video_key.return_value = ("course-1", "lesson-1")
    svc = _svc(repo, api_token="kin-token")

    out = svc.handle_kinescope_media_status(
        {
            "event": "media.update.status",
            "data": {"id": "vid-abc", "status": "done"},
        }
    )

    repo.set_lesson_video_status.assert_not_called()
    assert out == {"ignored": True, "reason": "verification_unconfigured"}


def test_done_ignored_when_api_status_mismatch() -> None:
    repo = MagicMock()
    repo.find_lesson_by_video_key.return_value = ("course-1", "lesson-1")
    svc = _svc(repo)
    verified = _verified(status="processing", duration_seconds=None)

    out = svc.handle_kinescope_media_status(
        {
            "event": "media.update.status",
            "data": {"id": "vid-abc", "status": "done"},
        },
        verified_metadata=verified["verified_metadata"],  # type: ignore[arg-type]
        verified_metadata_supplied=bool(verified["verified_metadata_supplied"]),
    )

    repo.set_lesson_video_status.assert_not_called()
    assert out == {"ignored": True, "reason": "status_mismatch"}


def test_error_sets_lesson_failed() -> None:
    repo = MagicMock()
    repo.find_lesson_by_video_key.return_value = ("c2", "l2")
    svc = _svc(repo)
    verified = _verified(status="error", duration_seconds=None)

    out = svc.handle_kinescope_media_status(
        {
            "event": "media.update.status",
            "data": {"id": "vid-x", "status": "error", "message": "import failed"},
        },
        verified_metadata=verified["verified_metadata"],  # type: ignore[arg-type]
        verified_metadata_supplied=bool(verified["verified_metadata_supplied"]),
    )

    repo.set_lesson_video_status.assert_called_once_with("c2", "l2", "failed")
    assert out["videoStatus"] == "failed"


def test_aborted_sets_lesson_failed() -> None:
    repo = MagicMock()
    repo.find_lesson_by_video_key.return_value = ("c3", "l3")
    svc = _svc(repo)
    verified = _verified(status="aborted", duration_seconds=None)

    svc.handle_kinescope_media_status(
        {
            "event": "media.update.status",
            "data": {"id": "vid-y", "status": "aborted"},
        },
        verified_metadata=verified["verified_metadata"],  # type: ignore[arg-type]
        verified_metadata_supplied=bool(verified["verified_metadata_supplied"]),
    )

    repo.set_lesson_video_status.assert_called_once_with("c3", "l3", "failed")


def test_unknown_video_id_is_acknowledged_without_repo_write() -> None:
    repo = MagicMock()
    repo.find_lesson_by_video_key.return_value = None
    svc = _svc(repo)

    out = svc.handle_kinescope_media_status(
        {
            "event": "media.update.status",
            "data": {"id": "unknown", "status": "done"},
        },
        verified_metadata=_verified()["verified_metadata"],  # type: ignore[arg-type]
        verified_metadata_supplied=True,
    )

    repo.set_lesson_video_status.assert_not_called()
    assert out == {"ignored": True}


def test_unsupported_event_raises_bad_request() -> None:
    svc = _svc()

    with pytest.raises(BadRequest, match="Unsupported"):
        svc.handle_kinescope_media_status({"event": "live.finished", "data": {}})


def test_missing_video_id_raises_bad_request() -> None:
    svc = _svc()

    with pytest.raises(BadRequest, match="video"):
        svc.handle_kinescope_media_status(
            {"event": "media.update.status", "data": {"status": "done"}}
        )
