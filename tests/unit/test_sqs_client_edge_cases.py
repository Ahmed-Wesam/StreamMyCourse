"""Unit tests for SQS client edge cases and error paths.

Tests boto3 client instantiation and chunking edge cases.
"""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from botocore.exceptions import ClientError

from services.common.errors import BadRequest
from services.common.sqs_client import (
    _chunk_keys_for_messages,
    _send_one,
    send_media_cleanup_job,
)


class TestChunkKeysForMessagesEdgeCases:
    """Tests for _chunk_keys_for_messages boundary conditions."""

    def test_single_key_too_large_raises(self) -> None:
        """A single key that's too large should raise BadRequest."""
        huge_key = "a" * 300 * 1024  # 300KB key
        with pytest.raises(BadRequest) as exc:
            list(_chunk_keys_for_messages("course-1", [huge_key], "2024-01-01", 240 * 1024))
        assert "too large" in exc.value.message.lower()

    def test_empty_keys_returns_empty(self) -> None:
        """Empty keys list should return empty chunks."""
        result = list(_chunk_keys_for_messages("c1", [], "ts", 1024))
        assert result == []

    def test_keys_at_exact_boundary(self) -> None:
        """Keys that exactly fit at boundary should be handled."""
        # Create keys that will exactly fit
        keys = ["key-1", "key-2", "key-3"]
        result = list(_chunk_keys_for_messages("c1", keys, "2024-01-01", 10 * 1024))
        assert len(result) >= 1
        # All keys should be in chunks
        all_keys = [k for chunk in result for k in chunk]
        assert all_keys == keys

    def test_many_small_keys_chunked_correctly(self) -> None:
        """Many small keys should be efficiently chunked."""
        keys = [f"key-{i}" for i in range(100)]
        result = list(_chunk_keys_for_messages("c1", keys, "2024-01-01", 1024))
        # All keys should be present
        all_keys = [k for chunk in result for k in chunk]
        assert len(all_keys) == 100
        assert all_keys == keys


class TestSendMediaCleanupJobBoto3Path:
    """Tests for boto3 client instantiation path."""

    def test_boto3_client_created_when_none_provided(self) -> None:
        """When sqs_client is None, boto3.client should be called."""
        mock_client = MagicMock()
        mock_client.send_message.return_value = {"MessageId": "msg-1"}

        with patch("boto3.client", return_value=mock_client) as mock_boto:
            send_media_cleanup_job(
                "https://sqs.us-east-1.amazonaws.com/123/q",
                "course-1",
                ["key1", "key2"],
            )

        mock_boto.assert_called_once_with("sqs")
        assert mock_client.send_message.call_count == 1

    def test_boto3_client_error_propagated(self) -> None:
        """Boto3 ClientError should be propagated with logging."""
        error = ClientError(
            {"Error": {"Code": "AWS.SimpleQueueService.NonExistentQueue", "Message": "Queue does not exist"}},
            "SendMessage",
        )

        mock_client = MagicMock()
        mock_client.send_message.side_effect = error

        with pytest.raises(ClientError) as exc:
            send_media_cleanup_job(
                "https://sqs.us-east-1.amazonaws.com/123/q",
                "course-1",
                ["key1"],
                sqs_client=mock_client,
            )

        assert "NonExistentQueue" in str(exc.value)

    def test_boto3_throttling_error_propagated(self) -> None:
        """Boto3 throttling error should be propagated."""
        error = ClientError(
            {"Error": {"Code": "Throttling", "Message": "Rate exceeded"}},
            "SendMessage",
        )

        mock_client = MagicMock()
        mock_client.send_message.side_effect = error

        with pytest.raises(ClientError) as exc:
            send_media_cleanup_job(
                "https://sqs.us-east-1.amazonaws.com/123/q",
                "course-1",
                ["key1"],
                sqs_client=mock_client,
            )

        assert "Throttling" in str(exc.value)


class TestSendOne:
    """Tests for _send_one helper."""

    def test_send_one_formats_call_correctly(self) -> None:
        """_send_one should format SQS call with correct parameters."""
        mock_client = MagicMock()

        _send_one(mock_client, "https://q", '{"test": "body"}')

        mock_client.send_message.assert_called_once_with(
            QueueUrl="https://q",
            MessageBody='{"test": "body"}',
        )


class TestSendMediaCleanupJobPartialFailure:
    """Tests for partial failure handling in multi-chunk scenarios."""

    @patch("services.common.sqs_client._chunk_keys_for_messages")
    def test_partial_failure_in_second_chunk_logged(
        self, mock_chunker, caplog
    ) -> None:
        """Failure on chunk 2 of 2 should log partial send details."""
        import logging

        mock_chunker.return_value = [["key1"], ["key2"]]

        mock_client = MagicMock()
        mock_client.send_message.side_effect = [
            {"MessageId": "msg-1"},
            RuntimeError("chunk 2 failed"),
        ]

        with caplog.at_level(logging.ERROR, logger="services.common.sqs_client"):
            with pytest.raises(RuntimeError, match="chunk 2 failed"):
                send_media_cleanup_job(
                    "https://sqs.us-east-1.amazonaws.com/123/queue-name",
                    "course-xyz",
                    ["ignored"],  # chunker mock overrides
                    sqs_client=mock_client,
                )

        assert mock_client.send_message.call_count == 2
        assert "media_cleanup_sqs_partial_send" in caplog.text
        assert "chunk 2 of 2" in caplog.text
        assert "course-xyz" in caplog.text
