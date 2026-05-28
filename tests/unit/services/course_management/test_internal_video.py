"""Catalog internal video handlers (upload-url slice 1, mark-ready slice 2)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from index import lambda_handler
from services.common.errors import BadRequest, Conflict, Forbidden
from services.course_management.internal_video import (
    handle_internal_video_apply_mark_ready,
    handle_internal_video_commit_pending_upload,
    handle_internal_video_prepare_mark_ready,
    handle_internal_video_prepare_upload,
    handle_internal_video_webhook_status,
)
from services.course_management.models import Course, Lesson
from services.course_management.service import CourseManagementService

_COURSE_ID = "11111111-1111-4111-8111-111111111111"
_LESSON_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
_OWNER_SUB = "teacher-owner-sub"
_VIDEO_KEY = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"


def _course(*, created_by: str = _OWNER_SUB) -> Course:
    return Course(
        id=_COURSE_ID,
        title="T",
        description="D",
        status="DRAFT",
        createdBy=created_by,
        thumbnailKey="",
    )


def _lesson(*, video_key: str = "") -> Lesson:
    return Lesson(
        id=_LESSON_ID,
        title="L",
        order=1,
        moduleId="99999999-9999-4999-8999-999999999999",
        moduleOrder=0,
        videoKey=video_key,
        videoStatus="pending",
        duration=0,
        thumbnailKey="",
    )


class TestInternalVideoPrepareUpload:
    def test_non_owner_raises_forbidden(self) -> None:
        svc = MagicMock(spec=CourseManagementService)
        svc.prepare_lesson_video_upload.side_effect = Forbidden("Not allowed to modify this course")

        with pytest.raises(Forbidden):
            handle_internal_video_prepare_upload(
                {
                    "userSub": "other-sub",
                    "role": "teacher",
                    "courseId": _COURSE_ID,
                    "lessonId": _LESSON_ID,
                    "filename": "x.mp4",
                    "contentType": "video/mp4",
                },
                course_service=svc,
            )

    def test_owner_returns_lesson_context(self) -> None:
        svc = MagicMock(spec=CourseManagementService)
        svc.prepare_lesson_video_upload.return_value = {
            "courseId": _COURSE_ID,
            "lessonId": _LESSON_ID,
            "filename": "lecture.mp4",
            "contentType": "video/mp4",
            "filesize": 2048,
            "expectedVideoKey": "prev-key",
        }

        out = handle_internal_video_prepare_upload(
            {
                "userSub": _OWNER_SUB,
                "role": "teacher",
                "courseId": _COURSE_ID,
                "lessonId": _LESSON_ID,
                "filename": "lecture.mp4",
                "contentType": "video/mp4",
                "filesize": 2048,
            },
            course_service=svc,
        )

        svc.prepare_lesson_video_upload.assert_called_once_with(
            course_id=_COURSE_ID,
            lesson_id=_LESSON_ID,
            filename="lecture.mp4",
            content_type="video/mp4",
            filesize=2048,
            cognito_sub=_OWNER_SUB,
            role="teacher",
        )
        assert out["expectedVideoKey"] == "prev-key"

    def test_missing_user_sub_raises(self) -> None:
        svc = MagicMock(spec=CourseManagementService)
        with pytest.raises(ValueError, match="userSub"):
            handle_internal_video_prepare_upload({}, course_service=svc)


class TestInternalVideoCommitPendingUpload:
    def test_commits_pending_video_key(self) -> None:
        svc = MagicMock(spec=CourseManagementService)
        svc.commit_pending_lesson_video_upload.return_value = {"committed": True}

        out = handle_internal_video_commit_pending_upload(
            {
                "userSub": _OWNER_SUB,
                "role": "teacher",
                "courseId": _COURSE_ID,
                "lessonId": _LESSON_ID,
                "videoKey": _VIDEO_KEY,
                "expectedVideoKey": "",
            },
            course_service=svc,
        )

        svc.commit_pending_lesson_video_upload.assert_called_once_with(
            course_id=_COURSE_ID,
            lesson_id=_LESSON_ID,
            video_key=_VIDEO_KEY,
            expected_video_key="",
            cognito_sub=_OWNER_SUB,
            role="teacher",
        )
        assert out == {"committed": True}

    def test_non_owner_raises_forbidden(self) -> None:
        svc = MagicMock(spec=CourseManagementService)
        svc.commit_pending_lesson_video_upload.side_effect = Forbidden(
            "Not allowed to modify this course"
        )

        with pytest.raises(Forbidden):
            handle_internal_video_commit_pending_upload(
                {
                    "userSub": "other-sub",
                    "role": "teacher",
                    "courseId": _COURSE_ID,
                    "lessonId": _LESSON_ID,
                    "videoKey": _VIDEO_KEY,
                    "expectedVideoKey": "",
                },
                course_service=svc,
            )


@pytest.fixture
def repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def video_provider() -> MagicMock:
    m = MagicMock()
    m.provider_id = "kinescope"
    m.marks_ready_on_upload_complete = False
    return m


@pytest.fixture
def enrollments() -> MagicMock:
    m = MagicMock()
    m.has_enrollment.return_value = False
    return m


class TestPrepareUploadServiceAuthz:
    def test_non_owner_teacher_forbidden(
        self, repo: MagicMock, video_provider: MagicMock, enrollments: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(created_by=_OWNER_SUB)
        svc = CourseManagementService(
            repo=repo,
            image_storage=MagicMock(),
            video_provider=video_provider,
            course_access=enrollments,
        )

        with pytest.raises(Forbidden):
            svc.prepare_lesson_video_upload(
                course_id=_COURSE_ID,
                lesson_id=_LESSON_ID,
                filename="x.mp4",
                content_type="video/mp4",
                filesize=None,
                cognito_sub="other-sub",
                role="teacher",
            )

    def test_owner_returns_expected_video_key(
        self, repo: MagicMock, video_provider: MagicMock, enrollments: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(created_by=_OWNER_SUB)
        repo.get_lesson_by_id.return_value = _lesson(video_key="existing-key")

        svc = CourseManagementService(
            repo=repo,
            image_storage=MagicMock(),
            video_provider=video_provider,
            course_access=enrollments,
        )

        out = svc.prepare_lesson_video_upload(
            course_id=_COURSE_ID,
            lesson_id=_LESSON_ID,
            filename="lecture.mp4",
            content_type="video/mp4",
            filesize=512,
            cognito_sub=_OWNER_SUB,
            role="teacher",
        )

        assert out == {
            "courseId": _COURSE_ID,
            "lessonId": _LESSON_ID,
            "filename": "lecture.mp4",
            "contentType": "video/mp4",
            "filesize": 512,
            "expectedVideoKey": "existing-key",
        }

    def test_rejects_non_video_content_type(
        self, repo: MagicMock, video_provider: MagicMock, enrollments: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(created_by=_OWNER_SUB)
        repo.get_lesson_by_id.return_value = _lesson()

        svc = CourseManagementService(
            repo=repo,
            image_storage=MagicMock(),
            video_provider=video_provider,
            course_access=enrollments,
        )

        with pytest.raises(BadRequest, match="Invalid or unsupported video content type"):
            svc.prepare_lesson_video_upload(
                course_id=_COURSE_ID,
                lesson_id=_LESSON_ID,
                filename="x.bin",
                content_type="application/octet-stream",
                filesize=None,
                cognito_sub=_OWNER_SUB,
                role="teacher",
            )


class TestCommitPendingUploadService:
    def test_persists_pending_status(
        self, repo: MagicMock, video_provider: MagicMock, enrollments: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(created_by=_OWNER_SUB)

        svc = CourseManagementService(
            repo=repo,
            image_storage=MagicMock(),
            video_provider=video_provider,
            course_access=enrollments,
        )

        out = svc.commit_pending_lesson_video_upload(
            course_id=_COURSE_ID,
            lesson_id=_LESSON_ID,
            video_key=_VIDEO_KEY,
            expected_video_key="",
            cognito_sub=_OWNER_SUB,
            role="teacher",
        )

        repo.set_lesson_video_if_video_key_matches.assert_called_once_with(
            course_id=_COURSE_ID,
            lesson_id=_LESSON_ID,
            video_key=_VIDEO_KEY,
            status="pending",
            expected_video_key="",
        )
        assert out == {"committed": True}

    def test_conflict_propagates(
        self, repo: MagicMock, video_provider: MagicMock, enrollments: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(created_by=_OWNER_SUB)
        repo.set_lesson_video_if_video_key_matches.side_effect = Conflict(
            "Another upload started for this lesson; retry."
        )

        svc = CourseManagementService(
            repo=repo,
            image_storage=MagicMock(),
            video_provider=video_provider,
            course_access=enrollments,
        )

        with pytest.raises(Conflict):
            svc.commit_pending_lesson_video_upload(
                course_id=_COURSE_ID,
                lesson_id=_LESSON_ID,
                video_key=_VIDEO_KEY,
                expected_video_key="",
                cognito_sub=_OWNER_SUB,
                role="teacher",
            )


class TestInternalVideoInvokeDispatch:
    def test_lambda_handler_dispatches_prepare_upload(self) -> None:
        expected = {"courseId": _COURSE_ID, "lessonId": _LESSON_ID, "expectedVideoKey": ""}
        with patch("index._handle_internal_event", return_value=expected) as mock:
            event = {
                "internal": "video.prepare_upload",
                "userSub": _OWNER_SUB,
                "courseId": _COURSE_ID,
                "lessonId": _LESSON_ID,
            }
            out = lambda_handler(event, None)
            mock.assert_called_once_with(event)
            assert out == expected

    def test_lambda_handler_dispatches_apply_mark_ready(self) -> None:
        expected = {"lessonId": _LESSON_ID, "videoStatus": "ready"}
        with patch("index._handle_internal_event", return_value=expected) as mock:
            event = {
                "internal": "video.apply_mark_ready",
                "userSub": _OWNER_SUB,
                "courseId": _COURSE_ID,
                "lessonId": _LESSON_ID,
                "videoKey": _VIDEO_KEY,
                "providerMetadataSupplied": True,
                "providerMetadata": {"status": "done", "durationSeconds": 60},
            }
            out = lambda_handler(event, None)
            mock.assert_called_once_with(event)
            assert out == expected


class TestInternalVideoPrepareMarkReady:
    def test_non_owner_raises_forbidden(self) -> None:
        svc = MagicMock(spec=CourseManagementService)
        svc.prepare_lesson_video_mark_ready.side_effect = Forbidden(
            "Not allowed to modify this course"
        )

        with pytest.raises(Forbidden):
            handle_internal_video_prepare_mark_ready(
                {
                    "userSub": "other-sub",
                    "role": "teacher",
                    "courseId": _COURSE_ID,
                    "lessonId": _LESSON_ID,
                },
                course_service=svc,
            )

    def test_missing_video_key_raises_bad_request(self) -> None:
        svc = MagicMock(spec=CourseManagementService)
        svc.prepare_lesson_video_mark_ready.side_effect = BadRequest("No video uploaded for lesson")

        with pytest.raises(BadRequest):
            handle_internal_video_prepare_mark_ready(
                {
                    "userSub": _OWNER_SUB,
                    "role": "teacher",
                    "courseId": _COURSE_ID,
                    "lessonId": _LESSON_ID,
                },
                course_service=svc,
            )

    def test_owner_returns_video_key(self) -> None:
        svc = MagicMock(spec=CourseManagementService)
        svc.prepare_lesson_video_mark_ready.return_value = {
            "courseId": _COURSE_ID,
            "lessonId": _LESSON_ID,
            "videoKey": _VIDEO_KEY,
        }

        out = handle_internal_video_prepare_mark_ready(
            {
                "userSub": _OWNER_SUB,
                "role": "teacher",
                "courseId": _COURSE_ID,
                "lessonId": _LESSON_ID,
            },
            course_service=svc,
        )

        svc.prepare_lesson_video_mark_ready.assert_called_once_with(
            course_id=_COURSE_ID,
            lesson_id=_LESSON_ID,
            cognito_sub=_OWNER_SUB,
            role="teacher",
        )
        assert out["videoKey"] == _VIDEO_KEY


class TestInternalVideoApplyMarkReady:
    def test_apply_with_supplied_metadata_skips_kinescope_fetch(
        self, repo: MagicMock, video_provider: MagicMock, enrollments: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(created_by=_OWNER_SUB)
        repo.get_lesson_by_id.return_value = _lesson(video_key=_VIDEO_KEY)

        svc = CourseManagementService(
            repo=repo,
            image_storage=MagicMock(),
            video_provider=video_provider,
            course_access=enrollments,
            kinescope_api_token="test-token",
            deployment_environment="prod",
        )

        out = handle_internal_video_apply_mark_ready(
            {
                "userSub": _OWNER_SUB,
                "role": "teacher",
                "courseId": _COURSE_ID,
                "lessonId": _LESSON_ID,
                "videoKey": _VIDEO_KEY,
                "providerMetadataSupplied": True,
                "providerMetadata": {"status": "done", "durationSeconds": 45},
            },
            course_service=svc,
        )

        repo.set_lesson_video_status.assert_called_once_with(
            course_id=_COURSE_ID, lesson_id=_LESSON_ID, status="ready"
        )
        repo.set_lesson_duration.assert_called_once_with(_COURSE_ID, _LESSON_ID, 45)
        assert out == {"lessonId": _LESSON_ID, "videoStatus": "ready", "duration": 45}

    def test_apply_dev_bypass_without_metadata(
        self, repo: MagicMock, video_provider: MagicMock, enrollments: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(created_by=_OWNER_SUB)
        repo.get_lesson_by_id.return_value = _lesson(video_key=_VIDEO_KEY)

        svc = CourseManagementService(
            repo=repo,
            image_storage=MagicMock(),
            video_provider=video_provider,
            course_access=enrollments,
            kinescope_api_token="test-token",
            deployment_environment="dev",
        )

        out = handle_internal_video_apply_mark_ready(
            {
                "userSub": _OWNER_SUB,
                "role": "teacher",
                "courseId": _COURSE_ID,
                "lessonId": _LESSON_ID,
                "videoKey": _VIDEO_KEY,
                "providerMetadataSupplied": False,
            },
            course_service=svc,
        )

        repo.set_lesson_video_status.assert_called_once_with(
            course_id=_COURSE_ID, lesson_id=_LESSON_ID, status="ready"
        )
        assert out == {"lessonId": _LESSON_ID, "videoStatus": "ready"}


class TestInternalVideoWebhookStatus:
    def test_delegates_to_service_without_kinescope_refetch(
        self, repo: MagicMock, video_provider: MagicMock, enrollments: MagicMock
    ) -> None:
        repo.find_lesson_by_video_key.return_value = (_COURSE_ID, _LESSON_ID)

        svc = CourseManagementService(
            repo=repo,
            image_storage=MagicMock(),
            video_provider=video_provider,
            course_access=enrollments,
            kinescope_api_token="test-token",
        )

        webhook_payload = {
            "event": "media.update.status",
            "data": {"id": _VIDEO_KEY, "status": "done"},
        }

        out = handle_internal_video_webhook_status(
            {
                "webhookPayload": webhook_payload,
                "providerMetadataSupplied": True,
                "providerMetadata": {"status": "done", "durationSeconds": 88},
            },
            course_service=svc,
        )

        repo.set_lesson_video_status.assert_called_once_with(
            course_id=_COURSE_ID, lesson_id=_LESSON_ID, status="ready"
        )
        repo.set_lesson_duration.assert_called_once_with(_COURSE_ID, _LESSON_ID, 88)
        assert out == {
            "courseId": _COURSE_ID,
            "lessonId": _LESSON_ID,
            "videoStatus": "ready",
            "duration": 88,
        }

    def test_missing_webhook_payload_raises(self) -> None:
        svc = MagicMock(spec=CourseManagementService)
        with pytest.raises(ValueError, match="webhookPayload"):
            handle_internal_video_webhook_status({}, course_service=svc)

    def test_lambda_handler_dispatches_webhook_status(self) -> None:
        expected = {"ignored": True}
        with patch("index._handle_internal_event", return_value=expected) as mock:
            event = {
                "internal": "video.webhook_status",
                "webhookPayload": {
                    "event": "media.update.status",
                    "data": {"id": _VIDEO_KEY, "status": "done"},
                },
                "providerMetadataSupplied": True,
                "providerMetadata": {"status": "done"},
            }
            out = lambda_handler(event, None)
            mock.assert_called_once_with(event)
            assert out == expected
