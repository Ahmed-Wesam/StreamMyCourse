"""Safety tests for integration test cleanup functions.

These tests verify that empty_entire_bucket() only targets the dev video-bucket
pattern and refuses production and unknown names.
"""

from __future__ import annotations

import os
import sys

import httpx
import pytest

# Add the integration helpers to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "integration"))

from helpers.cleanup import (
    delete_prefixed_teacher_courses_via_http,
    empty_entire_bucket,
    run_safety_net,
)


class TestEmptyEntireBucketSafety:
    """Fail-safe tests: empty_entire_bucket must refuse prod and unknown buckets."""

    def test_allows_dev_videobucket_pattern(self) -> None:
        """Dev video stack buckets are allowed (session-end safety net targets dev in CI)."""
        import unittest.mock as mock

        mock_s3 = mock.MagicMock()
        mock_s3.list_objects_v2.return_value = {"Contents": [], "IsTruncated": False}

        with mock.patch("boto3.client", return_value=mock_s3):
            result = empty_entire_bucket(
                "streammycourse-video-dev-videobucket-abc123",
                region="eu-west-1",
            )
        assert result == []

    def test_raises_on_prod_bucket(self) -> None:
        """Prod buckets must be rejected to prevent data loss."""
        with pytest.raises(RuntimeError, match="REFUSING.*prod"):
            empty_entire_bucket("streammycourse-video-prod-videobucket-xyz789", region="eu-west-1")

    def test_raises_on_unknown_bucket_pattern(self) -> None:
        """Buckets not matching the dev video-bucket pattern must be rejected."""
        with pytest.raises(RuntimeError, match="REFUSING"):
            empty_entire_bucket("some-random-bucket-name", region="eu-west-1")

    def test_raises_on_ambiguous_name_with_dev_substring(self) -> None:
        """Names containing 'dev' but not the dev video-bucket pattern must be rejected."""
        with pytest.raises(RuntimeError, match="REFUSING"):
            empty_entire_bucket("streammycourse-video-staging-dev-test", region="eu-west-1")

    def test_raises_on_prod_in_name(self) -> None:
        """Buckets with '-prod-' anywhere in name must be rejected."""
        with pytest.raises(RuntimeError, match="REFUSING.*prod"):
            empty_entire_bucket("streammycourse-video-staging-prod-test", region="eu-west-1")

    def test_returns_empty_list_for_none_bucket(self) -> None:
        """None/empty bucket should return empty list without error."""
        result = empty_entire_bucket("", region="eu-west-1")
        assert result == []

    def test_raises_on_non_dev_named_video_bucket(self) -> None:
        """Only the dev integration pattern is accepted; other env-style names are refused."""
        with pytest.raises(RuntimeError, match="REFUSING"):
            empty_entire_bucket(
                "streammycourse-video-legacyenv-videobucket-g0atv7zs5w4k",
                region="eu-west-1",
            )


class TestApiCourseCleanupSafetyNet:
    """HTTP safety-net: list instructor courses and delete test-prefixed titles."""

    def test_deletes_matching_courses_via_http(self) -> None:
        import unittest.mock as mock

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET" and str(request.url.path).rstrip("/").endswith("courses/mine"):
                return httpx.Response(
                    200,
                    json=[
                        {"id": "c-keep", "title": "Production title"},
                        {"id": "c-wipe", "title": "integration-test-leftover"},
                    ],
                )
            if request.method == "DELETE" and "/courses/c-wipe" in str(request.url.path):
                return httpx.Response(200, json={"id": "c-wipe", "deleted": True})
            return httpx.Response(404, text="unexpected")

        transport = httpx.MockTransport(handler)
        RealHttpxClient = httpx.Client

        def client_factory(**kwargs: object) -> httpx.Client:
            return RealHttpxClient(transport=transport, **kwargs)

        with mock.patch("helpers.cleanup.httpx.Client", side_effect=client_factory):
            deleted = delete_prefixed_teacher_courses_via_http(
                api_base_url="https://api.example/dev",
                auth_token="tok",
                title_prefix="integration-test-",
            )

        assert deleted == ["c-wipe"]

    def test_run_safety_net_calls_api_and_s3(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import unittest.mock as mock

        monkeypatch.setenv("INTEGRATION_API_BASE_URL", "https://api.example/dev")
        monkeypatch.setenv("INTEGRATION_COGNITO_JWT", "jwt")

        with mock.patch(
            "helpers.cleanup.delete_prefixed_teacher_courses_via_http",
            return_value=["a1"],
        ) as api_fn:
            with mock.patch("helpers.cleanup.empty_entire_bucket", return_value=["k1"]) as s3_fn:
                report = run_safety_net(
                    bucket="streammycourse-video-dev-videobucket-abc123",
                    region="eu-west-1",
                    title_prefix="integration-test-",
                )

        api_fn.assert_called_once()
        s3_fn.assert_called_once()
        assert report.courses_removed_via_api == ["a1"]
        assert report.leftover_objects == ["k1"]
