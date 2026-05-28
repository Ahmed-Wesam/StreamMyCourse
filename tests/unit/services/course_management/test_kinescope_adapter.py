"""Unit tests for playback-only KinescopeVideoAdapter in VPC catalog."""

from __future__ import annotations

import pytest

from services.common.errors import ServiceUnavailable
from services.course_management.video_providers.kinescope_adapter import (
    KinescopeVideoAdapter,
    KinescopeVideoMetadata,
    webhook_status_confirmed_by_api,
)
from services.course_management.video_providers.port import KinescopePlayback

CID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
LID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
KINESCope_VIDEO_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"


def _adapter() -> KinescopeVideoAdapter:
    return KinescopeVideoAdapter(
        api_token="test-token",
        parent_id="parent-folder-id",
    )


class TestKinescopePlaybackOnlyAdapter:
    def test_provider_id_and_marks_ready_flag(self) -> None:
        adapter = _adapter()
        assert adapter.provider_id == "kinescope"
        assert adapter.marks_ready_on_upload_complete is False

    def test_resolve_playback_returns_kinescope_playback(self) -> None:
        adapter = _adapter()
        playback = adapter.resolve_playback(video_key=KINESCope_VIDEO_ID)
        assert playback == KinescopePlayback(
            provider="kinescope",
            video_id=KINESCope_VIDEO_ID,
            drm_auth_token="",
        )

    def test_init_lesson_upload_requires_edge(self) -> None:
        adapter = _adapter()
        with pytest.raises(ServiceUnavailable, match="video provider edge"):
            adapter.init_lesson_upload(
                course_id=CID,
                lesson_id=LID,
                filename="intro.mp4",
                content_type="video/mp4",
            )

    def test_delete_videos_requires_edge(self) -> None:
        adapter = _adapter()
        with pytest.raises(ServiceUnavailable, match="video provider edge"):
            adapter.delete_videos([KINESCope_VIDEO_ID])

    def test_delete_videos_empty_list_is_no_op(self) -> None:
        adapter = _adapter()
        assert adapter.delete_videos([]) == []


class TestWebhookStatusConfirmation:
    def test_done_matches_ready_api_statuses(self) -> None:
        assert webhook_status_confirmed_by_api("done", "ready") is True
        assert webhook_status_confirmed_by_api("done", "processing") is False

    def test_error_matches_failed_api_statuses(self) -> None:
        assert webhook_status_confirmed_by_api("error", "failed") is True
        assert webhook_status_confirmed_by_api("aborted", "aborted") is True


class TestKinescopeVideoMetadata:
    def test_dataclass_fields(self) -> None:
        meta = KinescopeVideoMetadata(status="done", duration_seconds=90)
        assert meta.status == "done"
        assert meta.duration_seconds == 90
