"""RS-11 Slice 2: lesson file service rules and cleanup."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from services.common.errors import BadRequest, Forbidden, NotFound, ServiceUnavailable
from services.course_management.models import Course, Lesson, LessonFile
from services.course_management.service import CourseManagementService

_CID = "11111111-1111-4111-8111-111111111111"
_LID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
_MID = "22222222-2222-4222-8222-222222222222"
_FID = "33333333-3333-4333-8333-333333333333"
_OWNER = "teacher-sub"
_FILE_KEY = f"{_CID}/lessons/{_LID}/files/{_FID}.pdf"


def _lesson(**kwargs: object) -> Lesson:
    defaults: dict = {
        "id": _LID,
        "title": "L",
        "order": 1,
        "moduleId": _MID,
        "moduleOrder": 0,
        "videoKey": "",
        "videoStatus": "pending",
        "duration": 0,
        "thumbnailKey": "",
    }
    defaults.update(kwargs)
    return Lesson(**defaults)  # type: ignore[arg-type]


def _course(**kwargs: object) -> Course:
    defaults: dict = {
        "id": _CID,
        "title": "T",
        "description": "D",
        "status": "PUBLISHED",
        "createdBy": _OWNER,
    }
    defaults.update(kwargs)
    return Course(**defaults)  # type: ignore[arg-type]


def _file_row(*, status: str = "pending", kind: str = "resource") -> LessonFile:
    return LessonFile(
        id=_FID,
        courseId=_CID,
        lessonId=_LID,
        kind=kind,
        title="Syllabus",
        objectKey=_FILE_KEY,
        contentType="application/pdf",
        byteSize=100,
        status=status,
        fileType="pdf",
        createdAt="2026-01-01T00:00:00+00:00",
    )


def _service(
    *,
    role: str = "teacher",
    has_access: bool = True,
    module_locked: bool = False,
    queue_url: str = "https://sqs.example/q",
) -> tuple[CourseManagementService, MagicMock, MagicMock, MagicMock]:
    repo = MagicMock()
    repo.get_course.return_value = _course()
    repo.get_lesson_by_id.return_value = _lesson()
    repo.count_lesson_files.return_value = 0
    repo.create_lesson_file.return_value = _file_row()
    repo.get_lesson_file.return_value = _file_row()
    repo.list_lesson_files.return_value = [_file_row(status="ready")]

    file_storage = MagicMock()
    file_storage.presign_put_file.return_value = MagicMock(
        uploadUrl="https://upload.example",
        objectKey=_FILE_KEY,
    )
    file_storage.head_object.return_value = {
        "ContentLength": 100,
        "ContentType": "application/pdf",
    }
    file_storage.presign_get_file.return_value = "https://download.example"

    access = MagicMock()
    access.has_course_access.return_value = has_access

    module_lock = MagicMock()
    module_lock.is_module_locked_for_student.return_value = module_locked

    svc = CourseManagementService(
        repo,
        None,
        course_access=access,
        file_storage=file_storage,
        media_cleanup_queue_url=queue_url,
        module_lock=module_lock,
    )
    return svc, repo, file_storage, access


class TestCreateLessonFile:
    def test_teacher_gets_file_id_and_upload_url(self) -> None:
        svc, repo, file_storage, _ = _service()
        with patch(
            "services.course_management.service.uuid4",
            return_value=UUID(_FID),
        ):
            out = svc.create_lesson_file(
                _CID,
                _LID,
                title="Syllabus",
                kind="resource",
                file_type="pdf",
                byte_size=100,
                cognito_sub=_OWNER,
                role="teacher",
            )
        assert out == {"fileId": _FID, "uploadUrl": "https://upload.example"}
        repo.create_lesson_file.assert_called_once()
        file_storage.presign_put_file.assert_called_once()

    def test_student_post_forbidden(self) -> None:
        svc, repo, _, _ = _service()
        with pytest.raises(Forbidden):
            svc.create_lesson_file(
                _CID,
                _LID,
                title="Syllabus",
                kind="resource",
                file_type="pdf",
                byte_size=100,
                cognito_sub="student-sub",
                role="student",
            )
        repo.create_lesson_file.assert_not_called()

    @pytest.mark.parametrize("file_type", ["exe", ""])
    def test_invalid_file_type_rejected(self, file_type: str) -> None:
        svc, repo, _, _ = _service()
        with pytest.raises(BadRequest):
            svc.create_lesson_file(
                _CID,
                _LID,
                title="Syllabus",
                kind="resource",
                file_type=file_type,
                byte_size=100,
                cognito_sub=_OWNER,
                role="teacher",
            )
        repo.create_lesson_file.assert_not_called()

    @pytest.mark.parametrize("byte_size", [0, 104857601])
    def test_byte_size_out_of_range_rejected(self, byte_size: int) -> None:
        svc, repo, _, _ = _service()
        with pytest.raises(BadRequest):
            svc.create_lesson_file(
                _CID,
                _LID,
                title="Syllabus",
                kind="resource",
                file_type="pdf",
                byte_size=byte_size,
                cognito_sub=_OWNER,
                role="teacher",
            )
        repo.create_lesson_file.assert_not_called()

    def test_21st_file_rejected(self) -> None:
        svc, repo, _, _ = _service()
        repo.count_lesson_files.return_value = 20
        with pytest.raises(BadRequest, match="20"):
            svc.create_lesson_file(
                _CID,
                _LID,
                title="Syllabus",
                kind="resource",
                file_type="pdf",
                byte_size=100,
                cognito_sub=_OWNER,
                role="teacher",
            )


class TestCompleteLessonFile:
    def test_head_validates_and_marks_ready(self) -> None:
        svc, repo, file_storage, _ = _service()
        repo.get_lesson_file.return_value = _file_row(status="pending")
        out = svc.complete_lesson_file(
            _CID,
            _LID,
            _FID,
            cognito_sub=_OWNER,
            role="teacher",
        )
        assert out == {"fileId": _FID, "status": "ready"}
        file_storage.head_object.assert_called_once_with(_FILE_KEY)
        repo.mark_lesson_file_ready.assert_called_once_with(_CID, _LID, _FID)

    def test_student_complete_forbidden(self) -> None:
        svc, repo, _, _ = _service()
        with pytest.raises(Forbidden):
            svc.complete_lesson_file(
                _CID,
                _LID,
                _FID,
                cognito_sub="student-sub",
                role="student",
            )
        repo.mark_lesson_file_ready.assert_not_called()

    def test_head_mismatch_raises_bad_request(self) -> None:
        svc, repo, file_storage, _ = _service()
        repo.get_lesson_file.return_value = _file_row(status="pending")
        file_storage.head_object.return_value = {
            "ContentLength": 999,
            "ContentType": "application/pdf",
        }
        with pytest.raises(BadRequest):
            svc.complete_lesson_file(
                _CID,
                _LID,
                _FID,
                cognito_sub=_OWNER,
                role="teacher",
            )
        file_storage.delete_object.assert_called_once_with(_FILE_KEY)


class TestListLessonFiles:
    def test_instructor_sees_all_statuses_without_object_key(self) -> None:
        svc, repo, _, _ = _service()
        repo.list_lesson_files.return_value = [
            _file_row(status="pending"),
            _file_row(status="ready"),
        ]
        rows = svc.list_lesson_files(
            _CID,
            _LID,
            cognito_sub=_OWNER,
            role="teacher",
        )
        assert len(rows) == 2
        repo.list_lesson_files.assert_called_once_with(
            _CID, _LID, ready_only=False
        )
        for row in rows:
            assert "objectKey" not in row
            assert row["fileId"] == _FID
            assert row["kind"] in ("resource", "download")
            assert row["fileType"] == "pdf"

    def test_student_sees_ready_only_after_access_and_unlock(self) -> None:
        svc, repo, _, access = _service(has_access=True, module_locked=False)
        svc.list_lesson_files(
            _CID,
            _LID,
            cognito_sub="student-sub",
            role="student",
        )
        access.has_course_access.assert_called()
        repo.list_lesson_files.assert_called_once_with(
            _CID, _LID, ready_only=True
        )

    def test_student_list_blocked_when_module_locked(self) -> None:
        svc, repo, _, _ = _service(module_locked=True)
        with pytest.raises(Forbidden) as exc:
            svc.list_lesson_files(
                _CID,
                _LID,
                cognito_sub="student-sub",
                role="student",
            )
        assert exc.value.code == "module_locked"
        repo.list_lesson_files.assert_not_called()


class TestGetLessonFileDownloadUrl:
    def test_ready_file_returns_url(self) -> None:
        svc, repo, file_storage, _ = _service()
        repo.get_lesson_file.return_value = _file_row(status="ready")
        out = svc.get_lesson_file_download_url(
            _CID,
            _LID,
            _FID,
            cognito_sub="student-sub",
            role="student",
        )
        assert out == {"url": "https://download.example"}
        file_storage.presign_get_file.assert_called_once()

    def test_pending_file_not_found(self) -> None:
        svc, repo, file_storage, _ = _service()
        repo.get_lesson_file.return_value = _file_row(status="pending")
        with pytest.raises(NotFound):
            svc.get_lesson_file_download_url(
                _CID,
                _LID,
                _FID,
                cognito_sub="student-sub",
                role="student",
            )
        file_storage.presign_get_file.assert_not_called()

    def test_wrong_lesson_not_found(self) -> None:
        svc, repo, file_storage, _ = _service()
        repo.get_lesson_file.return_value = None
        with pytest.raises(NotFound):
            svc.get_lesson_file_download_url(
                _CID,
                _LID,
                _FID,
                cognito_sub="student-sub",
                role="student",
            )


class TestDeleteLessonFile:
    def test_delete_enqueues_cleanup_when_key_present(self) -> None:
        svc, repo, _, _ = _service()
        repo.get_lesson_file.return_value = _file_row(status="ready")
        with patch("services.course_management.service.send_media_cleanup_job") as send_job:
            out = svc.delete_lesson_file(
                _CID,
                _LID,
                _FID,
                cognito_sub=_OWNER,
                role="teacher",
            )
        assert out == {"fileId": _FID, "deleted": True}
        repo.delete_lesson_file.assert_called_once_with(_CID, _LID, _FID)
        send_job.assert_called_once()
        assert _FILE_KEY in send_job.call_args[0][2]

    def test_student_delete_forbidden(self) -> None:
        svc, repo, _, _ = _service()
        with pytest.raises(Forbidden):
            svc.delete_lesson_file(
                _CID,
                _LID,
                _FID,
                cognito_sub="student-sub",
                role="student",
            )
        repo.delete_lesson_file.assert_not_called()

    def test_delete_without_queue_raises_when_key_exists(self) -> None:
        svc, repo, _, _ = _service(queue_url="")
        repo.get_lesson_file.return_value = _file_row(status="ready")
        with pytest.raises(ServiceUnavailable, match="MEDIA_CLEANUP_QUEUE_URL"):
            svc.delete_lesson_file(
                _CID,
                _LID,
                _FID,
                cognito_sub=_OWNER,
                role="teacher",
            )


class TestDeleteLessonCollectsFileKeys:
    @patch("services.course_management.service.send_media_cleanup_job")
    def test_delete_lesson_includes_lesson_file_keys(
        self, send_job: MagicMock
    ) -> None:
        svc, repo, _, _ = _service()
        repo.list_lesson_file_object_keys_for_lesson.return_value = [_FILE_KEY]
        svc.delete_lesson(_CID, _LID)
        send_job.assert_called_once()
        keys = send_job.call_args[0][2]
        assert _FILE_KEY in keys

    @patch("services.course_management.service.send_media_cleanup_job")
    def test_delete_course_includes_all_lesson_file_keys(
        self, send_job: MagicMock
    ) -> None:
        svc, repo, _, _ = _service()
        repo.get_course.return_value = _course()
        repo.list_lessons.return_value = []
        repo.list_lesson_file_object_keys_for_course.return_value = [_FILE_KEY]
        svc.delete_course(_CID)
        send_job.assert_called_once()
        assert _FILE_KEY in send_job.call_args[0][2]
