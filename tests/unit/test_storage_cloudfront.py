"""Unit tests for CourseMediaStorage CloudFront delegation."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.common.errors import BadRequest
from services.course_management.storage import CourseMediaStorage


def _video_key() -> str:
    return (
        "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/lessons/"
        "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb/video/"
        "cccccccc-cccc-4ccc-8ccc-cccccccccccc.mp4"
    )


@pytest.fixture
def storage(monkeypatch: pytest.MonkeyPatch) -> CourseMediaStorage:
    import services.course_management.storage as storage_mod

    monkeypatch.setattr(storage_mod, "_s3_client", lambda: MagicMock())
    return CourseMediaStorage("my-video-bucket")


def test_presign_get_cloudfront_delegates_to_signer(storage: CourseMediaStorage) -> None:
    signer = MagicMock()
    signer.sign_url.return_value = "https://cf.example/signed"
    url = storage.presign_get_cloudfront(
        key=_video_key(), expires_seconds=28800, signer=signer
    )
    signer.sign_url.assert_called_once_with(_video_key(), expires_seconds=28800)
    assert url == "https://cf.example/signed"


def test_presign_get_cloudfront_validates_object_key_layout(
    storage: CourseMediaStorage,
) -> None:
    signer = MagicMock()
    with pytest.raises(BadRequest, match="Invalid object key"):
        storage.presign_get_cloudfront(
            key="not-a-valid-layout.mp4", expires_seconds=28800, signer=signer
        )
    signer.sign_url.assert_not_called()
