from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID

import pytest

import services.course_management.image_storage as image_storage_mod
from services.common.errors import BadRequest
from services.course_management.models import PresignResult

CID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
LID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
VID_FILE = "11111111-1111-4111-8111-111111111111"


@pytest.fixture
def patched_image_storage(monkeypatch: pytest.MonkeyPatch, frozen_uuid: UUID):
    """Construct `CourseImageStorage` with a fully mocked S3 client."""
    mock_s3 = MagicMock()
    mock_s3.generate_presigned_url.return_value = "https://signed.example/put?sig=abc"

    monkeypatch.setattr(image_storage_mod, "_s3_client", lambda: mock_s3)
    monkeypatch.setattr(image_storage_mod, "uuid4", lambda: frozen_uuid)

    storage = image_storage_mod.CourseImageStorage("my-bucket")
    return storage, mock_s3


class TestCourseImageStorageInit:
    def test_empty_bucket_raises(self) -> None:
        with pytest.raises(RuntimeError, match="VIDEO_BUCKET"):
            image_storage_mod.CourseImageStorage("")


class TestPresignThumbnailPut:
    def test_course_thumbnail_key_shape(self, patched_image_storage, frozen_uuid: UUID) -> None:
        storage, _ = patched_image_storage
        r = storage.presign_thumbnail_put(
            course_id=CID, filename="x.jpg", content_type="image/jpeg"
        )
        assert r.videoKey == f"{CID}/thumbnail/{frozen_uuid}.jpg"

    def test_forwards_content_type_to_sdk(self, patched_image_storage) -> None:
        storage, mock_s3 = patched_image_storage

        storage.presign_thumbnail_put(
            course_id=CID, filename="x.png", content_type="image/png"
        )

        mock_s3.generate_presigned_url.assert_called_once()
        kwargs = mock_s3.generate_presigned_url.call_args.kwargs
        assert kwargs["ClientMethod"] == "put_object"
        assert kwargs["Params"]["Bucket"] == "my-bucket"
        assert kwargs["Params"]["ContentType"] == "image/png"
        assert kwargs["ExpiresIn"] == 300

    @pytest.mark.parametrize(
        ("content_type", "expected_ext"),
        [
            ("image/jpeg", "jpg"),
            ("image/jpg", "jpg"),
            ("image/png", "png"),
            ("image/webp", "webp"),
            ("image/gif", "gif"),
        ],
    )
    def test_extension_mapping_for_image_content_types(
        self, monkeypatch: pytest.MonkeyPatch, content_type: str, expected_ext: str
    ) -> None:
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = "https://x"
        monkeypatch.setattr(image_storage_mod, "_s3_client", lambda: mock_s3)
        fixed = UUID("22222222-2222-4222-8222-222222222222")
        monkeypatch.setattr(image_storage_mod, "uuid4", lambda: fixed)
        storage = image_storage_mod.CourseImageStorage("b")

        storage.presign_thumbnail_put(
            course_id=CID, filename="ignored", content_type=content_type
        )
        key = mock_s3.generate_presigned_url.call_args.kwargs["Params"]["Key"]
        assert key == f"{CID}/thumbnail/{fixed}.{expected_ext}"


class TestPresignLessonThumbnailPut:
    def test_lesson_thumbnail_key_shape(self, patched_image_storage, frozen_uuid: UUID) -> None:
        storage, _ = patched_image_storage
        r = storage.presign_lesson_thumbnail_put(
            course_id=CID,
            lesson_id=LID,
            filename="x.png",
            content_type="image/png",
        )
        assert r.videoKey == f"{CID}/lessons/{LID}/thumbnail/{frozen_uuid}.png"

    def test_rejects_slash_in_course_or_lesson_id(self, patched_image_storage) -> None:
        storage, _ = patched_image_storage
        with pytest.raises(BadRequest, match="Invalid course or lesson id"):
            storage.presign_lesson_thumbnail_put(
                course_id="bad/course",
                lesson_id=LID,
                filename="x.png",
                content_type="image/png",
            )


class TestPresignGet:
    def test_accepts_lesson_thumbnail_key(self, patched_image_storage) -> None:
        storage, mock_s3 = patched_image_storage
        k = f"{CID}/lessons/{LID}/thumbnail/33333333-3333-4333-8333-333333333333.webp"
        storage.presign_get(key=k)
        assert mock_s3.generate_presigned_url.call_args.kwargs["Params"]["Key"] == k

    def test_accepts_course_thumbnail_key(self, patched_image_storage) -> None:
        storage, mock_s3 = patched_image_storage
        k = f"{CID}/thumbnail/44444444-4444-4444-8444-444444444444.gif"
        storage.presign_get(key=k)
        assert mock_s3.generate_presigned_url.call_args.kwargs["Params"]["Key"] == k

    def test_rejects_video_keys(self, patched_image_storage) -> None:
        storage, _ = patched_image_storage
        k = f"{CID}/lessons/{LID}/video/{VID_FILE}.mp4"
        with pytest.raises(BadRequest, match="Invalid object key"):
            storage.presign_get(key=k)

    @pytest.mark.parametrize(
        "bad_key",
        [
            "",
            "uploads/abc.jpg",
            f"{CID}/thumbnail/not-a-uuid.jpg",
            f"{CID}//thumbnail/{VID_FILE}.jpg",
        ],
    )
    def test_rejects_invalid_keys(self, patched_image_storage, bad_key: str) -> None:
        storage, _ = patched_image_storage
        with pytest.raises(BadRequest, match="Invalid object key"):
            storage.presign_get(key=bad_key)


class TestDeleteObjects:
    def test_empty_returns_empty(self, patched_image_storage) -> None:
        storage, mock_s3 = patched_image_storage
        assert storage.delete_objects([]) == []
        mock_s3.delete_objects.assert_not_called()

    def test_delegates_batch_delete(self, patched_image_storage) -> None:
        storage, mock_s3 = patched_image_storage
        k = f"{CID}/thumbnail/{VID_FILE}.jpg"
        mock_s3.delete_objects.return_value = {"Deleted": [{"Key": k}]}
        out = storage.delete_objects([k])
        assert out == [k]
        mock_s3.delete_objects.assert_called_once()
