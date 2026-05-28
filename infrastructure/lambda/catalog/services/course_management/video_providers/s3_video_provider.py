from __future__ import annotations

from typing import TYPE_CHECKING, List, Literal, Sequence

from services.course_management.video_providers.port import S3Playback, VideoPlayback, VideoUploadInit

if TYPE_CHECKING:
    from services.course_management.storage import CourseMediaStorage


class S3VideoProvider:
    """VideoProviderPort adapter backed by S3 presigned upload/playback."""

    def __init__(self, storage: CourseMediaStorage):
        self._storage = storage

    @property
    def provider_id(self) -> Literal["s3"]:
        return "s3"

    @property
    def marks_ready_on_upload_complete(self) -> bool:
        return True

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
        _ = filesize
        result = self._storage.presign_put(
            course_id=course_id,
            lesson_id=lesson_id,
            filename=filename,
            content_type=content_type,
            expires_seconds=expires_seconds,
        )
        return VideoUploadInit(
            upload_url=result.uploadUrl,
            video_key=result.videoKey,
            upload_method="post",
        )

    def resolve_playback(
        self,
        *,
        video_key: str,
        expires_seconds: int = 3600,
    ) -> VideoPlayback:
        url = self._storage.presign_get(key=video_key, expires_seconds=expires_seconds)
        return S3Playback(provider="s3", playback_url=url)

    def delete_videos(self, keys: Sequence[str]) -> List[str]:
        return self._storage.delete_objects(keys)
