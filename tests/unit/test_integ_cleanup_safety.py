"""Safety tests for integration test cleanup functions.

These tests verify that empty_entire_bucket() refuses to delete
from non-integ buckets to prevent accidental data loss in dev/prod.
"""

from __future__ import annotations

import pytest

# Import the function under test
import sys
import os

# Add the integration helpers to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "integration"))
from helpers.cleanup import empty_entire_bucket


class TestEmptyEntireBucketSafety:
    """Fail-safe tests: empty_entire_bucket must refuse non-integ buckets."""

    def test_raises_on_dev_bucket(self) -> None:
        """Dev buckets must be rejected to prevent data loss."""
        with pytest.raises(RuntimeError, match="REFUSING.*dev"):
            empty_entire_bucket("streammycourse-video-dev-videobucket-abc123", region="eu-west-1")

    def test_raises_on_prod_bucket(self) -> None:
        """Prod buckets must be rejected to prevent data loss."""
        with pytest.raises(RuntimeError, match="REFUSING.*prod"):
            empty_entire_bucket("streammycourse-video-prod-videobucket-xyz789", region="eu-west-1")

    def test_raises_on_unknown_bucket_pattern(self) -> None:
        """Buckets not matching integ pattern must be rejected."""
        with pytest.raises(RuntimeError, match="REFUSING.*integ"):
            empty_entire_bucket("some-random-bucket-name", region="eu-west-1")

    def test_raises_on_dev_in_name(self) -> None:
        """Buckets with '-dev-' anywhere in name must be rejected."""
        with pytest.raises(RuntimeError, match="REFUSING.*dev"):
            empty_entire_bucket("streammycourse-video-integ-dev-test", region="eu-west-1")

    def test_raises_on_prod_in_name(self) -> None:
        """Buckets with '-prod-' anywhere in name must be rejected."""
        with pytest.raises(RuntimeError, match="REFUSING.*prod"):
            empty_entire_bucket("streammycourse-video-integ-prod-test", region="eu-west-1")

    def test_returns_empty_list_for_none_bucket(self) -> None:
        """None/empty bucket should return empty list without error."""
        result = empty_entire_bucket("", region="eu-west-1")
        assert result == []

    def test_integ_bucket_pattern_allowed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Proper integ bucket pattern should pass the safety check.

        Note: This test only verifies the safety check passes, not the actual
        S3 deletion (which would require AWS credentials and a real bucket).
        """
        # Mock S3 client to avoid needing real AWS credentials
        import unittest.mock as mock

        mock_s3 = mock.MagicMock()
        mock_s3.list_objects_v2.return_value = {"Contents": [], "IsTruncated": False}

        with mock.patch("boto3.client", return_value=mock_s3):
            # This should NOT raise a RuntimeError about refusing the bucket
            result = empty_entire_bucket(
                "streammycourse-video-integ-videobucket-g0atv7zs5w4k",
                region="eu-west-1"
            )

        # Function should complete successfully with empty result
        assert result == []
