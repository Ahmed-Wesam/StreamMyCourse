"""Safety tests for integration test cleanup functions.

These tests verify that destructive S3 helpers only target the dev video-bucket
pattern and refuse production and unknown names, and that the session safety net
scopes S3 deletes to test course prefixes.
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

    def test_allows_devvideo_stack_bucket(self) -> None:
        """StreamMyCourse-DevVideo-dev physical names are allowed."""
        import unittest.mock as mock

        mock_s3 = mock.MagicMock()
        mock_s3.list_objects_v2.return_value = {"Contents": [], "IsTruncated": False}

        with mock.patch("boto3.client", return_value=mock_s3):
            result = empty_entire_bucket(
                "streammycourse-devvideo-dev-devvideobucket-0ialoqbjgwor",
                region="eu-west-1",
            )
        assert result == []

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
                        {
                            "id": "aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee",
                            "title": "Production title",
                        },
                        {
                            "id": "11111111-2222-4333-8444-555555555555",
                            "title": "integration-test-leftover",
                        },
                    ],
                )
            if request.method == "DELETE" and "/courses/11111111-2222-4333-8444-555555555555" in str(
                request.url.path
            ):
                return httpx.Response(
                    200, json={"id": "11111111-2222-4333-8444-555555555555", "deleted": True}
                )
            return httpx.Response(404, text="unexpected")

        transport = httpx.MockTransport(handler)
        RealHttpxClient = httpx.Client

        def client_factory(**kwargs: object) -> httpx.Client:
            return RealHttpxClient(transport=transport, **kwargs)

        with mock.patch("helpers.cleanup.httpx.Client", side_effect=client_factory):
            deleted, matched = delete_prefixed_teacher_courses_via_http(
                api_base_url="https://api.example/dev",
                auth_token="tok",
                title_prefix="integration-test-",
            )

        assert deleted == ["11111111-2222-4333-8444-555555555555"]
        assert matched == ["11111111-2222-4333-8444-555555555555"]

    def test_run_safety_net_calls_api_and_s3(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import unittest.mock as mock

        monkeypatch.setenv("INTEGRATION_API_BASE_URL", "https://api.example/dev")
        monkeypatch.setenv("INTEGRATION_COGNITO_JWT", "jwt")

        uid = "aaaaaaaa-bbbb-4ccc-dddd-000000000001"
        with mock.patch(
            "helpers.cleanup.delete_prefixed_teacher_courses_via_http",
            return_value=(["a1"], [uid]),
        ) as api_fn:
            with mock.patch(
                "helpers.cleanup.delete_orphan_media_for_course_prefixes",
                return_value=["k1"],
            ) as s3_fn:
                report = run_safety_net(
                    bucket="streammycourse-video-dev-videobucket-abc123",
                    region="eu-west-1",
                    title_prefix="integration-test-",
                )

        api_fn.assert_called_once()
        s3_fn.assert_called_once_with(
            "streammycourse-video-dev-videobucket-abc123",
            region="eu-west-1",
            course_ids=[uid],
        )
        assert report.courses_removed_via_api == ["a1"]
        assert report.leftover_objects == ["k1"]


class TestPrefixedCourseCleanupClearsPurchases:
    """HTTP safety-net must clear purchase rows blocking DELETE /courses/{id}."""

    _TEST_COURSE_ID = "11111111-2222-4333-8444-555555555555"
    _OTHER_TEST_COURSE_ID = "22222222-3333-4444-8555-666666666666"
    _PROD_COURSE_ID = "aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee"

    def test_delete_succeeds_after_clearer_runs_on_409(self) -> None:
        import unittest.mock as mock

        clearer_calls: list[str] = []
        purchase_cleared: dict[str, bool] = {self._TEST_COURSE_ID: False}

        def fake_clearer(course_id: str) -> None:
            clearer_calls.append(course_id)
            purchase_cleared[course_id] = True

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET" and str(request.url.path).rstrip("/").endswith(
                "courses/mine"
            ):
                return httpx.Response(
                    200,
                    json=[
                        {
                            "id": self._PROD_COURSE_ID,
                            "title": "Research Methodology",
                        },
                        {
                            "id": self._TEST_COURSE_ID,
                            "title": "integration-test-leftover",
                        },
                    ],
                )
            if request.method == "DELETE" and self._PROD_COURSE_ID in str(request.url.path):
                pytest.fail("DELETE must not run for non-test-prefixed courses")
            if request.method == "DELETE" and self._TEST_COURSE_ID in str(request.url.path):
                if purchase_cleared.get(self._TEST_COURSE_ID):
                    return httpx.Response(
                        200,
                        json={"id": self._TEST_COURSE_ID, "deleted": True},
                    )
                return httpx.Response(409, json={"error": "purchase_exists"})
            return httpx.Response(404, text="unexpected")

        transport = httpx.MockTransport(handler)
        RealHttpxClient = httpx.Client

        def client_factory(**kwargs: object) -> httpx.Client:
            return RealHttpxClient(transport=transport, **kwargs)

        with mock.patch("helpers.cleanup.httpx.Client", side_effect=client_factory):
            deleted, matched = delete_prefixed_teacher_courses_via_http(
                api_base_url="https://api.example/dev",
                auth_token="tok",
                title_prefix="integration-test-",
                clear_blocking_purchases=fake_clearer,
            )

        assert matched == [self._TEST_COURSE_ID]
        assert deleted == [self._TEST_COURSE_ID]
        assert clearer_calls == [self._TEST_COURSE_ID]

    def test_clearer_error_on_first_course_still_deletes_second(self) -> None:
        import unittest.mock as mock

        def fake_clearer(course_id: str) -> None:
            if course_id == self._TEST_COURSE_ID:
                raise RuntimeError("dsql unavailable")

        delete_attempts: dict[str, int] = {
            self._TEST_COURSE_ID: 0,
            self._OTHER_TEST_COURSE_ID: 0,
        }

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET" and str(request.url.path).rstrip("/").endswith(
                "courses/mine"
            ):
                return httpx.Response(
                    200,
                    json=[
                        {
                            "id": self._PROD_COURSE_ID,
                            "title": "Research Methodology",
                        },
                        {
                            "id": self._TEST_COURSE_ID,
                            "title": "integration-test-one",
                        },
                        {
                            "id": self._OTHER_TEST_COURSE_ID,
                            "title": "integration-test-two",
                        },
                    ],
                )
            if request.method == "DELETE" and self._PROD_COURSE_ID in str(request.url.path):
                pytest.fail("DELETE must not run for non-test-prefixed courses")
            for cid in (self._TEST_COURSE_ID, self._OTHER_TEST_COURSE_ID):
                if request.method == "DELETE" and cid in str(request.url.path):
                    delete_attempts[cid] += 1
                    if cid == self._TEST_COURSE_ID:
                        return httpx.Response(409, json={"error": "purchase_exists"})
                    return httpx.Response(
                        200, json={"id": cid, "deleted": True}
                    )
            return httpx.Response(404, text="unexpected")

        transport = httpx.MockTransport(handler)
        RealHttpxClient = httpx.Client

        def client_factory(**kwargs: object) -> httpx.Client:
            return RealHttpxClient(transport=transport, **kwargs)

        with mock.patch("helpers.cleanup.httpx.Client", side_effect=client_factory):
            deleted, matched = delete_prefixed_teacher_courses_via_http(
                api_base_url="https://api.example/dev",
                auth_token="tok",
                title_prefix="integration-test-",
                clear_blocking_purchases=fake_clearer,
            )

        assert matched == [self._TEST_COURSE_ID, self._OTHER_TEST_COURSE_ID]
        assert deleted == [self._OTHER_TEST_COURSE_ID]
        assert delete_attempts[self._TEST_COURSE_ID] >= 1
        assert delete_attempts[self._OTHER_TEST_COURSE_ID] >= 1

    def test_conftest_wires_delete_purchases_for_course_id(self) -> None:
        conftest_path = os.path.join(
            os.path.dirname(__file__), "..", "integration", "conftest.py"
        )
        with open(conftest_path, encoding="utf-8") as f:
            source = f.read()

        assert "delete_purchases_for_course_id" in source

        for marker in (
            "def course_factory(",
            "def alt_course_factory(",
            "def _run_cleanup_for_token(",
        ):
            start = source.index(marker)
            next_def = source.find("\ndef ", start + 1)
            block = source[start : next_def if next_def != -1 else len(source)]
            assert "delete_purchases_for_course_id" in block, (
                f"{marker} must call delete_purchases_for_course_id"
            )
