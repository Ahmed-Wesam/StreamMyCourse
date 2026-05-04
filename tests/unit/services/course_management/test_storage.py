from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID

import pytest

import services.course_management.storage as storage_mod
from services.common.errors import BadRequest
from services.course_management.models import PresignResult

CID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
LID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
VID_FILE = "11111111-1111-4111-8111-111111111111"


@pytest.fixture
def patched_storage(monkeypatch: pytest.MonkeyPatch, frozen_uuid: UUID):
    """Construct `CourseMediaStorage` with a fully mocked S3 client."""
    mock_s3 = MagicMock()
    mock_s3.generate_presigned_url.return_value = "https://signed.example/put?sig=abc"

    # Skip the real boto3 client builder entirely.
    monkeypatch.setattr(storage_mod, "_s3_client", lambda: mock_s3)
    monkeypatch.setattr(storage_mod, "uuid4", lambda: frozen_uuid)

    storage = storage_mod.CourseMediaStorage("my-bucket")
    return storage, mock_s3


class TestCourseMediaStorageInit:
    def test_empty_bucket_raises(self) -> None:
        with pytest.raises(RuntimeError, match="VIDEO_BUCKET"):
            storage_mod.CourseMediaStorage("")


class TestS3ClientFactory:
    def test_raises_when_boto3_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(storage_mod, "boto3", None)
        monkeypatch.setattr(storage_mod, "Config", None)
        with pytest.raises(RuntimeError, match="boto3 is not available"):
            storage_mod._s3_client()

    def test_uses_env_region_and_sigv4_config(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Replace boto3 + Config with mocks so we can inspect what the factory
        # passes in without hitting the real AWS SDK.
        mock_boto3 = MagicMock()
        mock_config_cls = MagicMock()
        monkeypatch.setattr(storage_mod, "boto3", mock_boto3)
        monkeypatch.setattr(storage_mod, "Config", mock_config_cls)
        monkeypatch.setenv("AWS_REGION", "us-west-2")

        storage_mod._s3_client()

        mock_config_cls.assert_called_once()
        cfg_kwargs = mock_config_cls.call_args.kwargs
        assert cfg_kwargs["signature_version"] == "s3v4"
        assert cfg_kwargs["s3"] == {"addressing_style": "virtual"}
        assert cfg_kwargs["connect_timeout"] == 5
        assert cfg_kwargs["read_timeout"] == 15

        client_kwargs = mock_boto3.client.call_args.kwargs
        assert mock_boto3.client.call_args.args[0] == "s3"
        assert client_kwargs["region_name"] == "us-west-2"
        assert client_kwargs["endpoint_url"] == "https://s3.us-west-2.amazonaws.com"

    def test_falls_back_to_aws_default_region(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_boto3 = MagicMock()
        monkeypatch.setattr(storage_mod, "boto3", mock_boto3)
        monkeypatch.setattr(storage_mod, "Config", MagicMock())
        monkeypatch.delenv("AWS_REGION", raising=False)
        monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-south-1")

        storage_mod._s3_client()

        client_kwargs = mock_boto3.client.call_args.kwargs
        assert client_kwargs["region_name"] == "ap-south-1"

    def test_falls_back_to_eu_west_1_when_no_env_region(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_boto3 = MagicMock()
        monkeypatch.setattr(storage_mod, "boto3", mock_boto3)
        monkeypatch.setattr(storage_mod, "Config", MagicMock())
        monkeypatch.delenv("AWS_REGION", raising=False)
        monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)

        storage_mod._s3_client()

        client_kwargs = mock_boto3.client.call_args.kwargs
        assert client_kwargs["region_name"] == "eu-west-1"


class TestPresignPut:
    def test_builds_video_key_under_course_lesson_video(
        self, patched_storage, frozen_uuid: UUID
    ) -> None:
        storage, mock_s3 = patched_storage

        result = storage.presign_put(
            course_id=CID,
            lesson_id=LID,
            filename="lesson-1.mp4",
            content_type="video/mp4",
        )

        assert isinstance(result, PresignResult)
        assert result.videoKey == f"{CID}/lessons/{LID}/video/{frozen_uuid}.mp4"
        assert result.uploadUrl == "https://signed.example/put?sig=abc"

    def test_forwards_content_type_to_sdk(self, patched_storage) -> None:
        storage, mock_s3 = patched_storage

        storage.presign_put(
            course_id=CID,
            lesson_id=LID,
            filename="x.mov",
            content_type="video/quicktime",
        )

        mock_s3.generate_presigned_url.assert_called_once()
        kwargs = mock_s3.generate_presigned_url.call_args.kwargs
        assert kwargs["ClientMethod"] == "put_object"
        assert kwargs["Params"]["Bucket"] == "my-bucket"
        assert kwargs["Params"]["ContentType"] == "video/quicktime"
        assert kwargs["ExpiresIn"] == 300

    def test_explicit_expiry_overrides_default(self, patched_storage) -> None:
        storage, mock_s3 = patched_storage

        storage.presign_put(
            course_id=CID,
            lesson_id=LID,
            filename="x.mp4",
            content_type="video/mp4",
            expires_seconds=60,
        )

        kwargs = mock_s3.generate_presigned_url.call_args.kwargs
        assert kwargs["ExpiresIn"] == 60

    @pytest.mark.parametrize(
        ("content_type", "expected_ext"),
        [
            ("video/mp4", "mp4"),
            ("video/webm", "webm"),
            ("video/quicktime", "mov"),
            ("video/x-msvideo", "avi"),
            ("image/jpeg", "jpg"),
            ("image/jpg", "jpg"),
            ("image/png", "png"),
            ("image/webp", "webp"),
            ("image/gif", "gif"),
        ],
    )
    def test_extension_mapping_for_presign_put_and_thumbnails(
        self, monkeypatch: pytest.MonkeyPatch, content_type: str, expected_ext: str
    ) -> None:
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = "https://x"
        monkeypatch.setattr(storage_mod, "_s3_client", lambda: mock_s3)
        fixed = UUID("22222222-2222-4222-8222-222222222222")
        monkeypatch.setattr(storage_mod, "uuid4", lambda: fixed)
        storage = storage_mod.CourseMediaStorage("b")

        if content_type.startswith("video/"):
            storage.presign_put(
                course_id=CID,
                lesson_id=LID,
                filename="ignored",
                content_type=content_type,
            )
            key = mock_s3.generate_presigned_url.call_args.kwargs["Params"]["Key"]
            assert key.endswith(f".{expected_ext}")
            assert f"/video/{fixed}.{expected_ext}" in key
        elif content_type.startswith("image/"):
            storage.presign_thumbnail_put(
                course_id=CID, filename="ignored", content_type=content_type
            )
            key = mock_s3.generate_presigned_url.call_args.kwargs["Params"]["Key"]
            assert key == f"{CID}/thumbnail/{fixed}.{expected_ext}"

    def test_presign_put_rejects_slash_in_course_or_lesson_id(self, patched_storage) -> None:
        storage, _ = patched_storage
        with pytest.raises(BadRequest, match="Invalid course or lesson id"):
            storage.presign_put(
                course_id="bad/course",
                lesson_id=LID,
                filename="x.mp4",
                content_type="video/mp4",
            )


class TestPresignThumbnailPut:
    def test_course_thumbnail_key_shape(self, patched_storage, frozen_uuid: UUID) -> None:
        storage, _ = patched_storage
        r = storage.presign_thumbnail_put(
            course_id=CID, filename="x.jpg", content_type="image/jpeg"
        )
        assert r.videoKey == f"{CID}/thumbnail/{frozen_uuid}.jpg"


class TestPresignLessonThumbnailPut:
    def test_lesson_thumbnail_key_shape(self, patched_storage, frozen_uuid: UUID) -> None:
        storage, _ = patched_storage
        r = storage.presign_lesson_thumbnail_put(
            course_id=CID,
            lesson_id=LID,
            filename="x.png",
            content_type="image/png",
        )
        assert r.videoKey == f"{CID}/lessons/{LID}/thumbnail/{frozen_uuid}.png"


class TestPresignGet:
    def test_accepts_lesson_video_key(self, patched_storage) -> None:
        storage, mock_s3 = patched_storage
        mock_s3.generate_presigned_url.return_value = "https://signed.example/get?sig=def"
        k = f"{CID}/lessons/{LID}/video/{VID_FILE}.mp4"
        url = storage.presign_get(key=k)
        assert url == "https://signed.example/get?sig=def"
        kwargs = mock_s3.generate_presigned_url.call_args.kwargs
        assert kwargs["ClientMethod"] == "get_object"
        assert kwargs["Params"] == {"Bucket": "my-bucket", "Key": k}

    def test_accepts_lesson_thumbnail_key(self, patched_storage) -> None:
        storage, mock_s3 = patched_storage
        k = f"{CID}/lessons/{LID}/thumbnail/33333333-3333-4333-8333-333333333333.webp"
        storage.presign_get(key=k)
        assert mock_s3.generate_presigned_url.call_args.kwargs["Params"]["Key"] == k

    def test_accepts_course_thumbnail_key(self, patched_storage) -> None:
        storage, mock_s3 = patched_storage
        k = f"{CID}/thumbnail/44444444-4444-4444-8444-444444444444.gif"
        storage.presign_get(key=k)
        assert mock_s3.generate_presigned_url.call_args.kwargs["Params"]["Key"] == k

    def test_explicit_expiry_overrides_default(self, patched_storage) -> None:
        storage, mock_s3 = patched_storage
        k = f"{CID}/lessons/{LID}/video/{VID_FILE}.webm"
        storage.presign_get(key=k, expires_seconds=120)
        assert mock_s3.generate_presigned_url.call_args.kwargs["ExpiresIn"] == 120

    @pytest.mark.parametrize(
        "bad_key",
        [
            "",
            "uploads/abc.mp4",
            f"{CID}/lessons/{LID}/video/{VID_FILE}.exe",
            f"{CID}/lessons/{LID}/video/not-a-uuid.mp4",
            f"{CID}/lessons/{LID}/video/../{VID_FILE}.mp4",
            f"{CID}//lessons/{LID}/video/{VID_FILE}.mp4",
            f"../{CID}/lessons/{LID}/video/{VID_FILE}.mp4",
        ],
    )
    def test_rejects_invalid_keys(self, patched_storage, bad_key: str) -> None:
        storage, _ = patched_storage
        with pytest.raises(BadRequest, match="Invalid object key"):
            storage.presign_get(key=bad_key)


class TestDeleteObject:
    def test_blank_noops(self, patched_storage) -> None:
        storage, mock_s3 = patched_storage
        storage.delete_object("")
        storage.delete_object("   ")
        mock_s3.delete_objects.assert_not_called()

    def test_delegates_to_delete_objects(self, patched_storage) -> None:
        storage, mock_s3 = patched_storage
        mock_s3.delete_objects.return_value = {}
        k = f"{CID}/lessons/{LID}/video/{VID_FILE}.mp4"
        storage.delete_object(k)
        mock_s3.delete_objects.assert_called_once()
        assert mock_s3.delete_objects.call_args.kwargs["Delete"]["Objects"] == [{"Key": k}]


class TestDeleteObjects:
    def test_empty_returns_empty(self, patched_storage) -> None:
        storage, mock_s3 = patched_storage
        assert storage.delete_objects([]) == []
        mock_s3.delete_objects.assert_not_called()

    def test_skips_blank_and_dedupes(self, patched_storage) -> None:
        storage, mock_s3 = patched_storage
        k = f"{CID}/lessons/{LID}/video/{VID_FILE}.mp4"
        mock_s3.delete_objects.return_value = {"Deleted": [{"Key": k}]}
        out = storage.delete_objects([k, "  ", k])
        assert out == [k]
        mock_s3.delete_objects.assert_called_once()
        kwargs = mock_s3.delete_objects.call_args.kwargs
        assert kwargs["Bucket"] == "my-bucket"
        assert kwargs["Delete"]["Objects"] == [{"Key": k}]

    def test_batches_over_1000_keys(self, monkeypatch: pytest.MonkeyPatch, patched_storage) -> None:
        storage, mock_s3 = patched_storage
        monkeypatch.setattr(storage_mod, "_S3_DELETE_BATCH", 2)
        keys = [
            f"{CID}/lessons/{LID}/video/11111111-1111-4111-8111-{i:012d}.mp4" for i in range(5)
        ]
        mock_s3.delete_objects.return_value = {}
        storage.delete_objects(keys)
        assert mock_s3.delete_objects.call_count == 3
