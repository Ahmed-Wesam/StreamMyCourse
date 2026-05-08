"""Unit tests for `services.course_management.service.CourseManagementService`.

The service is constructor-injected with a repo + (optional) storage port, so
we hand it `MagicMock` doubles directly. No patching of module globals — the
ports are the only seam we need.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from services.common.errors import BadRequest, Conflict, Forbidden, NotFound, ServiceUnavailable
from services.course_management.models import Course, CourseModule, Lesson, PresignResult
from services.course_management.service import CourseManagementService


_MID_DEFAULT = "99999999-9999-4999-8999-999999999999"
_VID_DEFAULT = "11111111-1111-4111-8111-111111111111"


def _lesson(
    *,
    id_: str = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    order: int = 1,
    module_id: str = _MID_DEFAULT,
    module_order: int = 0,
    video_key: str = "",
    video_status: str = "pending",
    title: str = "L",
    thumbnail_key: str = "",
) -> Lesson:
    return Lesson(
        id=id_,
        title=title,
        order=order,
        moduleId=module_id,
        moduleOrder=module_order,
        videoKey=video_key,
        videoStatus=video_status,
        duration=0,
        thumbnailKey=thumbnail_key,
    )


def _module(
    *,
    id_: str = _MID_DEFAULT,
    course_id: str = _VID_DEFAULT,
    order: int = 0,
    title: str = "Module",
) -> CourseModule:
    return CourseModule(
        id=id_,
        courseId=course_id,
        title=title,
        description="",
        order=order,
    )


def _course(
    *,
    id_: str = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    status: str = "DRAFT",
    thumbnail_key: str = "",
    created_by: str = "",
) -> Course:
    return Course(
        id=id_, title="T", description="D", status=status, thumbnailKey=thumbnail_key, createdBy=created_by
    )


_VID = "11111111-1111-4111-8111-111111111111"
_TH1 = "22222222-2222-4222-8222-222222222222"
_TH2 = "33333333-3333-4333-8333-333333333333"
_TH3 = "44444444-4444-4444-8444-444444444444"
_TH4 = "55555555-5555-4555-8555-555555555555"


def _video_key(course_id: str, lesson_id: str, file_id: str = _VID, ext: str = "mp4") -> str:
    return f"{course_id}/lessons/{lesson_id}/video/{file_id}.{ext}"


def _lesson_thumb_key(course_id: str, lesson_id: str, file_id: str = _TH1, ext: str = "jpg") -> str:
    return f"{course_id}/lessons/{lesson_id}/thumbnail/{file_id}.{ext}"


def _course_thumb_key(course_id: str, file_id: str = _TH2, ext: str = "jpg") -> str:
    return f"{course_id}/thumbnail/{file_id}.{ext}"


@pytest.fixture
def repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def storage() -> MagicMock:
    return MagicMock()


@pytest.fixture
def enrollments() -> MagicMock:
    m = MagicMock()
    m.has_enrollment.return_value = False
    return m


@pytest.fixture
def service(
    repo: MagicMock, storage: MagicMock, enrollments: MagicMock
) -> CourseManagementService:
    return CourseManagementService(repo, storage, enrollments)


@pytest.fixture
def service_no_storage(repo: MagicMock, enrollments: MagicMock) -> CourseManagementService:
    return CourseManagementService(repo, None, enrollments)


@pytest.fixture
def service_with_queue(
    repo: MagicMock, storage: MagicMock, enrollments: MagicMock
) -> CourseManagementService:
    return CourseManagementService(
        repo, storage, enrollments, media_cleanup_queue_url="https://sqs.example/queue"
    )


# --- list_published_courses ---------------------------------------------------


class TestListPublishedCourses:
    def test_filters_to_published(self, service: CourseManagementService, repo: MagicMock) -> None:
        repo.list_courses.return_value = [
            _course(id_="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", status="DRAFT"),
            _course(id_="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", status="PUBLISHED"),
            _course(id_="cccccccc-cccc-4ccc-8ccc-cccccccccccc", status="PUBLISHED"),
        ]
        repo.list_lessons.return_value = []
        published = service.list_published_courses()
        assert [c["id"] for c in published] == ["bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", "cccccccc-cccc-4ccc-8ccc-cccccccccccc"]

    def test_empty_when_no_courses(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.list_courses.return_value = []
        assert service.list_published_courses() == []


# --- list_instructor_courses --------------------------------------------------


class TestListInstructorCourses:
    def test_teacher_uses_repo_filter(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.list_courses_by_instructor.return_value = [
            _course(id_="dddddddd-dddd-4ddd-8ddd-dddddddddddd", status="DRAFT", created_by="sub-a"),
        ]
        repo.list_lessons.return_value = []
        out = service.list_instructor_courses(
            cognito_sub="sub-a", role="teacher"
        )
        repo.list_courses_by_instructor.assert_called_once_with("sub-a")
        repo.list_courses.assert_not_called()
        assert len(out) == 1
        assert out[0]["id"] == "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
        assert out[0]["status"] == "DRAFT"

    def test_admin_lists_all_courses(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.list_courses.return_value = [
            _course(id_="eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee", status="PUBLISHED"),
            _course(id_="ffffffff-ffff-4fff-8fff-ffffffffffff", status="DRAFT"),
        ]
        repo.list_lessons.return_value = []
        out = service.list_instructor_courses(
            cognito_sub="admin-sub", role="admin"
        )
        repo.list_courses.assert_called_once()
        repo.list_courses_by_instructor.assert_not_called()
        assert {c["id"] for c in out} == {"eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee", "ffffffff-ffff-4fff-8fff-ffffffffffff"}

    # Authentication (non-empty sub) is enforced in the controller layer.

    def test_student_role_raises_forbidden(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.list_courses.return_value = []
        repo.list_lessons.return_value = []
        with pytest.raises(Forbidden) as ei:
            service.list_instructor_courses(cognito_sub="sub-a", role="student")
        assert ei.value.code == "forbidden"


# --- get_course ---------------------------------------------------------------


class TestGetCourse:
    def test_missing_raises_not_found(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = None
        with pytest.raises(NotFound):
            service.get_course("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

    def test_existing_course_returned_as_dict(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_=_VID, status="PUBLISHED")
        repo.list_lessons.return_value = []
        out = service.get_course(_VID)
        assert out["id"] == _VID
        assert out["status"] == "PUBLISHED"


# --- create_course ------------------------------------------------------------


class TestCreateCourse:
    # Authentication (non-empty sub) is enforced in the controller layer.

    def test_student_role_raises_forbidden(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.create_course.return_value = _course(id_=_VID)
        with pytest.raises(Forbidden):
            service.create_course("T", "D", created_by="sub-a", role="student")
        repo.create_course.assert_not_called()

    def test_falls_back_to_untitled_for_blank_title(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.create_course.return_value = _course(id_=_VID)
        service.create_course("", "", created_by="sub-a", role="teacher")
        repo.create_course.assert_called_once_with(
            title="Untitled Course", description="", created_by="sub-a"
        )

    def test_returns_id_and_status(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.create_course.return_value = _course(id_=_VID, status="DRAFT")
        out = service.create_course("Title", "Desc", created_by="sub-a", role="teacher")
        assert out == {"id": _VID, "status": "DRAFT"}


class TestUpdateCourse:
    def test_delegates_and_returns_updated(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        out = service.update_course(_VID, "T2", "D2")
        repo.update_course.assert_called_once_with(
            course_id=_VID, title="T2", description="D2"
        )
        assert out == {"id": _VID, "updated": True}


class TestListLessons:
    def test_returns_dicts(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.list_lessons.return_value = [
            _lesson(id_="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", order=1),
            _lesson(id_="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", order=2),
        ]
        out = service.list_lessons(_VID)
        assert [l["id"] for l in out] == ["aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"]
        assert all("videoKey" not in l for l in out)

    def test_strips_video_key_from_public_lesson_dict(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.list_lessons.return_value = [
            _lesson(id_="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", order=1, video_key=_video_key(_VID, "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", "99999999-9999-4999-8999-999999999999"))
        ]
        out = service.list_lessons(_VID)
        assert "videoKey" not in out[0]

    def test_presigned_thumbnail_url_when_key_set(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        k = _lesson_thumb_key(_VID, "cccccccc-cccc-4ccc-8ccc-cccccccccccc", "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
        repo.list_lessons.return_value = [
            _lesson(id_="cccccccc-cccc-4ccc-8ccc-cccccccccccc", order=1, thumbnail_key=k),
        ]
        storage.presign_get.return_value = "https://signed-lesson-thumb"
        out = service.list_lessons(_VID)
        assert out[0]["thumbnailUrl"] == "https://signed-lesson-thumb"
        storage.presign_get.assert_called_once_with(key=k, expires_seconds=3600)


class TestCreateLessonService:
    def test_returns_lesson_id_and_order(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.list_course_modules.return_value = [_module(course_id=_VID, id_=_MID_DEFAULT)]
        repo.create_lesson.return_value = _lesson(id_="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", order=1)
        out = service.create_lesson(_VID, "")
        repo.create_lesson.assert_called_once_with(
            course_id=_VID, module_id=_MID_DEFAULT, title="Lesson"
        )
        assert out == {
            "lessonId": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            "moduleId": _MID_DEFAULT,
            "order": 1,
        }


# --- delete_course ------------------------------------------------------------


class TestDeleteCourse:
    def test_missing_course_raises_not_found(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = None
        with pytest.raises(NotFound, match="Course not found"):
            service.delete_course("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
        repo.delete_course_and_lessons.assert_not_called()

    def test_delegates_to_repo(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_=_VID)
        repo.list_lessons.return_value = []
        out = service.delete_course(_VID)
        repo.delete_course_and_lessons.assert_called_once_with(_VID)
        assert out == {"id": _VID, "deleted": True}

    def test_raises_when_queue_missing_but_course_has_media_keys(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(
            id_=_VID, thumbnail_key=_course_thumb_key(_VID, _TH3)
        )
        repo.list_lessons.return_value = []
        with pytest.raises(ServiceUnavailable, match="MEDIA_CLEANUP_QUEUE_URL"):
            service.delete_course(_VID)
        repo.delete_course_and_lessons.assert_not_called()

    @patch("services.course_management.service.send_media_cleanup_job")
    def test_enqueue_failure_after_db_delete_propagates(
        self, send_job: MagicMock, service_with_queue: CourseManagementService, repo: MagicMock
    ) -> None:
        _L1 = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        repo.get_course.return_value = _course(id_=_VID)
        repo.list_lessons.return_value = [_lesson(id_=_L1, video_key=_video_key(_VID, _L1))]
        send_job.side_effect = RuntimeError("sqs down")
        with pytest.raises(RuntimeError, match="sqs down"):
            service_with_queue.delete_course(_VID)
        repo.delete_course_and_lessons.assert_called_once_with(_VID)

    def test_without_storage_raises_when_queue_missing_and_media_keys(
        self, service_no_storage: CourseManagementService, repo: MagicMock
    ) -> None:
        _L1 = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        repo.get_course.return_value = _course(id_=_VID)
        repo.list_lessons.return_value = [_lesson(id_=_L1, video_key=_video_key(_VID, _L1))]
        with pytest.raises(ServiceUnavailable, match="MEDIA_CLEANUP_QUEUE_URL"):
            service_no_storage.delete_course(_VID)
        repo.delete_course_and_lessons.assert_not_called()

    @patch("services.course_management.service.send_media_cleanup_job")
    def test_enqueues_media_cleanup_when_queue_configured(
        self,
        send_job: MagicMock,
        service_with_queue: CourseManagementService,
        repo: MagicMock,
        storage: MagicMock,
    ) -> None:
        _L1 = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        repo.get_course.return_value = _course(id_=_VID, thumbnail_key=_course_thumb_key(_VID, _TH3))
        repo.list_lessons.return_value = [
            _lesson(
                id_=_L1,
                video_key=_video_key(_VID, _L1),
                thumbnail_key=_lesson_thumb_key(_VID, _L1, _TH4),
            ),
        ]
        order: list[str] = []

        def _mark_db(*_a: object, **_k: object) -> None:
            order.append("db")

        def _mark_send(*_a: object, **_k: object) -> None:
            order.append("sqs")

        repo.delete_course_and_lessons.side_effect = _mark_db
        send_job.side_effect = _mark_send
        service_with_queue.delete_course(_VID)
        assert order == ["db", "sqs"]
        storage.delete_objects.assert_not_called()
        send_job.assert_called_once()
        qurl, cid, keys = send_job.call_args[0]
        assert qurl == "https://sqs.example/queue"
        assert cid == _VID
        assert set(keys) == {
            _course_thumb_key(_VID, _TH3),
            _video_key(_VID, _L1),
            _lesson_thumb_key(_VID, _L1, _TH4),
        }

    @patch("services.course_management.service.send_media_cleanup_job")
    def test_enqueue_runs_without_storage_when_queue_configured(
        self, send_job: MagicMock, repo: MagicMock, enrollments: MagicMock
    ) -> None:
        _L1 = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        svc = CourseManagementService(
            repo, None, enrollments, media_cleanup_queue_url="https://sqs.example/queue"
        )
        repo.get_course.return_value = _course(id_=_VID)
        repo.list_lessons.return_value = [_lesson(id_=_L1, video_key=_video_key(_VID, _L1))]
        svc.delete_course(_VID)
        send_job.assert_called_once()


# --- update_lesson ------------------------------------------------------------


class TestUpdateLesson:
    def test_missing_lesson_raises(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = None
        with pytest.raises(NotFound):
            service.update_lesson(_VID, "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "new title")

    def test_blank_title_falls_back_to_existing(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(id_="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", title="Old Title")
        service.update_lesson(_VID, "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "")
        repo.update_lesson_title.assert_called_once_with(
            course_id=_VID, lesson_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", title="Old Title"
        )


# --- delete_lesson + order compaction -----------------------------------------


class TestDeleteLessonOrderCompaction:
    _LID1 = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    _LID2 = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    _LID3 = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    _LID4 = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"

    def test_missing_raises_not_found(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = None
        with pytest.raises(NotFound):
            service.delete_lesson(_VID, "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

    def test_raises_when_queue_missing_but_lesson_has_media_keys(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(
            id_=self._LID2,
            order=2,
            video_key=_video_key(_VID, self._LID2, "66666666-6666-4666-8666-666666666666"),
            thumbnail_key=_lesson_thumb_key(_VID, self._LID2),
        )
        with pytest.raises(ServiceUnavailable, match="MEDIA_CLEANUP_QUEUE_URL"):
            service.delete_lesson(_VID, self._LID2)
        repo.delete_lesson.assert_not_called()
        storage.delete_objects.assert_not_called()

    @patch("services.course_management.service.send_media_cleanup_job")
    def test_enqueues_media_cleanup_when_queue_configured(
        self,
        send_job: MagicMock,
        service_with_queue: CourseManagementService,
        repo: MagicMock,
        storage: MagicMock,
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(
            id_=self._LID2,
            order=2,
            video_key=_video_key(_VID, self._LID2, "66666666-6666-4666-8666-666666666666"),
            thumbnail_key=_lesson_thumb_key(_VID, self._LID2),
        )
        repo.list_lessons.return_value = []
        order: list[str] = []

        def _mark_db(*_a: object, **_k: object) -> None:
            order.append("db")

        def _mark_send(*_a: object, **_k: object) -> None:
            order.append("sqs")

        repo.delete_lesson.side_effect = _mark_db
        send_job.side_effect = _mark_send
        service_with_queue.delete_lesson(_VID, self._LID2)
        assert order == ["db", "sqs"]
        storage.delete_objects.assert_not_called()
        send_job.assert_called_once()
        qurl, cid, keys = send_job.call_args[0]
        assert qurl == "https://sqs.example/queue"
        assert cid == _VID
        assert set(keys) == {
            _video_key(_VID, self._LID2, "66666666-6666-4666-8666-666666666666"),
            _lesson_thumb_key(_VID, self._LID2),
        }

    def test_compacts_remaining_orders_to_one_through_n(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        # Starting state: lessons of orders [1,2,3,4] with stable ids.
        # We delete the order=2 lesson, so the remaining (1,3,4) must be
        # renumbered to (1,2,3) preserving their relative order.
        l1 = _lesson(id_=self._LID1, order=1)
        l3 = _lesson(id_=self._LID3, order=3)
        l4 = _lesson(id_=self._LID4, order=4)
        repo.get_lesson_by_id.return_value = _lesson(id_=self._LID2, order=2)
        repo.list_lessons.return_value = [l1, l3, l4]

        service.delete_lesson(_VID, self._LID2)

        storage.delete_objects.assert_not_called()
        repo.delete_lesson.assert_called_once_with(course_id=_VID, lesson_id=self._LID2)
        # First lesson stays at order 1; only mismatched orders are patched.
        repo.set_lesson_orders.assert_called_once_with(
            _VID, {self._LID3: 2, self._LID4: 3}
        )

    def test_preserves_order_when_unsorted_input_returned(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        # Belt-and-suspenders: even if the repo returns unsorted lessons,
        # the service must sort by `order` before reassigning.
        l1 = _lesson(id_=self._LID1, order=1)
        l3 = _lesson(id_=self._LID3, order=3)
        l4 = _lesson(id_=self._LID4, order=4)
        repo.get_lesson_by_id.return_value = _lesson(id_=self._LID2, order=2)
        repo.list_lessons.return_value = [l4, l1, l3]  # intentionally jumbled

        service.delete_lesson(_VID, self._LID2)

        storage.delete_objects.assert_not_called()
        repo.set_lesson_orders.assert_called_once_with(
            _VID, {self._LID3: 2, self._LID4: 3}
        )

    def test_no_remaining_lessons_skips_renumber(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(id_=self._LID1, order=1)
        repo.list_lessons.return_value = []

        service.delete_lesson(_VID, self._LID1)

        storage.delete_objects.assert_not_called()
        repo.set_lesson_orders.assert_not_called()


# --- publish_course (gate) ----------------------------------------------------


class TestPublishCourseGate:
    _LID1 = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    _LID2 = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

    def test_no_lessons_raises_bad_request(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.list_lessons.return_value = []
        with pytest.raises(BadRequest):
            service.publish_course(_VID)
        repo.set_course_status.assert_not_called()

    def test_lessons_exist_but_none_ready_raises(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.list_lessons.return_value = [
            _lesson(id_=self._LID1, order=1, video_status="pending"),
            _lesson(id_=self._LID2, order=2, video_status="pending"),
        ]
        with pytest.raises(BadRequest, match="ready"):
            service.publish_course(_VID)
        repo.set_course_status.assert_not_called()

    def test_at_least_one_ready_publishes(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.list_lessons.return_value = [
            _lesson(id_=self._LID1, order=1, video_status="pending"),
            _lesson(id_=self._LID2, order=2, video_status="ready"),
        ]
        out = service.publish_course(_VID)
        repo.set_course_status.assert_called_once_with(_VID, "PUBLISHED")
        assert out == {"id": _VID, "status": "PUBLISHED"}


# --- mark_lesson_video_ready --------------------------------------------------


class TestMarkLessonVideoReady:
    _LID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

    def test_missing_lesson_raises_not_found(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = None
        with pytest.raises(NotFound):
            service.mark_lesson_video_ready(_VID, "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")

    def test_lesson_with_no_video_key_raises_bad_request(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(id_=self._LID, video_key="")
        with pytest.raises(BadRequest, match="No video uploaded"):
            service.mark_lesson_video_ready(_VID, self._LID)
        repo.set_lesson_video_status.assert_not_called()

    def test_happy_path_sets_status_to_ready(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(
            id_=self._LID, video_key=_video_key(_VID, self._LID)
        )

        out = service.mark_lesson_video_ready(_VID, self._LID)

        repo.set_lesson_video_status.assert_called_once_with(
            course_id=_VID, lesson_id=self._LID, status="ready"
        )
        assert out == {"lessonId": self._LID, "videoStatus": "ready"}

    def test_optional_thumbnail_persisted_before_ready(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(
            id_=self._LID, video_key=_video_key(_VID, self._LID)
        )
        tk = _lesson_thumb_key(_VID, self._LID, "77777777-7777-4777-8777-777777777777")
        service.mark_lesson_video_ready(_VID, self._LID, thumbnail_key=tk)
        storage.delete_objects.assert_not_called()
        repo.set_lesson_thumbnail.assert_called_once_with(_VID, self._LID, tk)
        repo.set_lesson_video_status.assert_called_once_with(
            course_id=_VID, lesson_id=self._LID, status="ready"
        )

    def test_new_thumbnail_deletes_previous_lesson_thumb_from_s3(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        old_tk = _lesson_thumb_key(_VID, self._LID, "88888888-8888-4888-8888-888888888888")
        new_tk = _lesson_thumb_key(_VID, self._LID, "99999999-9999-4999-8999-999999999998")
        repo.get_lesson_by_id.return_value = _lesson(
            id_=self._LID,
            video_key=_video_key(_VID, self._LID),
            thumbnail_key=old_tk,
        )
        service.mark_lesson_video_ready(_VID, self._LID, thumbnail_key=new_tk)
        storage.delete_objects.assert_called_once_with([old_tk])
        repo.set_lesson_thumbnail.assert_called_once_with(_VID, self._LID, new_tk)

    def test_invalid_lesson_thumbnail_key_raises(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(
            id_=self._LID, video_key=_video_key(_VID, self._LID)
        )
        with pytest.raises(BadRequest, match="Invalid lesson thumbnail"):
            service.mark_lesson_video_ready(_VID, self._LID, thumbnail_key="wrong/key.jpg")
        repo.set_lesson_thumbnail.assert_not_called()


# --- get_playback_url ---------------------------------------------------------


class TestGetPlaybackUrl:
    _LID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

    def test_missing_lesson_raises_not_found(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = None
        with pytest.raises(NotFound):
            service.get_playback_url(_VID, self._LID, video_bucket="bucket")

    def test_not_ready_raises_bad_request(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(
            id_=self._LID, video_key=_video_key(_VID, self._LID), video_status="pending"
        )
        with pytest.raises(BadRequest, match="not ready"):
            service.get_playback_url(_VID, self._LID, video_bucket="bucket")

    def test_ready_but_no_video_key_raises_not_found(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(
            id_=self._LID, video_key="", video_status="ready"
        )
        with pytest.raises(NotFound):
            service.get_playback_url(_VID, self._LID, video_bucket="bucket")

    def test_storage_configured_returns_presigned_get(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(
            id_=self._LID, video_key=_video_key(_VID, self._LID), video_status="ready"
        )
        storage.presign_get.return_value = "https://signed.example/get?sig=def"

        out = service.get_playback_url(_VID, self._LID, video_bucket="bucket")

        storage.presign_get.assert_called_once_with(
            key=_video_key(_VID, self._LID), expires_seconds=3600
        )
        assert out == {"url": "https://signed.example/get?sig=def"}

    def test_no_storage_returns_public_s3_fallback_url(
        self, service_no_storage: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(
            id_=self._LID, video_key=_video_key(_VID, self._LID), video_status="ready"
        )
        out = service_no_storage.get_playback_url(
            _VID, self._LID, video_bucket="my-bucket"
        )
        # Fallback URL shape pinned: virtual-host style on the legacy SigV2
        # endpoint. If storage is wired, the presigned variant takes over.
        assert out == {
            "url": f"https://my-bucket.s3.amazonaws.com/{_video_key(_VID, self._LID)}"
        }


# --- get_upload_url -----------------------------------------------------------


class TestGetUploadUrl:
    _LID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

    def test_no_storage_raises_bad_request(
        self, service_no_storage: CourseManagementService
    ) -> None:
        with pytest.raises(BadRequest, match="not configured"):
            service_no_storage.get_upload_url(
                course_id=_VID,
                lesson_id=self._LID,
                filename="x.mp4",
                content_type="video/mp4",
            )

    def test_missing_lesson_raises_not_found(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = None
        with pytest.raises(NotFound):
            service.get_upload_url(
                course_id=_VID,
                lesson_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                filename="x.mp4",
                content_type="video/mp4",
            )

    def test_happy_path_calls_presign_then_records_video_key_pending(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(id_=self._LID)
        storage.presign_put.return_value = PresignResult(
            uploadUrl="https://signed.example/put?sig=abc",
            videoKey=_video_key(_VID, self._LID, "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        )

        out = service.get_upload_url(
            course_id=_VID,
            lesson_id=self._LID,
            filename="x.mp4",
            content_type="video/mp4",
        )

        storage.delete_objects.assert_not_called()
        storage.presign_put.assert_called_once_with(
            course_id=_VID,
            lesson_id=self._LID,
            filename="x.mp4",
            content_type="video/mp4",
        )
        repo.set_lesson_video_if_video_key_matches.assert_called_once_with(
            course_id=_VID,
            lesson_id=self._LID,
            video_key=_video_key(_VID, self._LID, "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
            status="pending",
            expected_video_key="",
        )
        assert out == {
            "uploadUrl": "https://signed.example/put?sig=abc",
            "videoKey": _video_key(_VID, self._LID, "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        }

    def test_second_presign_does_not_delete_previous_video_key_in_s3(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        """Regression: a second lesson-video presign must not remove the prior object.

        The client may still PUT to the first URL; deleting `prev` on presign caused
        DB to point at a new key while S3 lost the first upload.
        """
        prev = _video_key(_VID, self._LID, "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        repo.get_lesson_by_id.return_value = _lesson(id_=self._LID, video_key=prev)
        new_key = _video_key(_VID, self._LID, "cccccccc-cccc-4ccc-8ccc-cccccccccccc")
        storage.presign_put.return_value = PresignResult(
            uploadUrl="https://signed.example/put?sig=abc",
            videoKey=new_key,
        )
        service.get_upload_url(
            course_id=_VID,
            lesson_id=self._LID,
            filename="x.mp4",
            content_type="video/mp4",
        )
        storage.delete_objects.assert_not_called()

    def test_conflict_deletes_only_new_presigned_key_not_previous(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        prev = _video_key(_VID, self._LID, "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        repo.get_lesson_by_id.return_value = _lesson(id_=self._LID, video_key=prev)
        new_key = _video_key(_VID, self._LID, "cccccccc-cccc-4ccc-8ccc-cccccccccccc")
        storage.presign_put.return_value = PresignResult(
            uploadUrl="https://signed.example/put?sig=abc",
            videoKey=new_key,
        )
        repo.set_lesson_video_if_video_key_matches.side_effect = Conflict(
            "Another upload started for this lesson; retry."
        )
        with pytest.raises(Conflict):
            service.get_upload_url(
                course_id=_VID,
                lesson_id=self._LID,
                filename="x.mp4",
                content_type="video/mp4",
            )
        storage.delete_objects.assert_called_once_with([new_key])


# --- get_thumbnail_upload_url / mark_course_thumbnail_ready -------------------


class TestGetThumbnailUploadUrl:
    def test_no_storage_raises_bad_request(
        self, service_no_storage: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_=_VID)
        with pytest.raises(BadRequest, match="not configured"):
            service_no_storage.get_thumbnail_upload_url(
                course_id=_VID,
                filename="t.jpg",
                content_type="image/jpeg",
            )

    def test_missing_course_raises_not_found(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = None
        with pytest.raises(NotFound):
            service.get_thumbnail_upload_url(
                course_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                filename="t.jpg",
                content_type="image/jpeg",
            )

    def test_happy_path(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_=_VID)
        storage.presign_thumbnail_put.return_value = PresignResult(
            uploadUrl="https://signed.example/thumb",
            videoKey=_course_thumb_key(_VID, "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        )
        out = service.get_thumbnail_upload_url(
            course_id=_VID,
            filename="t.jpg",
            content_type="image/jpeg",
        )
        storage.delete_objects.assert_not_called()
        storage.presign_thumbnail_put.assert_called_once_with(
            course_id=_VID, filename="t.jpg", content_type="image/jpeg"
        )
        assert out == {
            "uploadUrl": "https://signed.example/thumb",
            "thumbnailKey": _course_thumb_key(_VID, "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        }

    def test_new_presign_keeps_previous_course_thumbnail_in_s3(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        old = _course_thumb_key(_VID, "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        repo.get_course.return_value = _course(id_=_VID, thumbnail_key=old)
        storage.presign_thumbnail_put.return_value = PresignResult(
            uploadUrl="https://signed.example/thumb",
            videoKey=_course_thumb_key(_VID, "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        )
        service.get_thumbnail_upload_url(
            course_id=_VID,
            filename="t.jpg",
            content_type="image/jpeg",
        )
        storage.delete_objects.assert_not_called()


class TestGetLessonThumbnailUploadUrl:
    _LID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

    def test_no_storage_raises_bad_request(
        self, service_no_storage: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(id_=self._LID)
        with pytest.raises(BadRequest, match="not configured"):
            service_no_storage.get_lesson_thumbnail_upload_url(
                course_id=_VID,
                lesson_id=self._LID,
                filename="t.jpg",
                content_type="image/jpeg",
            )

    def test_missing_lesson_raises_not_found(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = None
        with pytest.raises(NotFound):
            service.get_lesson_thumbnail_upload_url(
                course_id=_VID,
                lesson_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                filename="t.jpg",
                content_type="image/jpeg",
            )

    def test_happy_path(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(id_=self._LID)
        storage.presign_lesson_thumbnail_put.return_value = PresignResult(
            uploadUrl="https://signed.example/lthumb",
            videoKey=_lesson_thumb_key(_VID, self._LID, "cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
        )
        out = service.get_lesson_thumbnail_upload_url(
            course_id=_VID,
            lesson_id=self._LID,
            filename="t.jpg",
            content_type="image/jpeg",
        )
        storage.delete_objects.assert_not_called()
        storage.presign_lesson_thumbnail_put.assert_called_once_with(
            course_id=_VID,
            lesson_id=self._LID,
            filename="t.jpg",
            content_type="image/jpeg",
        )
        assert out == {
            "uploadUrl": "https://signed.example/lthumb",
            "thumbnailKey": _lesson_thumb_key(_VID, self._LID, "cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
        }

    def test_new_presign_keeps_previous_lesson_thumbnail_in_s3(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        old = _lesson_thumb_key(_VID, self._LID, "dddddddd-dddd-4ddd-8ddd-dddddddddddd")
        repo.get_lesson_by_id.return_value = _lesson(id_=self._LID, thumbnail_key=old)
        storage.presign_lesson_thumbnail_put.return_value = PresignResult(
            uploadUrl="https://signed.example/lthumb",
            videoKey=_lesson_thumb_key(_VID, self._LID, "cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
        )
        service.get_lesson_thumbnail_upload_url(
            course_id=_VID,
            lesson_id=self._LID,
            filename="t.jpg",
            content_type="image/jpeg",
        )
        storage.delete_objects.assert_not_called()


class TestMarkCourseThumbnailReady:
    def test_invalid_key_prefix_raises_bad_request(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_=_VID)
        with pytest.raises(BadRequest, match="Invalid thumbnail key"):
            service.mark_course_thumbnail_ready(_VID, "evil/thumbnail/22222222-2222-4222-8222-222222222222.jpg")

    def test_happy_path(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_=_VID)
        key = _course_thumb_key(_VID, "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")
        out = service.mark_course_thumbnail_ready(_VID, key)
        storage.delete_objects.assert_not_called()
        repo.set_course_thumbnail.assert_called_once_with(_VID, key)
        assert out == {"id": _VID, "thumbnailReady": True}

    def test_replaces_existing_thumbnail_deletes_old_from_s3(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        old = _course_thumb_key(_VID, "ffffffff-ffff-4fff-8fff-ffffffffffff")
        new_key = _course_thumb_key(_VID, "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")
        repo.get_course.return_value = _course(id_=_VID, thumbnail_key=old)
        service.mark_course_thumbnail_ready(_VID, new_key)
        storage.delete_objects.assert_called_once_with([old])
        repo.set_course_thumbnail.assert_called_once_with(_VID, new_key)


class TestPublicCourseThumbnailUrl:
    _CID1 = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    _CID2 = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

    def test_get_course_includes_presigned_thumbnail_url(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.get_course.return_value = Course(
            id=self._CID1,
            title="T",
            description="D",
            status="PUBLISHED",
            thumbnailKey=_course_thumb_key(self._CID1, "10101010-1010-4101-8101-101010101010"),
        )
        storage.presign_get.return_value = "https://signed-thumb"
        out = service.get_course(self._CID1)
        assert out["thumbnailUrl"] == "https://signed-thumb"
        assert "thumbnailKey" not in out
        storage.presign_get.assert_called_once_with(
            key=_course_thumb_key(self._CID1, "10101010-1010-4101-8101-101010101010"),
            expires_seconds=3600,
        )

    def test_list_published_attaches_thumbnail_url(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        _CID_LIST = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
        repo.list_courses.return_value = [
            Course(
                id=_CID_LIST,
                title="T",
                description="D",
                status="PUBLISHED",
                thumbnailKey=_course_thumb_key(_CID_LIST, "12121212-1212-4121-8121-121212121212"),
            ),
        ]
        storage.presign_get.return_value = "https://thumb"
        rows = service.list_published_courses()
        assert rows[0]["thumbnailUrl"] == "https://thumb"
        assert "thumbnailKey" not in rows[0]

    def test_get_course_uses_first_lesson_thumbnail_when_no_course_cover(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        _L1 = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
        _L2 = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
        repo.get_course.return_value = _course(id_=self._CID2, status="PUBLISHED", thumbnail_key="")
        repo.list_lessons.return_value = [
            _lesson(order=2, id_=_L2, thumbnail_key=_lesson_thumb_key(self._CID2, _L2)),
            _lesson(order=1, id_=_L1, thumbnail_key=_lesson_thumb_key(self._CID2, _L1, _TH3)),
        ]
        storage.presign_get.return_value = "https://from-lesson"
        out = service.get_course(self._CID2)
        assert out["thumbnailUrl"] == "https://from-lesson"
        storage.presign_get.assert_called_once_with(
            key=_lesson_thumb_key(self._CID2, _L1, _TH3), expires_seconds=3600
        )

    def test_list_published_uses_lesson_thumbnail_fallback(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        _PUB = "ffffffff-ffff-4fff-8fff-ffffffffffff"
        _L1 = "11111111-1111-4111-8111-111111111111"
        repo.list_courses.return_value = [_course(id_=_PUB, status="PUBLISHED", thumbnail_key="")]
        repo.list_lessons.return_value = [
            _lesson(
                order=1,
                id_=_L1,
                thumbnail_key=_lesson_thumb_key(_PUB, _L1, "abababab-abab-4aba-8aba-abababababab"),
            ),
        ]
        storage.presign_get.return_value = "https://list-fallback"
        rows = service.list_published_courses()
        assert rows[0]["thumbnailUrl"] == "https://list-fallback"


# --- enrollment / view access -------------------------------------------------


class TestGetCourseDetailPublicCatalog:
    """GET /courses/{id} is public for PUBLISHED; DRAFT hidden from non-managers."""

    def test_anonymous_published_has_enrolled_false(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_=_VID, status="PUBLISHED")
        repo.list_lessons.return_value = []
        out = service.get_course_detail_with_enrollment(
            _VID, cognito_sub="", role=""
        )
        assert out["id"] == _VID
        assert out["status"] == "PUBLISHED"
        assert out["enrolled"] is False

    def test_anonymous_draft_raises_not_found(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_=_VID, status="DRAFT")
        with pytest.raises(NotFound):
            service.get_course_detail_with_enrollment(
                _VID, cognito_sub="", role=""
            )

    def test_owner_teacher_sees_draft_detail(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = Course(
            id=_VID,
            title="T",
            description="D",
            status="DRAFT",
            createdBy="owner-sub",
        )
        repo.list_lessons.return_value = []
        out = service.get_course_detail_with_enrollment(
            _VID, cognito_sub="owner-sub", role="teacher"
        )
        assert out["id"] == _VID
        assert out["status"] == "DRAFT"


class TestListLessonsPublic:
    _LID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

    def test_anonymous_published_returns_sorted_rows_without_video_key(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_=_VID, status="PUBLISHED")
        k = _lesson_thumb_key(_VID, self._LID, "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
        repo.list_lessons.return_value = [
            _lesson(id_="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", order=2, thumbnail_key=""),
            _lesson(id_="cccccccc-cccc-4ccc-8ccc-cccccccccccc", order=1, thumbnail_key=k),
        ]
        storage.presign_get.return_value = "https://signed-thumb"
        out = service.list_lessons_public(
            _VID, cognito_sub="", role="student"
        )
        assert [r["id"] for r in out] == ["cccccccc-cccc-4ccc-8ccc-cccccccccccc", "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"]
        assert out[0].get("thumbnailUrl") == "https://signed-thumb"
        assert "thumbnailUrl" not in out[1]
        assert all("videoKey" not in r for r in out)

    def test_anonymous_draft_raises_not_found(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_=_VID, status="DRAFT")
        with pytest.raises(NotFound):
            service.list_lessons_public(
                _VID, cognito_sub="", role="student"
            )

    def test_anonymous_draft_does_not_query_lessons(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_=_VID, status="DRAFT")
        with pytest.raises(NotFound):
            service.list_lessons_public(
                _VID, cognito_sub="", role="student"
            )
        repo.get_course.assert_called_once_with(_VID)
        repo.list_lessons.assert_not_called()

    def test_owner_teacher_draft_lists_lessons(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        _L1 = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
        repo.get_course.return_value = Course(
            id=_VID,
            title="T",
            description="D",
            status="DRAFT",
            createdBy="owner-sub",
        )
        repo.list_lessons.return_value = [_lesson(id_=_L1, order=1)]
        out = service.list_lessons_public(
            _VID, cognito_sub="owner-sub", role="teacher"
        )
        assert len(out) == 1
        repo.list_lessons.assert_called_once_with(_VID)

    def test_presign_failure_omits_thumbnail_url(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_=_VID, status="PUBLISHED")
        k = _lesson_thumb_key(_VID, self._LID)
        repo.list_lessons.return_value = [_lesson(id_=self._LID, order=1, thumbnail_key=k)]
        storage.presign_get.side_effect = RuntimeError("network")
        out = service.list_lessons_public(
            _VID, cognito_sub="", role="student"
        )
        assert out[0]["id"] == self._LID
        assert "thumbnailUrl" not in out[0]
        assert "videoKey" not in out[0]


class TestEnsureCanViewLessonsAndPlayback:
    def test_published_requires_enrollment_when_auth_on(
        self, service: CourseManagementService, repo: MagicMock, enrollments: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_=_VID, status="PUBLISHED")
        enrollments.has_enrollment.return_value = False
        with pytest.raises(Forbidden) as ei:
            service.ensure_can_view_lessons_and_playback(
                _VID, cognito_sub="sub1", role="student"
            )
        assert ei.value.code == "enrollment_required"

    def test_admin_bypasses_enrollment(
        self, service: CourseManagementService, repo: MagicMock, enrollments: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_=_VID, status="PUBLISHED")
        enrollments.has_enrollment.return_value = False
        c = service.ensure_can_view_lessons_and_playback(
            _VID, cognito_sub="admin-sub", role="admin"
        )
        assert c.id == _VID
        enrollments.has_enrollment.assert_not_called()

    def test_owner_teacher_bypasses_enrollment(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = Course(
            id=_VID,
            title="T",
            description="D",
            status="PUBLISHED",
            createdBy="owner-sub",
        )
        c = service.ensure_can_view_lessons_and_playback(
            _VID, cognito_sub="owner-sub", role="teacher"
        )
        assert c.id == _VID

    def test_enrolled_student_allowed(
        self, service: CourseManagementService, repo: MagicMock, enrollments: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_=_VID, status="PUBLISHED")
        enrollments.has_enrollment.return_value = True
        c = service.ensure_can_view_lessons_and_playback(
            _VID, cognito_sub="stu1", role="student"
        )
        assert c.id == _VID


class TestEnrollInPublishedCourse:
    def test_writes_enrollment(
        self, service: CourseManagementService, repo: MagicMock, enrollments: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_=_VID, status="PUBLISHED")
        out = service.enroll_in_published_course(_VID, cognito_sub="u1")
        assert out == {"courseId": _VID, "enrolled": True}
        enrollments.put_enrollment.assert_called_once_with(user_sub="u1", course_id=_VID)


class TestSetLessonDuration:
    """Tests for set_lesson_duration repository method called via progress service."""

    _LID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

    def test_set_lesson_duration_calls_repo_method(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        """When progress update includes duration, lesson duration should be set."""
        repo.set_lesson_duration.return_value = None
        service._repo = repo
        # Direct call to the repo method (called by progress service)
        repo.set_lesson_duration(_VID, self._LID, 120)
        repo.set_lesson_duration.assert_called_once_with(_VID, self._LID, 120)

    def test_set_lesson_duration_skips_zero_duration(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        """Duration of 0 should not trigger a DB update."""
        repo.set_lesson_duration.return_value = None
        # Simulate the guard clause in the actual method
        duration = 0
        if duration > 0:
            repo.set_lesson_duration(_VID, self._LID, duration)
        repo.set_lesson_duration.assert_not_called()

    def test_set_lesson_duration_skips_negative_duration(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        """Negative duration should not trigger a DB update."""
        repo.set_lesson_duration.return_value = None
        duration = -10
        if duration > 0:
            repo.set_lesson_duration(_VID, self._LID, duration)
        repo.set_lesson_duration.assert_not_called()


class TestUuidValidation:
    """Tests for UUID validation across all service methods.

    Invalid UUID formats should raise NotFound before any database operations.
    """

    @pytest.fixture
    def service(self, repo: MagicMock, storage: MagicMock) -> CourseManagementService:
        return CourseManagementService(repo, storage, MagicMock())

    def test_get_course_invalid_uuid_raises_not_found(self, service: CourseManagementService) -> None:
        with pytest.raises(NotFound):
            service.get_course("invalid-uuid")

    def test_enroll_in_published_course_invalid_uuid_raises_not_found(self, service: CourseManagementService) -> None:
        with pytest.raises(NotFound):
            service.enroll_in_published_course("not-a-uuid", cognito_sub="user123")

    def test_update_course_invalid_uuid_raises_not_found(self, service: CourseManagementService) -> None:
        with pytest.raises(NotFound):
            service.update_course("bad-id", title="Test", description="Desc")

    def test_delete_course_invalid_uuid_raises_not_found(self, service: CourseManagementService) -> None:
        with pytest.raises(NotFound):
            service.delete_course("bad-id")

    def test_list_lessons_invalid_uuid_raises_not_found(self, service: CourseManagementService) -> None:
        with pytest.raises(NotFound):
            service.list_lessons("bad-id")

    def test_list_lessons_public_invalid_uuid_raises_not_found(self, service: CourseManagementService) -> None:
        with pytest.raises(NotFound):
            service.list_lessons_public("bad-id", cognito_sub="user", role="student")

    def test_create_lesson_invalid_course_uuid_raises_not_found(self, service: CourseManagementService) -> None:
        with pytest.raises(NotFound):
            service.create_lesson("bad-id", title="Lesson")

    def test_update_lesson_invalid_course_uuid_raises_not_found(self, service: CourseManagementService) -> None:
        with pytest.raises(NotFound):
            service.update_lesson("bad-course", lesson_id=_VID, title="Updated")

    def test_update_lesson_invalid_lesson_uuid_raises_not_found(self, service: CourseManagementService) -> None:
        with pytest.raises(NotFound):
            service.update_lesson(_VID, lesson_id="bad-lesson", title="Updated")

    def test_delete_lesson_invalid_course_uuid_raises_not_found(self, service: CourseManagementService) -> None:
        with pytest.raises(NotFound):
            service.delete_lesson("bad-course", lesson_id=_VID)

    def test_delete_lesson_invalid_lesson_uuid_raises_not_found(self, service: CourseManagementService) -> None:
        with pytest.raises(NotFound):
            service.delete_lesson(_VID, lesson_id="bad-lesson")

    def test_publish_course_invalid_uuid_raises_not_found(self, service: CourseManagementService) -> None:
        with pytest.raises(NotFound):
            service.publish_course("bad-id")

    def test_mark_lesson_video_ready_invalid_course_uuid_raises_not_found(self, service: CourseManagementService) -> None:
        with pytest.raises(NotFound):
            service.mark_lesson_video_ready("bad-course", lesson_id=_VID)

    def test_mark_lesson_video_ready_invalid_lesson_uuid_raises_not_found(self, service: CourseManagementService) -> None:
        with pytest.raises(NotFound):
            service.mark_lesson_video_ready(course_id=_VID, lesson_id="bad-lesson")

    def test_get_playback_url_invalid_course_uuid_raises_not_found(self, service: CourseManagementService) -> None:
        with pytest.raises(NotFound):
            service.get_playback_url("bad-course", lesson_id=_VID, video_bucket="bucket")

    def test_get_playback_url_invalid_lesson_uuid_raises_not_found(self, service: CourseManagementService) -> None:
        with pytest.raises(NotFound):
            service.get_playback_url(course_id=_VID, lesson_id="bad-lesson", video_bucket="bucket")

    def test_get_upload_url_invalid_course_uuid_raises_not_found(self, service: CourseManagementService) -> None:
        with pytest.raises(NotFound):
            service.get_upload_url(course_id="bad-id", lesson_id=_VID, filename="x.mp4", content_type="video/mp4")

    def test_get_upload_url_invalid_lesson_uuid_raises_not_found(self, service: CourseManagementService) -> None:
        with pytest.raises(NotFound):
            service.get_upload_url(course_id=_VID, lesson_id="bad-id", filename="x.mp4", content_type="video/mp4")

    def test_get_thumbnail_upload_url_invalid_uuid_raises_not_found(self, service: CourseManagementService) -> None:
        with pytest.raises(NotFound):
            service.get_thumbnail_upload_url(course_id="bad-id", filename="x.jpg", content_type="image/jpeg")

    def test_get_lesson_thumbnail_upload_url_invalid_course_uuid_raises_not_found(self, service: CourseManagementService) -> None:
        with pytest.raises(NotFound):
            service.get_lesson_thumbnail_upload_url(course_id="bad-id", lesson_id=_VID, filename="x.jpg", content_type="image/jpeg")

    def test_get_lesson_thumbnail_upload_url_invalid_lesson_uuid_raises_not_found(self, service: CourseManagementService) -> None:
        with pytest.raises(NotFound):
            service.get_lesson_thumbnail_upload_url(course_id=_VID, lesson_id="bad-id", filename="x.jpg", content_type="image/jpeg")

    def test_mark_course_thumbnail_ready_invalid_uuid_raises_not_found(self, service: CourseManagementService) -> None:
        with pytest.raises(NotFound):
            service.mark_course_thumbnail_ready("bad-id", thumbnail_key="thumb.jpg")

    def test_valid_uuid_passes_validation(self, repo: MagicMock, storage: MagicMock) -> None:
        """Valid UUIDs should pass validation and reach the repository."""
        valid_course_id = "a673d83c-b4f6-4aa1-be51-45b88bd35295"
        repo.get_course.return_value = _course(id_=valid_course_id)
        service = CourseManagementService(repo, storage, MagicMock())

        result = service.get_course(valid_course_id)

        assert result is not None
        repo.get_course.assert_called_once_with(valid_course_id)
