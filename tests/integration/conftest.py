"""Pytest fixtures and session hooks for the HTTP integration test suite.

Required environment variables (set by CI; for local runs see README.md):

- INTEGRATION_API_BASE_URL  -- API Gateway base URL (no trailing slash)
- INTEGRATION_VIDEO_BUCKET  -- S3 bucket for lesson/thumbnail uploads
- INTEGRATION_AWS_REGION    -- defaults to eu-west-1
"""

from __future__ import annotations

import os
import sys
from typing import Iterator, List

import httpx
import pytest

from helpers.api import ApiClient
from helpers.factories import (
    TEST_TITLE_PREFIX,
    build_course_factory,
    build_lesson_factory,
)
from helpers.cleanup import log_integration_cleanup_error, run_safety_net


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        pytest.exit(
            f"Required environment variable {name} is not set. "
            "See tests/integration/README.md for local-run instructions.",
            returncode=2,
        )
    return value


# --- Session-scoped configuration ------------------------------------------------


@pytest.fixture(scope="session")
def api_base_url() -> str:
    return _required_env("INTEGRATION_API_BASE_URL").rstrip("/")


@pytest.fixture(scope="session")
def video_bucket() -> str:
    return _required_env("INTEGRATION_VIDEO_BUCKET")


@pytest.fixture(scope="session")
def aws_region() -> str:
    return os.environ.get("INTEGRATION_AWS_REGION", "eu-west-1")


# --- HTTP client ----------------------------------------------------------------


@pytest.fixture(scope="session")
def http_client(api_base_url: str) -> Iterator[httpx.Client]:
    # Dev (and prod) stacks enforce Cognito on mutating routes.
    # CI: `.github/workflows/deploy-backend.yml` `integration-http-tests` mints
    # `INTEGRATION_COGNITO_JWT` (same flow as `verify-rds-reusable.yml`).
    default_headers: dict[str, str] = {}
    token = os.environ.get("INTEGRATION_COGNITO_JWT", "").strip()
    if token:
        default_headers["Authorization"] = f"Bearer {token}"
    with httpx.Client(
        base_url=api_base_url, timeout=30.0, headers=default_headers or None
    ) as client:
        yield client


@pytest.fixture
def api(http_client: httpx.Client) -> ApiClient:
    return ApiClient(http_client)


# --- Per-test course/lesson factories with auto-cleanup -------------------------


@pytest.fixture
def course_factory(api: ApiClient, request: pytest.FixtureRequest):
    """Create courses via the API; deleted at test teardown via DELETE /courses/{id}.

    Lesson cleanup is implicit because course delete cascades to its lessons."""
    created_course_ids: List[str] = []

    def register(course_id: str) -> None:
        created_course_ids.append(course_id)

    factory = build_course_factory(api, register)

    def cleanup() -> None:
        for course_id in created_course_ids:
            try:
                api.delete_course(course_id)
            except Exception:
                # Per policy, cleanup failures are non-fatal; safety net catches leftovers.
                pass

    request.addfinalizer(cleanup)
    return factory


@pytest.fixture
def lesson_factory(api: ApiClient):
    """Create lessons; cleanup happens transitively when the parent course is deleted."""
    return build_lesson_factory(api)


# --- Session-end safety net -----------------------------------------------------


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Sweep test-prefixed leftover courses (HTTP) and their S3 prefixes only.

    Courses: ``GET /courses/mine`` + ``DELETE /courses/{id}`` when
    ``INTEGRATION_API_BASE_URL`` and ``INTEGRATION_COGNITO_JWT`` are set.
    S3: deletes objects only under ``{courseId}/`` for matched integration-test
    courses (shared dev buckets are not fully emptied). Never fails CI."""
    bucket = os.environ.get("INTEGRATION_VIDEO_BUCKET", "").strip()
    region = os.environ.get("INTEGRATION_AWS_REGION", "eu-west-1")
    if not bucket:
        return

    try:
        report = run_safety_net(
            bucket=bucket,
            region=region,
            title_prefix=TEST_TITLE_PREFIX,
        )
    except Exception as e:  # broad: never let cleanup raise from a session hook
        log_integration_cleanup_error(f"session safety-net raised: {e!r}")
        return

    summary = report.render_summary()
    sys.stderr.write(summary + "\n")

    step_summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary_path:
        try:
            with open(step_summary_path, "a", encoding="utf-8") as fh:
                fh.write(summary + "\n")
        except Exception:
            pass
