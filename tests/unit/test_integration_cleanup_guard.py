"""Prod S3 cleanup guard for integration tests (target: Slice 2 integration-prod-safety)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_INTEGRATION_DIR = Path(__file__).resolve().parents[1] / "integration"
if str(_INTEGRATION_DIR) not in sys.path:
    sys.path.insert(0, str(_INTEGRATION_DIR))

from helpers.cleanup import _assert_integration_video_bucket  # noqa: E402

_PROD_BUCKET = "streammycourse-video-prod-abc123-videobucketxyz"
_WRONG_BUCKET = "some-other-bucket-name"


def test_assert_integration_video_bucket_accepts_prod_when_flag_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTEGRATION_ALLOW_PROD_CLEANUP", "1")
    _assert_integration_video_bucket(_PROD_BUCKET)


def test_assert_integration_video_bucket_rejects_prod_when_flag_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("INTEGRATION_ALLOW_PROD_CLEANUP", raising=False)
    with pytest.raises(RuntimeError, match="prod"):
        _assert_integration_video_bucket(_PROD_BUCKET)


def test_assert_integration_video_bucket_rejects_wrong_bucket_even_with_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INTEGRATION_ALLOW_PROD_CLEANUP", "1")
    with pytest.raises(RuntimeError):
        _assert_integration_video_bucket(_WRONG_BUCKET)


def test_assert_integration_video_bucket_rejects_empty_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INTEGRATION_ALLOW_PROD_CLEANUP", "1")
    with pytest.raises(RuntimeError, match="empty"):
        _assert_integration_video_bucket("")
