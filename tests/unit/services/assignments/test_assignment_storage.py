"""RS-13: AssignmentFileStorage S3 adapter (fake client, no AWS)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import services.assignments.storage as storage_mod
from services.assignments.ports import ObjectHead


@pytest.fixture
def patched_storage(monkeypatch: pytest.MonkeyPatch):
    mock_s3 = MagicMock()
    mock_s3.generate_presigned_url.return_value = "https://signed.example/url"
    monkeypatch.setattr(storage_mod, "_s3_client", lambda: mock_s3)
    storage = storage_mod.AssignmentFileStorage("video-bucket")
    return storage, mock_s3


def test_presign_put_params_include_content_type_and_length(patched_storage) -> None:
    storage, mock_s3 = patched_storage
    key = "course/assignments/aid/submissions/sid/fid.pdf"
    url = storage.presign_put(key, "application/pdf", 4096)
    assert url == "https://signed.example/url"
    mock_s3.generate_presigned_url.assert_called_once_with(
        ClientMethod="put_object",
        Params={
            "Bucket": "video-bucket",
            "Key": key,
            "ContentType": "application/pdf",
            "ContentLength": 4096,
        },
        ExpiresIn=300,
    )


def test_head_missing_object_returns_none(patched_storage) -> None:
    storage, mock_s3 = patched_storage
    err = Exception("missing")
    err.response = {"Error": {"Code": "404"}}  # type: ignore[attr-defined]
    mock_s3.head_object.side_effect = err
    assert storage.head("course/assignments/aid/missing.pdf") is None


def test_head_returns_content_type_and_length(patched_storage) -> None:
    storage, mock_s3 = patched_storage
    mock_s3.head_object.return_value = {
        "ContentType": "application/pdf",
        "ContentLength": 2048,
    }
    key = "course/assignments/aid/files/fid.pdf"
    result = storage.head(key)
    assert result == ObjectHead(content_type="application/pdf", content_length=2048)
    mock_s3.head_object.assert_called_once_with(Bucket="video-bucket", Key=key)


def test_presign_get_attachment_filename_strips_cr_lf_and_quotes(
    patched_storage,
) -> None:
    storage, mock_s3 = patched_storage
    key = "course/assignments/aid/submissions/sid/fid.pdf"
    storage.presign_get(
        key,
        disposition="attachment",
        download_filename='evil\r\n"name".pdf',
        expires_seconds=300,
    )
    params = mock_s3.generate_presigned_url.call_args.kwargs["Params"]
    disposition = params["ResponseContentDisposition"]
    assert disposition == 'attachment; filename="evilname.pdf"'
    assert "\r" not in disposition and "\n" not in disposition


def test_delete_calls_delete_object_with_the_key(patched_storage) -> None:
    storage, mock_s3 = patched_storage
    key = "course/assignments/aid/files/fid.pdf"
    storage.delete(key)
    mock_s3.delete_object.assert_called_once_with(Bucket="video-bucket", Key=key)
