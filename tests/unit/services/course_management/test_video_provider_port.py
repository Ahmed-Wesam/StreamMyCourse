from __future__ import annotations



from dataclasses import dataclass

from typing import List, Sequence

from unittest.mock import MagicMock

from uuid import UUID



import pytest



from services.course_management.models import PresignResult

from services.course_management.video_providers.port import (

    KinescopePlayback,

    S3Playback,

    VdocipherPlayback,

    VideoProviderPort,

    VideoUploadInit,

)

from services.course_management.video_providers.s3_video_provider import S3VideoProvider

from services.course_management.video_providers.vdocipher_adapter import VdocipherVideoAdapter



CID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

LID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"





@dataclass

class _FakeVideoProvider:

    """Minimal in-memory fake for VideoProviderPort contract tests."""



    upload: VideoUploadInit | None = None

    playback: S3Playback | KinescopePlayback | VdocipherPlayback = S3Playback(

        provider="s3",

        playback_url="https://playback.example/v",

    )

    deleted: List[str] | None = None



    @property

    def provider_id(self) -> str:

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

        _ = course_id, lesson_id, filename, content_type, expires_seconds, filesize

        if self.upload is None:

            raise RuntimeError("upload not configured")

        return self.upload



    def resolve_playback(

        self,

        *,

        video_key: str,

        expires_seconds: int = 3600,

    ) -> S3Playback | KinescopePlayback | VdocipherPlayback:

        _ = video_key, expires_seconds

        return self.playback



    def delete_videos(self, keys: Sequence[str]) -> List[str]:

        self.deleted = list(keys)

        return list(keys)





class TestVideoProviderPortContract:

    def test_fake_satisfies_protocol(self) -> None:

        provider: VideoProviderPort = _FakeVideoProvider(

            upload=VideoUploadInit(

                upload_url="https://upload.example",

                video_key=f"{CID}/lessons/{LID}/video/x.mp4",

            )

        )

        init = provider.init_lesson_upload(

            course_id=CID,

            lesson_id=LID,

            filename="lesson.mp4",

            content_type="video/mp4",

        )

        assert init.upload_url == "https://upload.example"

        assert init.video_key.endswith(".mp4")



        playback = provider.resolve_playback(video_key=init.video_key)

        assert playback == S3Playback(provider="s3", playback_url="https://playback.example/v")



        deleted = provider.delete_videos([init.video_key])

        assert deleted == [init.video_key]





class TestS3VideoProvider:

    def test_delegates_upload_to_underlying_storage(

        self, monkeypatch: pytest.MonkeyPatch, frozen_uuid: UUID

    ) -> None:

        import services.course_management.storage as storage_mod



        mock_s3 = MagicMock()

        mock_s3.generate_presigned_url.return_value = "https://signed.example/put"

        monkeypatch.setattr(storage_mod, "_s3_client", lambda: mock_s3)

        monkeypatch.setattr(storage_mod, "uuid4", lambda: frozen_uuid)



        storage = storage_mod.CourseMediaStorage("my-bucket")

        provider = S3VideoProvider(storage)



        init = provider.init_lesson_upload(

            course_id=CID,

            lesson_id=LID,

            filename="x.mp4",

            content_type="video/mp4",

        )



        assert init == VideoUploadInit(

            upload_url="https://signed.example/put",

            video_key=f"{CID}/lessons/{LID}/video/{frozen_uuid}.mp4",

        )

        assert provider.provider_id == "s3"

        assert provider.marks_ready_on_upload_complete is True



    def test_delegates_playback_and_delete(self, monkeypatch: pytest.MonkeyPatch) -> None:

        import services.course_management.storage as storage_mod



        mock_s3 = MagicMock()

        mock_s3.generate_presigned_url.return_value = "https://signed.example/get"

        mock_s3.delete_objects.return_value = {}

        monkeypatch.setattr(storage_mod, "_s3_client", lambda: mock_s3)



        storage = storage_mod.CourseMediaStorage("my-bucket")

        provider = S3VideoProvider(storage)

        video_key = f"{CID}/lessons/{LID}/video/11111111-1111-4111-8111-111111111111.mp4"



        playback = provider.resolve_playback(video_key=video_key)

        assert playback == S3Playback(provider="s3", playback_url="https://signed.example/get")



        deleted = provider.delete_videos([video_key])

        assert deleted == []

        mock_s3.delete_objects.assert_called_once()





class TestStubAdapters:

    def test_vdocipher_adapter_raises_not_implemented(self) -> None:

        adapter = VdocipherVideoAdapter()

        assert adapter.provider_id == "vdocipher"

        assert adapter.marks_ready_on_upload_complete is False

        with pytest.raises(NotImplementedError):

            adapter.resolve_playback(

                video_key=f"{CID}/lessons/{LID}/video/x.mp4",

            )

