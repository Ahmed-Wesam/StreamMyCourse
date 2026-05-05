"""Unit tests for `CourseManagementService` media URL behavior."""

from __future__ import annotations

from typing import List, Optional

import pytest

from services.common.errors import BadRequest
from services.course_management.models import Course, Lesson
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

    def presign_get_cloudfront(self, *, key: str, expires_seconds: int, signer) -> str:  # noqa: ANN001
        return signer.sign_url(key, expires_seconds=expires_seconds)


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
        lessons = [
            Lesson(
                id="l1",
                title="Bad thumb",
                order=1,
                videoKey=f"{_CID}/lessons/{_L1}/video/11111111-1111-4111-8111-111111111111.mp4",
                videoStatus="ready",
                thumbnailKey="legacy/course-thumb.jpg",
            ),
            Lesson(
                id="l2",
                title="Good thumb",
                order=2,
                videoKey="",
                videoStatus="pending",
                thumbnailKey=(
                    f"{_CID}/lessons/{_L2}/thumbnail/"
                    "22222222-2222-4222-8222-222222222222.png"
                ),
            ),
        ]
        svc = CourseManagementService(_LessonsRepo(lessons), _FakeStorageStrict(), _FakeEnrollments())
        out = svc.list_lessons("c1")
        assert len(out) == 2
        assert "thumbnailUrl" not in out[0]
        assert (
            out[1]["thumbnailUrl"]
            == f"https://signed.test/{_CID}/lessons/{_L2}/thumbnail/22222222-2222-4222-8222-222222222222.png"
        )

    def test_list_published_courses_omits_bad_course_thumbnail(self) -> None:
        courses = [
            Course(
                id="c1",
                title="T",
                description="",
                status="PUBLISHED",
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
                    videoKey="legacy-video.mp4",
                    videoStatus="ready",
                )

        svc = CourseManagementService(_OneLessonRepo(), _FakeStorageStrict(), _FakeEnrollments())
        with pytest.raises(BadRequest):
            svc.get_playback_url("c1", "l1", video_bucket="ignored-when-storage-set")

    def test_get_playback_url_uses_cloudfront_when_signer_configured(self) -> None:
        class _Repo:
            def get_lesson_by_id(self, course_id: str, lesson_id: str) -> Optional[Lesson]:
                return Lesson(
                    id=lesson_id,
                    title="x",
                    order=1,
                    videoKey=(
                        f"{_CID}/lessons/{_L1}/video/"
                        "11111111-1111-4111-8111-111111111111.mp4"
                    ),
                    videoStatus="ready",
                )

        class _Signer:
            def sign_url(self, key: str, *, expires_seconds: int) -> str:
                return f"https://cf.example/{key}?sig=1"

        svc = CourseManagementService(
            _Repo(),
            _FakeStorageStrict(),
            _FakeEnrollments(),
            cloudfront_signer=_Signer(),
        )
        out = svc.get_playback_url("c1", "l1", video_bucket="b")
        assert out["url"].startswith("https://cf.example/")

    def test_get_playback_url_falls_back_to_s3_when_signer_missing(self) -> None:
        class _Repo:
            def get_lesson_by_id(self, course_id: str, lesson_id: str) -> Optional[Lesson]:
                return Lesson(
                    id=lesson_id,
                    title="x",
                    order=1,
                    videoKey=(
                        f"{_CID}/lessons/{_L1}/video/"
                        "11111111-1111-4111-8111-111111111111.mp4"
                    ),
                    videoStatus="ready",
                )

        svc = CourseManagementService(_Repo(), _FakeStorageStrict(), _FakeEnrollments())
        out = svc.get_playback_url("c1", "l1", video_bucket="b")
        assert out["url"].startswith("https://signed.test/")

    def test_thumbnail_url_uses_cloudfront_when_signer_configured(self) -> None:
        class _Signer:
            def sign_url(self, key: str, *, expires_seconds: int) -> str:
                return f"https://cf.example/{key}"

        thumb = f"{_CID}/lessons/{_L2}/thumbnail/22222222-2222-4222-8222-222222222222.png"
        lessons = [
            Lesson(
                id="l2",
                title="T",
                order=1,
                videoKey="",
                videoStatus="pending",
                thumbnailKey=thumb,
            ),
        ]
        svc = CourseManagementService(
            _LessonsRepo(lessons), _FakeStorageStrict(), _FakeEnrollments(), cloudfront_signer=_Signer()
        )
        out = svc.list_lessons("c1")
        assert out[0]["thumbnailUrl"].startswith("https://cf.example/")
