"""RS-11 Slice 2: lesson file S3 presign and validation."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID

import pytest

import services.course_management.s3_common as s3_common_mod
import services.course_management.storage as storage_mod
from services.common.errors import BadRequest
from services.course_management.models import LessonFilePresignResult

CID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
LID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
FID = "11111111-1111-4111-8111-111111111111"


@pytest.fixture
def patched_file_storage(monkeypatch: pytest.MonkeyPatch, frozen_uuid: UUID):
    mock_s3 = MagicMock()
    mock_s3.generate_presigned_url.return_value = "https://signed.example/put"
    mock_s3.head_object.return_value = {
        "ContentLength": 100,
        "ContentType": "application/pdf",
    }
    monkeypatch.setattr(storage_mod, "_s3_client", lambda: mock_s3)
    storage = storage_mod.LessonFileStorage("files-bucket")
    return storage, mock_s3


class TestLessonFileS3Common:
    def test_max_bytes_is_100_mib(self) -> None:
        assert s3_common_mod.MAX_LESSON_FILE_BYTES == 104857600

    @pytest.mark.parametrize(
        "file_type,ext,ctype",
        [
            ("pdf", "pdf", "application/pdf"),
            ("csv", "csv", "text/csv"),
            (
                "xlsx",
                "xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            (
                "docx",
                "docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            ("sav", "sav", "application/x-spss-sav"),
        ],
    )
    def test_file_type_maps_to_extension_and_content_type(
        self, file_type: str, ext: str, ctype: str
    ) -> None:
        assert s3_common_mod.extension_for_lesson_file_type(file_type) == ext
        assert s3_common_mod.content_type_for_lesson_file_type(file_type) == ctype

    def test_invalid_file_type_raises(self) -> None:
        with pytest.raises(BadRequest):
            s3_common_mod.extension_for_lesson_file_type("exe")

    def test_lesson_file_key_pattern_accepts_valid_key(self) -> None:
        key = f"{CID}/lessons/{LID}/files/{FID}.pdf"
        assert s3_common_mod.is_valid_lesson_file_object_key(key)

    def test_sanitize_title_strips_unsafe_chars_and_caps_length(self) -> None:
        raw = 'My\r\n"file";name\\' + ("x" * 200)
        out = s3_common_mod.sanitize_download_filename(raw)
        assert "\r" not in out and "\n" not in out
        assert '"' not in out and ";" not in out and "\\" not in out
        assert len(out) == 120


class TestLessonFileStoragePresignPut:
    def test_presign_put_includes_content_type_and_length(
        self, patched_file_storage
    ) -> None:
        storage, mock_s3 = patched_file_storage
        key = f"{CID}/lessons/{LID}/files/{FID}.pdf"
        result = storage.presign_put_file(
            course_id=CID,
            lesson_id=LID,
            file_id=FID,
            file_type="pdf",
            byte_size=4096,
        )
        assert isinstance(result, LessonFilePresignResult)
        assert result.objectKey == key
        assert result.uploadUrl == "https://signed.example/put"
        mock_s3.generate_presigned_url.assert_called_once()
        params = mock_s3.generate_presigned_url.call_args.kwargs["Params"]
        assert params["ContentType"] == "application/pdf"
        assert params["ContentLength"] == 4096


class TestLessonFileStoragePresignGet:
    def test_resource_pdf_uses_inline_disposition(self, patched_file_storage) -> None:
        storage, mock_s3 = patched_file_storage
        key = f"{CID}/lessons/{LID}/files/{FID}.pdf"
        storage.presign_get_file(
            key=key,
            kind="resource",
            title="Week 1 Notes",
            file_type="pdf",
        )
        call = mock_s3.generate_presigned_url.call_args
        assert call.kwargs["ExpiresIn"] == 300
        params = call.kwargs["Params"]
        assert params["ResponseContentDisposition"].startswith("inline;")

    def test_download_kind_uses_attachment(self, patched_file_storage) -> None:
        storage, mock_s3 = patched_file_storage
        key = f"{CID}/lessons/{LID}/files/{FID}.csv"
        storage.presign_get_file(
            key=key,
            kind="download",
            title="data",
            file_type="csv",
        )
        params = mock_s3.generate_presigned_url.call_args.kwargs["Params"]
        assert params["ResponseContentDisposition"].startswith("attachment;")

    def test_resource_non_pdf_uses_attachment(self, patched_file_storage) -> None:
        storage, mock_s3 = patched_file_storage
        key = f"{CID}/lessons/{LID}/files/{FID}.csv"
        storage.presign_get_file(
            key=key,
            kind="resource",
            title="data",
            file_type="csv",
        )
        params = mock_s3.generate_presigned_url.call_args.kwargs["Params"]
        assert params["ResponseContentDisposition"].startswith("attachment;")


class TestLessonFileStorageHead:
    def test_head_object_delegates(self, patched_file_storage) -> None:
        storage, mock_s3 = patched_file_storage
        key = f"{CID}/lessons/{LID}/files/{FID}.pdf"
        meta = storage.head_object(key)
        mock_s3.head_object.assert_called_once_with(Bucket="files-bucket", Key=key)
        assert meta["ContentLength"] == 100
