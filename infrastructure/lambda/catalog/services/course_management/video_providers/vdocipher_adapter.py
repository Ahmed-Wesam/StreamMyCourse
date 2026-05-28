from __future__ import annotations

from typing import List, Literal, Sequence

from services.course_management.video_providers.port import VideoPlayback, VideoUploadInit


class VdocipherVideoAdapter:
    """Stub VdoCipher provider — reserved for future provider swap."""

    @property
    def provider_id(self) -> Literal["vdocipher"]:
        return "vdocipher"

    @property
    def marks_ready_on_upload_complete(self) -> bool:
        return False

    def init_lesson_upload(
        self,
        *,
        course_id: str,
        lesson_id: str,
        filename: str,
        content_type: str,
        expires_seconds: int = 300,
        filesize: int | None = None,
    ) -> VideoUploadInit:
        _ = course_id, lesson_id, filename, content_type, expires_seconds, filesize
        raise NotImplementedError("VdoCipher upload is not implemented yet")

    def resolve_playback(
        self,
        *,
        video_key: str,
        expires_seconds: int = 3600,
    ) -> VideoPlayback:
        _ = video_key, expires_seconds
        raise NotImplementedError("VdoCipher playback is not implemented yet")

    def delete_videos(self, keys: Sequence[str]) -> List[str]:
        _ = keys
        raise NotImplementedError("VdoCipher delete is not implemented yet")
