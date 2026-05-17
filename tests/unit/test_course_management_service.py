"""Unit tests for `CourseManagementService` media URL behavior."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from services.common.errors import BadRequest
from services.course_management.contracts import as_course_module_list
from services.course_management.models import Course, CourseModule, Lesson
from services.course_management.service import CourseManagementService
from services.course_management.storage import _is_valid_media_object_key


class _FakeEnrollments:
    def has_enrollment(self, *, user_sub: str, course_id: str) -> bool:
        return True

    def put_enrollment(self, *, user_sub: str, course_id: str, source: str = "self_service") -> None:
        return None


class _FakeStorageStrict:
    """Mirrors `CourseMediaStorage.presign_get` key validation without boto3."""

    def presign_get(self, *, key: str, expires_seconds: int = 3600) -> str:
        k = (key or "").strip()
        if not _is_valid_media_object_key(k):
            raise BadRequest("Invalid object key for playback")
        return f"https://signed.test/{k}"

    def presign_put(self, **kwargs):  # pragma: no cover - unused in these tests
        raise NotImplementedError

    def presign_thumbnail_put(self, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def presign_lesson_thumbnail_put(self, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def delete_object(self, key: str) -> None:  # pragma: no cover
        return None

    def delete_objects(self, keys):  # pragma: no cover
        return []


class _LessonsRepo:
    def __init__(self, lessons: List[Lesson]) -> None:
        self._lessons = lessons

    def list_lessons(self, course_id: str) -> List[Lesson]:
        return list(self._lessons)


class _CoursesRepo:
    def __init__(self, courses: List[Course]) -> None:
        self._courses = courses

    def list_courses(self) -> List[Course]:
        return list(self._courses)

    def list_lessons(self, course_id: str) -> List[Lesson]:
        return []


_CID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
_L1 = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
_L2 = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"


class TestSafePresignThumbnails:
    def test_list_lessons_omits_thumbnail_when_presign_rejected(self) -> None:
        _mid = "99999999-9999-4999-8999-999999999999"
        lessons = [
            Lesson(
                id=_L1,
                title="Bad thumb",
                order=1,
                moduleId=_mid,
                moduleOrder=0,
                videoKey=f"{_CID}/lessons/{_L1}/video/11111111-1111-4111-8111-111111111111.mp4",
                videoStatus="ready",
                thumbnailKey="legacy/course-thumb.jpg",
            ),
            Lesson(
                id=_L2,
                title="Good thumb",
                order=2,
                moduleId=_mid,
                moduleOrder=0,
                videoKey="",
                videoStatus="pending",
                thumbnailKey=(
                    f"{_CID}/lessons/{_L2}/thumbnail/"
                    "22222222-2222-4222-8222-222222222222.png"
                ),
            ),
        ]
        svc = CourseManagementService(_LessonsRepo(lessons), _FakeStorageStrict(), _FakeEnrollments())
        out = svc.list_lessons(_CID)
        assert len(out) == 2
        assert "thumbnailUrl" not in out[0]
        assert (
            out[1]["thumbnailUrl"]
            == f"https://signed.test/{_CID}/lessons/{_L2}/thumbnail/22222222-2222-4222-8222-222222222222.png"
        )

    def test_list_published_courses_omits_bad_course_thumbnail(self) -> None:
        courses = [
            Course(
                id=_CID,
                title="T",
                description="",
                status="PUBLISHED",
                createdBy="teacher-sub",
                thumbnailKey="not-under/valid/prefix.jpg",
            )
        ]
        svc = CourseManagementService(_CoursesRepo(courses), _FakeStorageStrict(), _FakeEnrollments())
        pub = svc.list_published_courses()
        assert len(pub) == 1
        assert "thumbnailUrl" not in pub[0]

    def test_get_playback_url_still_raises_on_invalid_video_key(self) -> None:
        class _OneLessonRepo:
            def get_lesson_by_id(self, course_id: str, lesson_id: str) -> Optional[Lesson]:
                return Lesson(
                    id=lesson_id,
                    title="x",
                    order=1,
                    moduleId="99999999-9999-4999-8999-999999999999",
                    moduleOrder=0,
                    videoKey="legacy-video.mp4",
                    videoStatus="ready",
                )

        svc = CourseManagementService(_OneLessonRepo(), _FakeStorageStrict(), _FakeEnrollments())
        with pytest.raises(BadRequest):
            svc.get_playback_url(_CID, _L1, video_bucket="ignored-when-storage-set")


_MID1 = "11111111-1111-4111-8111-111111111111"
_MID2 = "22222222-2222-4222-8222-222222222222"
_STUDENT_SUB = "student-sub-00000000-0000-4000-8000-000000000001"


class _RecordingModuleQuizVisibilityPort:
    def __init__(self, result: Dict[str, Dict[str, Any]]) -> None:
        self._result = result
        self.calls: list[dict[str, Any]] = []

    def module_quiz_visibility_by_course(
        self,
        course_id: str,
        *,
        course_status: str,
        has_lesson_access: bool,
        cognito_sub: str,
    ) -> Dict[str, Dict[str, Any]]:
        self.calls.append(
            {
                "course_id": course_id,
                "course_status": course_status,
                "has_lesson_access": has_lesson_access,
                "cognito_sub": cognito_sub,
            }
        )
        if course_status != "PUBLISHED" or not has_lesson_access:
            return {}
        return dict(self._result)


class _ModulesRepo:
    def __init__(self, *, course: Course, modules: List[CourseModule]) -> None:
        self._course = course
        self._modules = modules

    def get_course(self, course_id: str) -> Optional[Course]:
        return self._course if course_id == self._course.id else None

    def list_course_modules(self, course_id: str) -> List[CourseModule]:
        if course_id != self._course.id:
            return []
        return list(self._modules)


class _EnrollmentsWithAccess:
    def has_enrollment(self, *, user_sub: str, course_id: str) -> bool:
        return user_sub == _STUDENT_SUB and course_id == _CID

    def put_enrollment(self, *, user_sub: str, course_id: str, source: str = "self_service") -> None:
        return None


class _EnrollmentsWithoutAccess:
    def has_enrollment(self, *, user_sub: str, course_id: str) -> bool:
        return False

    def put_enrollment(self, *, user_sub: str, course_id: str, source: str = "self_service") -> None:
        return None


def _published_course() -> Course:
    return Course(
        id=_CID,
        title="Course",
        description="",
        status="PUBLISHED",
        createdBy="teacher-sub",
    )


def _draft_course() -> Course:
    return Course(
        id=_CID,
        title="Course",
        description="",
        status="DRAFT",
        createdBy="teacher-sub",
    )


def _two_modules() -> List[CourseModule]:
    return [
        CourseModule(
            id=_MID1,
            courseId=_CID,
            title="Module 1",
            description="",
            order=1,
        ),
        CourseModule(
            id=_MID2,
            courseId=_CID,
            title="Module 2",
            description="",
            order=2,
        ),
    ]


class TestListCourseModulesPublicModuleQuiz:
    def test_includes_module_quiz_when_port_returns_visibility(self) -> None:
        port = _RecordingModuleQuizVisibilityPort(
            {_MID1: {"available": True, "servedCountN": 2}}
        )
        svc = CourseManagementService(
            _ModulesRepo(course=_published_course(), modules=_two_modules()),
            None,
            _EnrollmentsWithAccess(),
            module_quiz_visibility=port,
        )
        rows = svc.list_course_modules_public(
            _CID, cognito_sub=_STUDENT_SUB, role="student"
        )
        assert rows[0]["moduleQuiz"] == {"available": True, "servedCountN": 2}
        assert "moduleQuiz" not in rows[1]
        assert port.calls == [
            {
                "course_id": _CID,
                "course_status": "PUBLISHED",
                "has_lesson_access": True,
                "cognito_sub": _STUDENT_SUB,
            }
        ]
        dto_rows = as_course_module_list(rows)
        assert dto_rows[0]["moduleQuiz"] == {"available": True, "servedCountN": 2}

    def test_omits_module_quiz_when_port_returns_empty(self) -> None:
        port = _RecordingModuleQuizVisibilityPort({})
        svc = CourseManagementService(
            _ModulesRepo(course=_published_course(), modules=_two_modules()),
            None,
            _EnrollmentsWithAccess(),
            module_quiz_visibility=port,
        )
        rows = svc.list_course_modules_public(
            _CID, cognito_sub=_STUDENT_SUB, role="student"
        )
        assert "moduleQuiz" not in rows[0]
        assert "moduleQuiz" not in rows[1]

    def test_draft_course_omits_module_quiz_even_when_port_has_data(self) -> None:
        port = _RecordingModuleQuizVisibilityPort(
            {_MID1: {"available": True, "servedCountN": 2}}
        )
        svc = CourseManagementService(
            _ModulesRepo(course=_draft_course(), modules=_two_modules()),
            None,
            _EnrollmentsWithAccess(),
            module_quiz_visibility=port,
        )
        rows = svc.list_course_modules_public(
            _CID, cognito_sub="teacher-sub", role="teacher"
        )
        assert "moduleQuiz" not in rows[0]
        assert port.calls == [
            {
                "course_id": _CID,
                "course_status": "DRAFT",
                "has_lesson_access": True,
                "cognito_sub": "teacher-sub",
            }
        ]

    def test_unenrolled_viewer_omits_module_quiz(self) -> None:
        port = _RecordingModuleQuizVisibilityPort(
            {_MID1: {"available": True, "servedCountN": 2}}
        )
        svc = CourseManagementService(
            _ModulesRepo(course=_published_course(), modules=_two_modules()),
            None,
            _EnrollmentsWithoutAccess(),
            module_quiz_visibility=port,
        )
        rows = svc.list_course_modules_public(
            _CID, cognito_sub="other-student", role="student"
        )
        assert "moduleQuiz" not in rows[0]
        assert port.calls == [
            {
                "course_id": _CID,
                "course_status": "PUBLISHED",
                "has_lesson_access": False,
                "cognito_sub": "other-student",
            }
        ]

    def test_no_port_injected_omits_module_quiz(self) -> None:
        svc = CourseManagementService(
            _ModulesRepo(course=_published_course(), modules=_two_modules()),
            None,
            _EnrollmentsWithAccess(),
        )
        rows = svc.list_course_modules_public(
            _CID, cognito_sub=_STUDENT_SUB, role="student"
        )
        assert "moduleQuiz" not in rows[0]
