"""Pytest fixtures and session hooks for the integ test suite.

Required environment variables (set by CI; for local runs see README.md):

- INTEG_API_BASE_URL  -- e.g. https://abc123.execute-api.eu-west-1.amazonaws.com/integ
- INTEG_TABLE_NAME    -- e.g. StreamMyCourse-Catalog-integ
- INTEG_VIDEO_BUCKET  -- e.g. streammycourse-video-integ-...
- INTEG_REGION        -- defaults to eu-west-1
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
from helpers.cleanup import run_safety_net


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
    return _required_env("INTEG_API_BASE_URL").rstrip("/")


@pytest.fixture(scope="session")
def integ_table_name() -> str:
    return _required_env("INTEG_TABLE_NAME")


@pytest.fixture(scope="session")
def integ_video_bucket() -> str:
    return _required_env("INTEG_VIDEO_BUCKET")


@pytest.fixture(scope="session")
def integ_region() -> str:
    return os.environ.get("INTEG_REGION", "eu-west-1")


# --- HTTP client ----------------------------------------------------------------


@pytest.fixture(scope="session")
def http_client(api_base_url: str) -> Iterator[httpx.Client]:
    # Dev (and some prod) stacks enforce Cognito on mutating routes. CI sets
    # INTEG_COGNITO_JWT set by verify-rds-reusable (minted or COGNITO_RDS_VERIFY_JWT); local runs
    # can export the same variable after signing in via the hosted UI.
    default_headers: dict[str, str] = {}
    token = os.environ.get("INTEG_COGNITO_JWT", "").strip()
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
    """Sweep any test-prefixed leftovers in DDB and the integ video S3 bucket.
    Logs to stdout and to GITHUB_STEP_SUMMARY when present. Never fails CI."""
    table_name = os.environ.get("INTEG_TABLE_NAME", "").strip()
    bucket = os.environ.get("INTEG_VIDEO_BUCKET", "").strip()
    region = os.environ.get("INTEG_REGION", "eu-west-1")
    if not table_name or not bucket:
        return  # nothing to do

    try:
        report = run_safety_net(
            table_name=table_name,
            bucket=bucket,
            region=region,
            title_prefix=TEST_TITLE_PREFIX,
        )
    except Exception as e:  # broad: never let cleanup raise from a session hook
        sys.stderr.write(f"[integ] safety-net cleanup raised: {e}\n")
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
