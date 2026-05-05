"""S3 cleanup: deleting a course or lesson removes uploaded objects from the bucket."""

from __future__ import annotations

import time

import httpx
import pytest

from helpers.api import ApiClient
from helpers.cleanup import s3_object_exists


def _wait_until_object_absent(
    bucket: str, key: str, *, region: str, timeout_s: float = 120.0, poll_s: float = 2.0
) -> None:
    """Course delete enqueues async S3 cleanup; poll until the worker removes the object."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if not s3_object_exists(bucket, key, region=region):
            return
        time.sleep(poll_s)
    assert not s3_object_exists(bucket, key, region=region), (
        f"S3 object still present after {timeout_s}s: s3://{bucket}/{key}"
    )


@pytest.mark.slow
def test_delete_course_removes_uploaded_lesson_video(
    api: ApiClient,
    course_factory,
    lesson_factory,
    video_bucket: str,
    aws_region: str,
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

    assert s3_object_exists(video_bucket, video_key, region=aws_region)

    deleted = api.delete_course(course.course_id)
    assert deleted.status_code == 200

    _wait_until_object_absent(video_bucket, video_key, region=aws_region)


@pytest.mark.slow
def test_delete_lesson_removes_uploaded_video(
    api: ApiClient,
    course_factory,
    lesson_factory,
    video_bucket: str,
    aws_region: str,
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

    assert s3_object_exists(video_bucket, video_key, region=aws_region)

    deleted = api.delete_lesson(course.course_id, lesson.lesson_id)
    assert deleted.status_code == 200

    _wait_until_object_absent(video_bucket, video_key, region=aws_region)
