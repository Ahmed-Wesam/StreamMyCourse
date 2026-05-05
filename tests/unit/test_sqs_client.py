"""Unit tests for media cleanup SQS enqueue helper."""

from __future__ import annotations

import json
from typing import Any, Dict, List
import logging
from unittest.mock import MagicMock, patch

import pytest

from services.common.errors import BadRequest
from services.common.sqs_client import send_media_cleanup_job


class _FakeSQS:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    def send_message(self, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(kwargs)
        return {"MessageId": "mid-1"}


def test_send_media_cleanup_job_formats_payload() -> None:
    fake = _FakeSQS()
    send_media_cleanup_job(
        "https://sqs.eu-west-1.amazonaws.com/123/q",
        "course-uuid-1",
        ["a/b/key1", "a/b/key2"],
        sqs_client=fake,
    )
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["QueueUrl"] == "https://sqs.eu-west-1.amazonaws.com/123/q"
    body = json.loads(call["MessageBody"])
    assert body["courseId"] == "course-uuid-1"
    assert body["keys"] == ["a/b/key1", "a/b/key2"]
    assert "timestamp" in body
    assert isinstance(body["timestamp"], str) and len(body["timestamp"]) > 0


def test_send_media_cleanup_job_requires_queue_url_when_keys_present() -> None:
    fake = _FakeSQS()
    with pytest.raises(BadRequest):
        send_media_cleanup_job("", "c1", ["k"], sqs_client=fake)
    assert fake.calls == []


def test_send_media_cleanup_job_skips_when_no_keys() -> None:
    fake = _FakeSQS()
    send_media_cleanup_job("https://q", "c1", [], sqs_client=fake)
    assert fake.calls == []


def test_send_media_cleanup_job_propagates_client_error() -> None:
    client = MagicMock()
    client.send_message.side_effect = RuntimeError("SQS unavailable")
    with pytest.raises(RuntimeError, match="SQS unavailable"):
        send_media_cleanup_job("https://q", "c1", ["k1"], sqs_client=client)


@patch(
    "services.common.sqs_client._chunk_keys_for_messages",
    return_value=[["k1"], ["k2"]],
)
def test_send_media_cleanup_job_logs_and_propagates_on_second_chunk_failure(
    _mock_chunks: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    client = MagicMock()
    client.send_message.side_effect = [{"MessageId": "a"}, RuntimeError("chunk2fail")]
    long_url = "https://sqs.example.com/queues/" + ("x" * 80)
    with caplog.at_level(logging.ERROR, logger="services.common.sqs_client"):
        with pytest.raises(RuntimeError, match="chunk2fail"):
            send_media_cleanup_job(long_url, "course-z", ["ignored"], sqs_client=client)
    assert client.send_message.call_count == 2
    assert "media_cleanup_sqs_partial_send" in caplog.text
    assert "chunk 2 of 2" in caplog.text
    assert "course-z" in caplog.text
