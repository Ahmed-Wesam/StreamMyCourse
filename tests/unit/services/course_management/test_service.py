"""Unit tests for `services.course_management.service.CourseManagementService`.

The service is constructor-injected with a repo + (optional) storage port, so
we hand it `MagicMock` doubles directly. No patching of module globals — the
ports are the only seam we need.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.common.errors import BadRequest, Conflict, Forbidden, NotFound
from services.course_management.models import Course, Lesson, PresignResult
from services.course_management.service import CourseManagementService


def _lesson(
    *,
    id_: str = "lid",
    order: int = 1,
    video_key: str = "",
    video_status: str = "pending",
    title: str = "L",
    thumbnail_key: str = "",
) -> Lesson:
    return Lesson(
        id=id_,
        title=title,
        order=order,
        videoKey=video_key,
        videoStatus=video_status,
        duration=0,
        thumbnailKey=thumbnail_key,
    )


def _course(
    *,
    id_: str = "cid",
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


# --- list_published_courses ---------------------------------------------------


class TestListPublishedCourses:
    def test_filters_to_published(self, service: CourseManagementService, repo: MagicMock) -> None:
        repo.list_courses.return_value = [
            _course(id_="a", status="DRAFT"),
            _course(id_="b", status="PUBLISHED"),
            _course(id_="c", status="PUBLISHED"),
        ]
        repo.list_lessons.return_value = []
        published = service.list_published_courses()
        assert [c["id"] for c in published] == ["b", "c"]

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
            _course(id_="d1", status="DRAFT", created_by="sub-a"),
        ]
        repo.list_lessons.return_value = []
        out = service.list_instructor_courses(
            cognito_sub="sub-a", role="teacher", auth_enforced=True
        )
        repo.list_courses_by_instructor.assert_called_once_with("sub-a")
        repo.list_courses.assert_not_called()
        assert len(out) == 1
        assert out[0]["id"] == "d1"
        assert out[0]["status"] == "DRAFT"

    def test_admin_lists_all_courses(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.list_courses.return_value = [
            _course(id_="x", status="PUBLISHED"),
            _course(id_="y", status="DRAFT"),
        ]
        repo.list_lessons.return_value = []
        out = service.list_instructor_courses(
            cognito_sub="admin-sub", role="admin", auth_enforced=True
        )
        repo.list_courses.assert_called_once()
        repo.list_courses_by_instructor.assert_not_called()
        assert {c["id"] for c in out} == {"x", "y"}

    def test_unauth_dev_lists_all(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.list_courses.return_value = [_course(id_="z")]
        repo.list_lessons.return_value = []
        service.list_instructor_courses(
            cognito_sub="", role="teacher", auth_enforced=False
        )
        repo.list_courses.assert_called_once()
        repo.list_courses_by_instructor.assert_not_called()


# --- get_course ---------------------------------------------------------------


class TestGetCourse:
    def test_missing_raises_not_found(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = None
        with pytest.raises(NotFound):
            service.get_course("missing")

    def test_existing_course_returned_as_dict(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_="c1", status="PUBLISHED")
        repo.list_lessons.return_value = []
        out = service.get_course("c1")
        assert out["id"] == "c1"
        assert out["status"] == "PUBLISHED"


# --- create_course ------------------------------------------------------------


class TestCreateCourse:
    def test_falls_back_to_untitled_for_blank_title(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.create_course.return_value = _course(id_="c1")
        service.create_course("", "")
        repo.create_course.assert_called_once_with(
            title="Untitled Course", description="", created_by=""
        )

    def test_returns_id_and_status(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.create_course.return_value = _course(id_="c1", status="DRAFT")
        out = service.create_course("Title", "Desc")
        assert out == {"id": "c1", "status": "DRAFT"}


class TestUpdateCourse:
    def test_delegates_and_returns_updated(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        out = service.update_course("c1", "T2", "D2")
        repo.update_course.assert_called_once_with(
            course_id="c1", title="T2", description="D2"
        )
        assert out == {"id": "c1", "updated": True}


class TestListLessons:
    def test_returns_dicts(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.list_lessons.return_value = [
            _lesson(id_="lid-1", order=1),
            _lesson(id_="lid-2", order=2),
        ]
        out = service.list_lessons("c1")
        assert [l["id"] for l in out] == ["lid-1", "lid-2"]
        assert all("videoKey" not in l for l in out)

    def test_strips_video_key_from_public_lesson_dict(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.list_lessons.return_value = [
            _lesson(id_="l1", order=1, video_key=_video_key("c1", "l1", "99999999-9999-4999-8999-999999999999"))
        ]
        out = service.list_lessons("c1")
        assert "videoKey" not in out[0]

    def test_presigned_thumbnail_url_when_key_set(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        k = _lesson_thumb_key("c1", "lid", "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
        repo.list_lessons.return_value = [
            _lesson(id_="lid", order=1, thumbnail_key=k),
        ]
        storage.presign_get.return_value = "https://signed-lesson-thumb"
        out = service.list_lessons("c1")
        assert out[0]["thumbnailUrl"] == "https://signed-lesson-thumb"
        storage.presign_get.assert_called_once_with(key=k, expires_seconds=3600)


class TestCreateLessonService:
    def test_returns_lesson_id_and_order(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.create_lesson.return_value = _lesson(id_="lid-1", order=1)
        out = service.create_lesson("c1", "")
        repo.create_lesson.assert_called_once_with(course_id="c1", title="Lesson")
        assert out == {"lessonId": "lid-1", "order": 1}


# --- delete_course ------------------------------------------------------------


class TestDeleteCourse:
    def test_missing_course_raises_not_found(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = None
        with pytest.raises(NotFound, match="Course not found"):
            service.delete_course("nope")
        repo.delete_course_and_lessons.assert_not_called()

    def test_delegates_to_repo(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_="c1")
        repo.list_lessons.return_value = []
        out = service.delete_course("c1")
        repo.delete_course_and_lessons.assert_called_once_with("c1")
        assert out == {"id": "c1", "deleted": True}

    def test_deletes_db_before_s3(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(
            id_="c1", thumbnail_key=_course_thumb_key("c1", _TH3)
        )
        repo.list_lessons.return_value = [
            _lesson(
                id_="l1",
                video_key=_video_key("c1", "l1"),
                thumbnail_key=_lesson_thumb_key("c1", "l1", _TH4),
            ),
        ]
        order: list[str] = []

        def _mark_db(*_a: object, **_k: object) -> None:
            order.append("db")

        def _mark_s3(*_a: object, **_k: object) -> list[str]:
            order.append("s3")
            return []

        repo.delete_course_and_lessons.side_effect = _mark_db
        storage.delete_objects.side_effect = _mark_s3
        service.delete_course("c1")
        assert order == ["db", "s3"]
        storage.delete_objects.assert_called_once()
        keys = storage.delete_objects.call_args[0][0]
        assert set(keys) == {
            _course_thumb_key("c1", _TH3),
            _video_key("c1", "l1"),
            _lesson_thumb_key("c1", "l1", _TH4),
        }
        repo.delete_course_and_lessons.assert_called_once_with("c1")

    def test_s3_failure_still_deletes_course_in_db(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_="c1")
        repo.list_lessons.return_value = [_lesson(id_="l1", video_key=_video_key("c1", "l1"))]
        storage.delete_objects.side_effect = RuntimeError("boom")
        out = service.delete_course("c1")
        assert out == {"id": "c1", "deleted": True}
        repo.delete_course_and_lessons.assert_called_once_with("c1")

    def test_without_storage_skips_s3(
        self, service_no_storage: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_="c1")
        repo.list_lessons.return_value = [_lesson(id_="l1", video_key=_video_key("c1", "l1"))]
        out = service_no_storage.delete_course("c1")
        assert out == {"id": "c1", "deleted": True}
        repo.delete_course_and_lessons.assert_called_once_with("c1")


# --- update_lesson ------------------------------------------------------------


class TestUpdateLesson:
    def test_missing_lesson_raises(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = None
        with pytest.raises(NotFound):
            service.update_lesson("c1", "lid", "new title")

    def test_blank_title_falls_back_to_existing(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(id_="lid", title="Old Title")
        service.update_lesson("c1", "lid", "")
        repo.update_lesson_title.assert_called_once_with(
            course_id="c1", lesson_id="lid", title="Old Title"
        )


# --- delete_lesson + order compaction -----------------------------------------


class TestDeleteLessonOrderCompaction:
    def test_missing_raises_not_found(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = None
        with pytest.raises(NotFound):
            service.delete_lesson("c1", "missing")

    def test_deletes_s3_before_repo(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(
            id_="lid-2",
            order=2,
            video_key=_video_key("c1", "lid-2", "66666666-6666-4666-8666-666666666666"),
            thumbnail_key=_lesson_thumb_key("c1", "lid-2"),
        )
        repo.list_lessons.return_value = []
        service.delete_lesson("c1", "lid-2")
        storage.delete_objects.assert_called_once_with(
            [
                _video_key("c1", "lid-2", "66666666-6666-4666-8666-666666666666"),
                _lesson_thumb_key("c1", "lid-2"),
            ]
        )
        repo.delete_lesson.assert_called_once_with(course_id="c1", lesson_id="lid-2")

    def test_compacts_remaining_orders_to_one_through_n(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        # Starting state: lessons of orders [1,2,3,4] with stable ids.
        # We delete the order=2 lesson, so the remaining (1,3,4) must be
        # renumbered to (1,2,3) preserving their relative order.
        l1 = _lesson(id_="lid-1", order=1)
        l3 = _lesson(id_="lid-3", order=3)
        l4 = _lesson(id_="lid-4", order=4)
        repo.get_lesson_by_id.return_value = _lesson(id_="lid-2", order=2)
        repo.list_lessons.return_value = [l1, l3, l4]

        service.delete_lesson("c1", "lid-2")

        storage.delete_objects.assert_not_called()
        repo.delete_lesson.assert_called_once_with(course_id="c1", lesson_id="lid-2")
        repo.set_lesson_orders.assert_called_once_with(
            "c1", {"lid-1": 1, "lid-3": 2, "lid-4": 3}
        )

    def test_preserves_order_when_unsorted_input_returned(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        # Belt-and-suspenders: even if the repo returns unsorted lessons,
        # the service must sort by `order` before reassigning.
        l1 = _lesson(id_="lid-1", order=1)
        l3 = _lesson(id_="lid-3", order=3)
        l4 = _lesson(id_="lid-4", order=4)
        repo.get_lesson_by_id.return_value = _lesson(id_="lid-2", order=2)
        repo.list_lessons.return_value = [l4, l1, l3]  # intentionally jumbled

        service.delete_lesson("c1", "lid-2")

        storage.delete_objects.assert_not_called()
        # Mapping must reflect the *sorted* iteration, not the input order.
        repo.set_lesson_orders.assert_called_once_with(
            "c1", {"lid-1": 1, "lid-3": 2, "lid-4": 3}
        )

    def test_no_remaining_lessons_skips_renumber(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(id_="lid-1", order=1)
        repo.list_lessons.return_value = []

        service.delete_lesson("c1", "lid-1")

        storage.delete_objects.assert_not_called()
        repo.set_lesson_orders.assert_not_called()


# --- publish_course (gate) ----------------------------------------------------


class TestPublishCourseGate:
    def test_no_lessons_raises_bad_request(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.list_lessons.return_value = []
        with pytest.raises(BadRequest):
            service.publish_course("c1")
        repo.set_course_status.assert_not_called()

    def test_lessons_exist_but_none_ready_raises(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.list_lessons.return_value = [
            _lesson(id_="lid-1", order=1, video_status="pending"),
            _lesson(id_="lid-2", order=2, video_status="pending"),
        ]
        with pytest.raises(BadRequest, match="ready"):
            service.publish_course("c1")
        repo.set_course_status.assert_not_called()

    def test_at_least_one_ready_publishes(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.list_lessons.return_value = [
            _lesson(id_="lid-1", order=1, video_status="pending"),
            _lesson(id_="lid-2", order=2, video_status="ready"),
        ]
        out = service.publish_course("c1")
        repo.set_course_status.assert_called_once_with("c1", "PUBLISHED")
        assert out == {"id": "c1", "status": "PUBLISHED"}


# --- mark_lesson_video_ready --------------------------------------------------


class TestMarkLessonVideoReady:
    def test_missing_lesson_raises_not_found(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = None
        with pytest.raises(NotFound):
            service.mark_lesson_video_ready("c1", "lid-x")

    def test_lesson_with_no_video_key_raises_bad_request(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(id_="lid", video_key="")
        with pytest.raises(BadRequest, match="No video uploaded"):
            service.mark_lesson_video_ready("c1", "lid")
        repo.set_lesson_video_status.assert_not_called()

    def test_happy_path_sets_status_to_ready(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(
            id_="lid", video_key=_video_key("c1", "lid")
        )

        out = service.mark_lesson_video_ready("c1", "lid")

        repo.set_lesson_video_status.assert_called_once_with(
            course_id="c1", lesson_id="lid", status="ready"
        )
        assert out == {"lessonId": "lid", "videoStatus": "ready"}

    def test_optional_thumbnail_persisted_before_ready(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(
            id_="lid", video_key=_video_key("c1", "lid")
        )
        tk = _lesson_thumb_key("c1", "lid", "77777777-7777-4777-8777-777777777777")
        service.mark_lesson_video_ready("c1", "lid", thumbnail_key=tk)
        storage.delete_objects.assert_not_called()
        repo.set_lesson_thumbnail.assert_called_once_with("c1", "lid", tk)
        repo.set_lesson_video_status.assert_called_once_with(
            course_id="c1", lesson_id="lid", status="ready"
        )

    def test_new_thumbnail_deletes_previous_lesson_thumb_from_s3(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        old_tk = _lesson_thumb_key("c1", "lid", "88888888-8888-4888-8888-888888888888")
        new_tk = _lesson_thumb_key("c1", "lid", "99999999-9999-4999-8999-999999999998")
        repo.get_lesson_by_id.return_value = _lesson(
            id_="lid",
            video_key=_video_key("c1", "lid"),
            thumbnail_key=old_tk,
        )
        service.mark_lesson_video_ready("c1", "lid", thumbnail_key=new_tk)
        storage.delete_objects.assert_called_once_with([old_tk])
        repo.set_lesson_thumbnail.assert_called_once_with("c1", "lid", new_tk)

    def test_invalid_lesson_thumbnail_key_raises(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(
            id_="lid", video_key=_video_key("c1", "lid")
        )
        with pytest.raises(BadRequest, match="Invalid lesson thumbnail"):
            service.mark_lesson_video_ready("c1", "lid", thumbnail_key="wrong/key.jpg")
        repo.set_lesson_thumbnail.assert_not_called()


# --- get_playback_url ---------------------------------------------------------


class TestGetPlaybackUrl:
    def test_missing_lesson_raises_not_found(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = None
        with pytest.raises(NotFound):
            service.get_playback_url("c1", "lid", video_bucket="bucket")

    def test_not_ready_raises_bad_request(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(
            id_="lid", video_key=_video_key("c1", "lid"), video_status="pending"
        )
        with pytest.raises(BadRequest, match="not ready"):
            service.get_playback_url("c1", "lid", video_bucket="bucket")

    def test_ready_but_no_video_key_raises_not_found(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(
            id_="lid", video_key="", video_status="ready"
        )
        with pytest.raises(NotFound):
            service.get_playback_url("c1", "lid", video_bucket="bucket")

    def test_storage_configured_returns_presigned_get(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(
            id_="lid", video_key=_video_key("c1", "lid"), video_status="ready"
        )
        storage.presign_get.return_value = "https://signed.example/get?sig=def"

        out = service.get_playback_url("c1", "lid", video_bucket="bucket")

        storage.presign_get.assert_called_once_with(
            key=_video_key("c1", "lid"), expires_seconds=3600
        )
        assert out == {"url": "https://signed.example/get?sig=def"}

    def test_no_storage_returns_public_s3_fallback_url(
        self, service_no_storage: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(
            id_="lid", video_key=_video_key("c1", "lid"), video_status="ready"
        )
        out = service_no_storage.get_playback_url(
            "c1", "lid", video_bucket="my-bucket"
        )
        # Fallback URL shape pinned: virtual-host style on the legacy SigV2
        # endpoint. If storage is wired, the presigned variant takes over.
        assert out == {
            "url": f"https://my-bucket.s3.amazonaws.com/{_video_key('c1', 'lid')}"
        }


# --- get_upload_url -----------------------------------------------------------


class TestGetUploadUrl:
    def test_no_storage_raises_bad_request(
        self, service_no_storage: CourseManagementService
    ) -> None:
        with pytest.raises(BadRequest, match="not configured"):
            service_no_storage.get_upload_url(
                course_id="c1",
                lesson_id="lid",
                filename="x.mp4",
                content_type="video/mp4",
            )

    def test_missing_lesson_raises_not_found(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = None
        with pytest.raises(NotFound):
            service.get_upload_url(
                course_id="c1",
                lesson_id="missing",
                filename="x.mp4",
                content_type="video/mp4",
            )

    def test_happy_path_calls_presign_then_records_video_key_pending(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(id_="lid")
        storage.presign_put.return_value = PresignResult(
            uploadUrl="https://signed.example/put?sig=abc",
            videoKey=_video_key("c1", "lid", "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        )

        out = service.get_upload_url(
            course_id="c1",
            lesson_id="lid",
            filename="x.mp4",
            content_type="video/mp4",
        )

        storage.delete_objects.assert_not_called()
        storage.presign_put.assert_called_once_with(
            course_id="c1",
            lesson_id="lid",
            filename="x.mp4",
            content_type="video/mp4",
        )
        repo.set_lesson_video_if_video_key_matches.assert_called_once_with(
            course_id="c1",
            lesson_id="lid",
            video_key=_video_key("c1", "lid", "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
            status="pending",
            expected_video_key="",
        )
        assert out == {
            "uploadUrl": "https://signed.example/put?sig=abc",
            "videoKey": _video_key("c1", "lid", "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        }

    def test_second_presign_does_not_delete_previous_video_key_in_s3(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        """Regression: a second lesson-video presign must not remove the prior object.

        The client may still PUT to the first URL; deleting `prev` on presign caused
        DB to point at a new key while S3 lost the first upload.
        """
        prev = _video_key("c1", "lid", "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        repo.get_lesson_by_id.return_value = _lesson(id_="lid", video_key=prev)
        new_key = _video_key("c1", "lid", "cccccccc-cccc-4ccc-8ccc-cccccccccccc")
        storage.presign_put.return_value = PresignResult(
            uploadUrl="https://signed.example/put?sig=abc",
            videoKey=new_key,
        )
        service.get_upload_url(
            course_id="c1",
            lesson_id="lid",
            filename="x.mp4",
            content_type="video/mp4",
        )
        storage.delete_objects.assert_not_called()

    def test_conflict_deletes_only_new_presigned_key_not_previous(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        prev = _video_key("c1", "lid", "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        repo.get_lesson_by_id.return_value = _lesson(id_="lid", video_key=prev)
        new_key = _video_key("c1", "lid", "cccccccc-cccc-4ccc-8ccc-cccccccccccc")
        storage.presign_put.return_value = PresignResult(
            uploadUrl="https://signed.example/put?sig=abc",
            videoKey=new_key,
        )
        repo.set_lesson_video_if_video_key_matches.side_effect = Conflict(
            "Another upload started for this lesson; retry."
        )
        with pytest.raises(Conflict):
            service.get_upload_url(
                course_id="c1",
                lesson_id="lid",
                filename="x.mp4",
                content_type="video/mp4",
            )
        storage.delete_objects.assert_called_once_with([new_key])


# --- get_thumbnail_upload_url / mark_course_thumbnail_ready -------------------


class TestGetThumbnailUploadUrl:
    def test_no_storage_raises_bad_request(
        self, service_no_storage: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_="c1")
        with pytest.raises(BadRequest, match="not configured"):
            service_no_storage.get_thumbnail_upload_url(
                course_id="c1",
                filename="t.jpg",
                content_type="image/jpeg",
            )

    def test_missing_course_raises_not_found(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = None
        with pytest.raises(NotFound):
            service.get_thumbnail_upload_url(
                course_id="missing",
                filename="t.jpg",
                content_type="image/jpeg",
            )

    def test_happy_path(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_="c1")
        storage.presign_thumbnail_put.return_value = PresignResult(
            uploadUrl="https://signed.example/thumb",
            videoKey=_course_thumb_key("c1", "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        )
        out = service.get_thumbnail_upload_url(
            course_id="c1",
            filename="t.jpg",
            content_type="image/jpeg",
        )
        storage.delete_objects.assert_not_called()
        storage.presign_thumbnail_put.assert_called_once_with(
            course_id="c1", filename="t.jpg", content_type="image/jpeg"
        )
        assert out == {
            "uploadUrl": "https://signed.example/thumb",
            "thumbnailKey": _course_thumb_key("c1", "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        }

    def test_new_presign_keeps_previous_course_thumbnail_in_s3(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        old = _course_thumb_key("c1", "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        repo.get_course.return_value = _course(id_="c1", thumbnail_key=old)
        storage.presign_thumbnail_put.return_value = PresignResult(
            uploadUrl="https://signed.example/thumb",
            videoKey=_course_thumb_key("c1", "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        )
        service.get_thumbnail_upload_url(
            course_id="c1",
            filename="t.jpg",
            content_type="image/jpeg",
        )
        storage.delete_objects.assert_not_called()


class TestGetLessonThumbnailUploadUrl:
    def test_no_storage_raises_bad_request(
        self, service_no_storage: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(id_="lid")
        with pytest.raises(BadRequest, match="not configured"):
            service_no_storage.get_lesson_thumbnail_upload_url(
                course_id="c1",
                lesson_id="lid",
                filename="t.jpg",
                content_type="image/jpeg",
            )

    def test_missing_lesson_raises_not_found(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = None
        with pytest.raises(NotFound):
            service.get_lesson_thumbnail_upload_url(
                course_id="c1",
                lesson_id="missing",
                filename="t.jpg",
                content_type="image/jpeg",
            )

    def test_happy_path(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.get_lesson_by_id.return_value = _lesson(id_="lid")
        storage.presign_lesson_thumbnail_put.return_value = PresignResult(
            uploadUrl="https://signed.example/lthumb",
            videoKey=_lesson_thumb_key("c1", "lid", "cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
        )
        out = service.get_lesson_thumbnail_upload_url(
            course_id="c1",
            lesson_id="lid",
            filename="t.jpg",
            content_type="image/jpeg",
        )
        storage.delete_objects.assert_not_called()
        storage.presign_lesson_thumbnail_put.assert_called_once_with(
            course_id="c1",
            lesson_id="lid",
            filename="t.jpg",
            content_type="image/jpeg",
        )
        assert out == {
            "uploadUrl": "https://signed.example/lthumb",
            "thumbnailKey": _lesson_thumb_key("c1", "lid", "cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
        }

    def test_new_presign_keeps_previous_lesson_thumbnail_in_s3(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        old = _lesson_thumb_key("c1", "lid", "dddddddd-dddd-4ddd-8ddd-dddddddddddd")
        repo.get_lesson_by_id.return_value = _lesson(id_="lid", thumbnail_key=old)
        storage.presign_lesson_thumbnail_put.return_value = PresignResult(
            uploadUrl="https://signed.example/lthumb",
            videoKey=_lesson_thumb_key("c1", "lid", "cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
        )
        service.get_lesson_thumbnail_upload_url(
            course_id="c1",
            lesson_id="lid",
            filename="t.jpg",
            content_type="image/jpeg",
        )
        storage.delete_objects.assert_not_called()


class TestMarkCourseThumbnailReady:
    def test_invalid_key_prefix_raises_bad_request(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_="c1")
        with pytest.raises(BadRequest, match="Invalid thumbnail key"):
            service.mark_course_thumbnail_ready("c1", "evil/thumbnail/22222222-2222-4222-8222-222222222222.jpg")

    def test_happy_path(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_="c1")
        key = _course_thumb_key("c1", "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")
        out = service.mark_course_thumbnail_ready("c1", key)
        storage.delete_objects.assert_not_called()
        repo.set_course_thumbnail.assert_called_once_with("c1", key)
        assert out == {"id": "c1", "thumbnailReady": True}

    def test_replaces_existing_thumbnail_deletes_old_from_s3(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        old = _course_thumb_key("c1", "ffffffff-ffff-4fff-8fff-ffffffffffff")
        new_key = _course_thumb_key("c1", "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")
        repo.get_course.return_value = _course(id_="c1", thumbnail_key=old)
        service.mark_course_thumbnail_ready("c1", new_key)
        storage.delete_objects.assert_called_once_with([old])
        repo.set_course_thumbnail.assert_called_once_with("c1", new_key)


class TestPublicCourseThumbnailUrl:
    def test_get_course_includes_presigned_thumbnail_url(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.get_course.return_value = Course(
            id="c1",
            title="T",
            description="D",
            status="PUBLISHED",
            thumbnailKey=_course_thumb_key("c1", "10101010-1010-4101-8101-101010101010"),
        )
        storage.presign_get.return_value = "https://signed-thumb"
        out = service.get_course("c1")
        assert out["thumbnailUrl"] == "https://signed-thumb"
        assert "thumbnailKey" not in out
        storage.presign_get.assert_called_once_with(
            key=_course_thumb_key("c1", "10101010-1010-4101-8101-101010101010"),
            expires_seconds=3600,
        )

    def test_list_published_attaches_thumbnail_url(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.list_courses.return_value = [
            Course(
                id="a",
                title="T",
                description="D",
                status="PUBLISHED",
                thumbnailKey=_course_thumb_key("a", "12121212-1212-4121-8121-121212121212"),
            ),
        ]
        storage.presign_get.return_value = "https://thumb"
        rows = service.list_published_courses()
        assert rows[0]["thumbnailUrl"] == "https://thumb"
        assert "thumbnailKey" not in rows[0]

    def test_get_course_uses_first_lesson_thumbnail_when_no_course_cover(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_="c1", status="PUBLISHED", thumbnail_key="")
        repo.list_lessons.return_value = [
            _lesson(order=2, id_="l2", thumbnail_key=_lesson_thumb_key("c1", "l2")),
            _lesson(order=1, id_="l1", thumbnail_key=_lesson_thumb_key("c1", "l1", _TH3)),
        ]
        storage.presign_get.return_value = "https://from-lesson"
        out = service.get_course("c1")
        assert out["thumbnailUrl"] == "https://from-lesson"
        storage.presign_get.assert_called_once_with(
            key=_lesson_thumb_key("c1", "l1", _TH3), expires_seconds=3600
        )

    def test_list_published_uses_lesson_thumbnail_fallback(
        self, service: CourseManagementService, repo: MagicMock, storage: MagicMock
    ) -> None:
        repo.list_courses.return_value = [_course(id_="pub", status="PUBLISHED", thumbnail_key="")]
        repo.list_lessons.return_value = [
            _lesson(
                order=1,
                id_="l1",
                thumbnail_key=_lesson_thumb_key("pub", "l1", "abababab-abab-4aba-8aba-abababababab"),
            ),
        ]
        storage.presign_get.return_value = "https://list-fallback"
        rows = service.list_published_courses()
        assert rows[0]["thumbnailUrl"] == "https://list-fallback"


# --- enrollment / view access -------------------------------------------------


class TestGetCoursePreview:
    def test_published_includes_lessons_preview(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_="c1", status="PUBLISHED")
        repo.list_lessons.return_value = [
            _lesson(id_="a", order=2, title="Second"),
            _lesson(id_="b", order=1, title="First"),
        ]
        out = service.get_course_preview("c1")
        assert out["id"] == "c1"
        assert out["lessonsPreview"] == [
            {"id": "b", "title": "First", "order": 1},
            {"id": "a", "title": "Second", "order": 2},
        ]

    def test_draft_raises_not_found(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_="c1", status="DRAFT")
        with pytest.raises(NotFound):
            service.get_course_preview("c1")


class TestEnsureCanViewLessonsAndPlayback:
    def test_auth_off_allows_without_enrollment(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_="c1", status="PUBLISHED")
        c = service.ensure_can_view_lessons_and_playback(
            "c1", cognito_sub="", role="student", auth_enforced=False
        )
        assert c.id == "c1"

    def test_published_requires_enrollment_when_auth_on(
        self, service: CourseManagementService, repo: MagicMock, enrollments: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_="c1", status="PUBLISHED")
        enrollments.has_enrollment.return_value = False
        with pytest.raises(Forbidden) as ei:
            service.ensure_can_view_lessons_and_playback(
                "c1", cognito_sub="sub1", role="student", auth_enforced=True
            )
        assert ei.value.code == "enrollment_required"

    def test_admin_bypasses_enrollment(
        self, service: CourseManagementService, repo: MagicMock, enrollments: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_="c1", status="PUBLISHED")
        enrollments.has_enrollment.return_value = False
        c = service.ensure_can_view_lessons_and_playback(
            "c1", cognito_sub="admin-sub", role="admin", auth_enforced=True
        )
        assert c.id == "c1"
        enrollments.has_enrollment.assert_not_called()

    def test_owner_teacher_bypasses_enrollment(
        self, service: CourseManagementService, repo: MagicMock
    ) -> None:
        repo.get_course.return_value = Course(
            id="c1",
            title="T",
            description="D",
            status="PUBLISHED",
            createdBy="owner-sub",
        )
        c = service.ensure_can_view_lessons_and_playback(
            "c1", cognito_sub="owner-sub", role="teacher", auth_enforced=True
        )
        assert c.id == "c1"

    def test_enrolled_student_allowed(
        self, service: CourseManagementService, repo: MagicMock, enrollments: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_="c1", status="PUBLISHED")
        enrollments.has_enrollment.return_value = True
        c = service.ensure_can_view_lessons_and_playback(
            "c1", cognito_sub="stu1", role="student", auth_enforced=True
        )
        assert c.id == "c1"


class TestEnrollInPublishedCourse:
    def test_writes_enrollment(
        self, service: CourseManagementService, repo: MagicMock, enrollments: MagicMock
    ) -> None:
        repo.get_course.return_value = _course(id_="c1", status="PUBLISHED")
        out = service.enroll_in_published_course("c1", cognito_sub="u1")
        assert out == {"courseId": "c1", "enrolled": True}
        enrollments.put_enrollment.assert_called_once_with(user_sub="u1", course_id="c1")
