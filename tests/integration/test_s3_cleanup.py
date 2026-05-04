"""S3 cleanup: deleting a course or lesson removes uploaded objects from the bucket."""

from __future__ import annotations

import httpx
import pytest

from helpers.api import ApiClient
from helpers.cleanup import s3_object_exists


@pytest.mark.slow
def test_delete_course_removes_uploaded_lesson_video(
    api: ApiClient,
    course_factory,
    lesson_factory,
    integ_video_bucket: str,
    integ_region: str,
) -> None:
    course = course_factory()
    lesson = lesson_factory(course.course_id)

    upload = api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id)
    assert upload.status_code == 200
    body = upload.json()
    video_key = body["videoKey"]
    put = httpx.put(
        body["uploadUrl"],
        content=b"\x00" * 64,
        headers={"content-type": "video/mp4"},
        timeout=30.0,
    )
    assert put.status_code == 200

    assert s3_object_exists(integ_video_bucket, video_key, region=integ_region)

    deleted = api.delete_course(course.course_id)
    assert deleted.status_code == 200

    assert not s3_object_exists(integ_video_bucket, video_key, region=integ_region)


@pytest.mark.slow
def test_delete_lesson_removes_uploaded_video(
    api: ApiClient,
    course_factory,
    lesson_factory,
    integ_video_bucket: str,
    integ_region: str,
) -> None:
    course = course_factory()
    lesson = lesson_factory(course.course_id)

    upload = api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id)
    assert upload.status_code == 200
    body = upload.json()
    video_key = body["videoKey"]
    put = httpx.put(
        body["uploadUrl"],
        content=b"\x00" * 64,
        headers={"content-type": "video/mp4"},
        timeout=30.0,
    )
    assert put.status_code == 200

    assert s3_object_exists(integ_video_bucket, video_key, region=integ_region)

    deleted = api.delete_lesson(course.course_id, lesson.lesson_id)
    assert deleted.status_code == 200

    assert not s3_object_exists(integ_video_bucket, video_key, region=integ_region)
