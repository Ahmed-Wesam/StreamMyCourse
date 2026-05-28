"""Unit tests for KinescopeVideoAdapter init upload (mocked HTTP)."""

from __future__ import annotations

import json
from io import BytesIO
from typing import Any
from unittest.mock import patch

import pytest

from services.common.errors import BadRequest, ServiceUnavailable
from services.course_management.video_providers.kinescope_adapter import (
    KinescopeVideoAdapter,
    TUS_FILESIZE_THRESHOLD_BYTES,
)
from services.course_management.video_providers.port import VideoUploadInit

CID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
LID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
KINESCope_VIDEO_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
KINESCope_ENDPOINT = "https://uploader.kinescope.io/upload/abc123"


def _adapter() -> KinescopeVideoAdapter:
    return KinescopeVideoAdapter(
        api_token="test-token",
        parent_id="parent-folder-id",
    )


def _init_response(*, video_id: str = KINESCope_VIDEO_ID, endpoint: str = KINESCope_ENDPOINT) -> bytes:
    return json.dumps({"data": {"id": video_id, "endpoint": endpoint}}).encode("utf-8")


class TestKinescopeInitUpload:
    def test_posts_to_uploader_init_with_bearer_and_body(self) -> None:
        adapter = _adapter()
        captured: dict[str, Any] = {}

        def fake_urlopen(req: Any, timeout: float = 0) -> Any:
            captured["url"] = req.full_url
            captured["headers"] = dict(req.header_items())
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return BytesIO(_init_response())

        with patch("services.course_management.video_providers.kinescope_adapter.urlopen", side_effect=fake_urlopen):
            result = adapter.init_lesson_upload(
                course_id=CID,
                lesson_id=LID,
                filename="intro.mp4",
                content_type="video/mp4",
            )

        assert captured["url"] == "https://uploader.kinescope.io/v2/init"
        assert captured["headers"]["Authorization"] == "Bearer test-token"
        assert captured["headers"].get("Content-type") == "application/json" or captured[
            "headers"
        ].get("Content-Type") == "application/json"
        body = captured["body"]
        assert body["type"] == "video"
        assert body["parent_id"] == "parent-folder-id"
        assert body["filename"] == "intro.mp4"
        assert body["title"] == "intro"
        assert body["filesize"] == 1
        assert result == VideoUploadInit(
            upload_url=KINESCope_ENDPOINT,
            video_key=KINESCope_VIDEO_ID,
            upload_method="post",
        )

    def test_small_filesize_uses_post_upload_method(self) -> None:
        adapter = _adapter()

        def fake_urlopen(req: Any, timeout: float = 0) -> Any:
            return BytesIO(_init_response())

        with patch("services.course_management.video_providers.kinescope_adapter.urlopen", side_effect=fake_urlopen):
            result = adapter.init_lesson_upload(
                course_id=CID,
                lesson_id=LID,
                filename="clip.mp4",
                content_type="video/mp4",
                filesize=TUS_FILESIZE_THRESHOLD_BYTES - 1,
            )

        assert result.upload_method == "post"

    def test_large_filesize_uses_tus_upload_method(self) -> None:
        adapter = _adapter()

        def fake_urlopen(req: Any, timeout: float = 0) -> Any:
            return BytesIO(_init_response())

        with patch("services.course_management.video_providers.kinescope_adapter.urlopen", side_effect=fake_urlopen):
            result = adapter.init_lesson_upload(
                course_id=CID,
                lesson_id=LID,
                filename="long.mp4",
                content_type="video/mp4",
                filesize=TUS_FILESIZE_THRESHOLD_BYTES,
            )

        assert result.upload_method == "tus"

    def test_missing_credentials_raises_bad_request(self) -> None:
        adapter = KinescopeVideoAdapter(api_token="", parent_id="")
        with pytest.raises(BadRequest, match="not configured"):
            adapter.init_lesson_upload(
                course_id=CID,
                lesson_id=LID,
                filename="x.mp4",
                content_type="video/mp4",
            )

    def test_http_error_raises_service_unavailable(self) -> None:
        from urllib.error import HTTPError

        adapter = _adapter()

        def fake_urlopen(req: Any, timeout: float = 0) -> Any:
            raise HTTPError(
                url=req.full_url,
                code=401,
                msg="Unauthorized",
                hdrs=None,
                fp=BytesIO(b""),
            )

        with patch("services.course_management.video_providers.kinescope_adapter.urlopen", side_effect=fake_urlopen):
            with pytest.raises(ServiceUnavailable, match="Failed to initiate"):
                adapter.init_lesson_upload(
                    course_id=CID,
                    lesson_id=LID,
                    filename="x.mp4",
                    content_type="video/mp4",
                )

    def test_invalid_response_raises_service_unavailable(self) -> None:
        adapter = _adapter()

        def fake_urlopen(req: Any, timeout: float = 0) -> Any:
            return BytesIO(b"{}")

        with patch("services.course_management.video_providers.kinescope_adapter.urlopen", side_effect=fake_urlopen):
            with pytest.raises(ServiceUnavailable, match="Failed to initiate"):
                adapter.init_lesson_upload(
                    course_id=CID,
                    lesson_id=LID,
                    filename="x.mp4",
                    content_type="video/mp4",
                )

    def test_delete_videos_calls_kinescope_api(self) -> None:
        adapter = _adapter()
        deleted_urls: list[str] = []

        def fake_urlopen(req: Any, timeout: float = 0) -> Any:
            deleted_urls.append(req.full_url)
            return BytesIO(b"{}")

        with patch("services.course_management.video_providers.kinescope_adapter.urlopen", side_effect=fake_urlopen):
            result = adapter.delete_videos([KINESCope_VIDEO_ID, ""])

        assert result == [KINESCope_VIDEO_ID]
        assert deleted_urls == [f"https://api.kinescope.io/v1/videos/{KINESCope_VIDEO_ID}"]

    def test_delete_videos_without_token_is_no_op(self) -> None:
        adapter = KinescopeVideoAdapter(api_token="", parent_id="parent-folder-id")
        assert adapter.delete_videos([KINESCope_VIDEO_ID]) == []
