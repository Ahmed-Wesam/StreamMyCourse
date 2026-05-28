"""Unit tests for media cleanup worker Lambda (SQS -> S3 delete_objects)."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "infrastructure" / "lambda" / "media_cleanup"))

import worker as media_cleanup_worker  # noqa: E402


def test_deploy_media_cleanup_script_zips_worker_and_kinescope_adapter() -> None:
    script = _REPO_ROOT / "scripts" / "deploy-media-cleanup.sh"
    assert script.is_file(), f"missing {script}"
    text = script.read_text(encoding="utf-8")
    assert "kinescope_adapter.py" in text
    assert "_zip_dir_recursive" in text
    assert "_zip_one_file" not in text


def test_worker_imports_kinescope_adapter() -> None:
    from kinescope_adapter import KinescopeDeleteAdapter  # noqa: E402

    assert media_cleanup_worker.KinescopeDeleteAdapter is KinescopeDeleteAdapter


def test_handler_deletes_s3_objects_in_batch(monkeypatch) -> None:
    monkeypatch.setenv("VIDEO_BUCKET", "my-bucket")
    mock_s3 = MagicMock()
    mock_s3.delete_objects.return_value = {"Errors": []}
    monkeypatch.setattr(media_cleanup_worker, "_s3", mock_s3)

    event = {
        "Records": [
            {
                "messageId": "m1",
                "body": json.dumps({"courseId": "c1", "keys": ["a/b/1", "a/b/2"]}),
            }
        ]
    }
    out = media_cleanup_worker.lambda_handler(event, None)
    assert out["batchItemFailures"] == []
    mock_s3.delete_objects.assert_called_once()
    kw = mock_s3.delete_objects.call_args.kwargs
    assert kw["Bucket"] == "my-bucket"
    assert {o["Key"] for o in kw["Delete"]["Objects"]} == {"a/b/1", "a/b/2"}


def test_handler_returns_batch_item_failures_for_partial_failure(monkeypatch) -> None:
    monkeypatch.setenv("VIDEO_BUCKET", "b1")
    mock_s3 = MagicMock()
    mock_s3.delete_objects.return_value = {"Errors": [{"Key": "k", "Code": "AccessDenied"}]}
    monkeypatch.setattr(media_cleanup_worker, "_s3", mock_s3)
    event = {
        "Records": [{"messageId": "mid-9", "body": json.dumps({"courseId": "c", "keys": ["k"]})}]
    }
    out = media_cleanup_worker.lambda_handler(event, None)
    assert out["batchItemFailures"] == [{"itemIdentifier": "mid-9"}]


def test_handler_returns_batch_failures_when_video_bucket_missing(monkeypatch) -> None:
    monkeypatch.delenv("VIDEO_BUCKET", raising=False)
    mock_s3 = MagicMock()
    monkeypatch.setattr(media_cleanup_worker, "_s3", mock_s3)
    event = {
        "Records": [
            {"messageId": "m-a", "body": "{}"},
            {"messageId": "m-b", "body": "{}"},
        ]
    }
    out = media_cleanup_worker.lambda_handler(event, None)
    assert sorted(f["itemIdentifier"] for f in out["batchItemFailures"]) == ["m-a", "m-b"]
    mock_s3.delete_objects.assert_not_called()


def test_handler_skips_delete_when_no_keys(monkeypatch) -> None:
    monkeypatch.setenv("VIDEO_BUCKET", "b1")
    mock_s3 = MagicMock()
    monkeypatch.setattr(media_cleanup_worker, "_s3", mock_s3)
    event = {"Records": [{"messageId": "m2", "body": json.dumps({"courseId": "c", "keys": []})}]}
    out = media_cleanup_worker.lambda_handler(event, None)
    assert out["batchItemFailures"] == []
    mock_s3.delete_objects.assert_not_called()


def test_handler_logs_success_metrics(caplog, monkeypatch) -> None:
    monkeypatch.setenv("VIDEO_BUCKET", "b1")
    mock_s3 = MagicMock()
    mock_s3.delete_objects.return_value = {"Errors": []}
    monkeypatch.setattr(media_cleanup_worker, "_s3", mock_s3)
    event = {
        "Records": [{"messageId": "m3", "body": json.dumps({"courseId": "c9", "keys": ["x/y"]})}]
    }
    with caplog.at_level(logging.INFO):
        media_cleanup_worker.lambda_handler(event, None)
    assert "Media cleanup completed" in caplog.text


def test_handler_deletes_kinescope_video_ids(monkeypatch) -> None:
    monkeypatch.setenv("VIDEO_BUCKET", "my-bucket")
    mock_s3 = MagicMock()
    mock_adapter = MagicMock()
    adapter_cls = MagicMock(return_value=mock_adapter)
    monkeypatch.setattr(media_cleanup_worker, "_s3", mock_s3)
    monkeypatch.setattr(media_cleanup_worker, "KinescopeDeleteAdapter", adapter_cls)

    event = {
        "Records": [
            {
                "messageId": "m-k",
                "body": json.dumps(
                    {
                        "courseId": "c1",
                        "provider": "kinescope",
                        "kinescopeVideoIds": ["vid-1", "vid-2", "vid-1"],
                    }
                ),
            }
        ]
    }
    out = media_cleanup_worker.lambda_handler(event, None)
    assert out["batchItemFailures"] == []
    adapter_cls.assert_called_once()
    assert mock_adapter.delete_video.call_count == 2
    mock_s3.delete_objects.assert_not_called()


def test_handler_legacy_or_s3_provider_still_deletes_s3_keys(monkeypatch) -> None:
    monkeypatch.setenv("VIDEO_BUCKET", "my-bucket")
    mock_s3 = MagicMock()
    mock_s3.delete_objects.return_value = {"Errors": []}
    monkeypatch.setattr(media_cleanup_worker, "_s3", mock_s3)

    event = {
        "Records": [
            {
                "messageId": "m-s3",
                "body": json.dumps(
                    {
                        "courseId": "c1",
                        "provider": "s3",
                        "s3Keys": ["a/b/1", "a/b/2"],
                    }
                ),
            }
        ]
    }
    out = media_cleanup_worker.lambda_handler(event, None)
    assert out["batchItemFailures"] == []
    mock_s3.delete_objects.assert_called_once()
