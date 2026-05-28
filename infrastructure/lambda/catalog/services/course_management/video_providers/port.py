from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Protocol, Sequence, Union

VideoProviderId = Literal["s3", "kinescope", "vdocipher"]


@dataclass(frozen=True)
class VideoUploadInit:
    upload_url: str
    video_key: str
    upload_method: Literal["post", "tus"] = "post"


@dataclass(frozen=True)
class S3Playback:
    provider: Literal["s3"]
    playback_url: str


@dataclass(frozen=True)
class KinescopePlayback:
    provider: Literal["kinescope"]
    video_id: str
    drm_auth_token: str


@dataclass(frozen=True)
class VdocipherPlayback:
    provider: Literal["vdocipher"]
    otp: str
    playback_info: str


VideoPlayback = Union[S3Playback, KinescopePlayback, VdocipherPlayback]


class VideoProviderPort(Protocol):
    @property
    def provider_id(self) -> VideoProviderId: ...

    @property
    def marks_ready_on_upload_complete(self) -> bool:
        """True when the client can mark the lesson ready after upload (S3)."""
        ...

    def init_lesson_upload(
        self,
        *,
        course_id: str,
        lesson_id: str,
        filename: str,
        content_type: str,
        expires_seconds: int = 300,
        filesize: int | None = None,
    ) -> VideoUploadInit: ...

    def resolve_playback(
        self,
        *,
        video_key: str,
        expires_seconds: int = 3600,
    ) -> VideoPlayback: ...

    def delete_videos(self, keys: Sequence[str]) -> List[str]: ...
