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
from helpers.cleanup import (
    CleanupReport,
    delete_orphan_media_for_course_prefixes,
    log_integration_cleanup_error,
)


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


# --- Multi-principal HTTP clients (for cross-user access control tests) -------


# Environment variable names for multi-principal JWTs
_ALT_JWT_ENV = "INTEGRATION_COGNITO_JWT_ALT"
_STUDENT_JWT_ENV = "INTEGRATION_COGNITO_JWT_STUDENT"


@pytest.fixture(scope="session")
def alt_http_client(api_base_url: str) -> Iterator[httpx.Client]:
    """HTTP client authenticated as an alternate teacher (teacher B).

    Requires INTEGRATION_COGNITO_JWT_ALT to be set.
    """
    token = _required_env(_ALT_JWT_ENV)
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(base_url=api_base_url, timeout=30.0, headers=headers) as client:
        yield client


@pytest.fixture(scope="session")
def student_http_client(api_base_url: str) -> Iterator[httpx.Client]:
    """HTTP client authenticated as a student.

    Requires INTEGRATION_COGNITO_JWT_STUDENT to be set.
    """
    token = _required_env(_STUDENT_JWT_ENV)
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(base_url=api_base_url, timeout=30.0, headers=headers) as client:
        yield client


# --- Multi-principal ApiClient wrappers ----------------------------------------


@pytest.fixture
def alt_api(alt_http_client: httpx.Client) -> ApiClient:
    """ApiClient wrapping alt_http_client (alternate teacher / teacher B)."""
    return ApiClient(alt_http_client)


@pytest.fixture
def student_api(student_http_client: httpx.Client) -> ApiClient:
    """ApiClient wrapping student_http_client (student principal)."""
    return ApiClient(student_http_client)


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


@pytest.fixture
def alt_course_factory(alt_api: ApiClient, request: pytest.FixtureRequest):
    """Create courses via alt_api (Teacher B); deleted at test teardown via DELETE /courses/{id}."""
    created_course_ids: List[str] = []

    def register(course_id: str) -> None:
        created_course_ids.append(course_id)

    factory = build_course_factory(alt_api, register)

    def cleanup() -> None:
        for course_id in created_course_ids:
            try:
                alt_api.delete_course(course_id)
            except Exception:
                pass

    request.addfinalizer(cleanup)
    return factory


@pytest.fixture
def alt_lesson_factory(alt_api: ApiClient):
    """Create lessons as alternate teacher (Teacher B); cleanup happens transitively when the parent course is deleted."""
    return build_lesson_factory(alt_api)


# --- Enrolled course factory (creates published course and enrolls student) -----


@pytest.fixture
def enrolled_course(
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
    request: pytest.FixtureRequest,
):
    """Factory that creates a published course with a lesson, then enrolls the student.

    Returns a tuple (course_id, lesson_id).

    Uses the existing course_factory and lesson_factory patterns, plus calls
    api.enroll_course() using the student_api client.
    """

    created_enrollments: List[tuple[str, str]] = []

    def _make_enrolled_course() -> tuple[str, str]:
        # 1. Create a course
        course_resp = course_factory(label="Enrolled Course Test")
        course_id = course_resp.course_id

        # 2. Create a lesson
        lesson_resp = lesson_factory(course_id, label="Enrolled Course Lesson")
        lesson_id = lesson_resp.lesson_id

        # 3. Get upload URL to set videoKey (required before marking video ready)
        upload_resp = api.get_upload_url(course_id=course_id, lesson_id=lesson_id)
        assert upload_resp.status_code == 200, f"Failed to get upload URL: {upload_resp.text}"

        # 4. Mark video ready (required for publish)
        api.mark_video_ready(course_id, lesson_id)

        # 4. Publish the course
        api.publish_course(course_id)

        # 5. Enroll the student
        enroll_resp = student_api.enroll_course(course_id)
        if enroll_resp.status_code not in (200, 201):
            # Best-effort: if enrollment fails, note it but don't crash the factory
            pass

        created_enrollments.append((course_id, lesson_id))
        return (course_id, lesson_id)

    # The factory function itself doesn't need cleanup - course_factory handles it
    return _make_enrolled_course


# --- Session-end safety net -----------------------------------------------------


def _run_cleanup_for_token(api_base: str, token: str, title_prefixes: list[str]) -> tuple[list[str], list[str]]:
    """Run safety net cleanup for a specific JWT token with multiple prefixes. Returns (deleted_ids, matched_ids)."""
    from helpers.cleanup import delete_prefixed_teacher_courses_via_http
    all_deleted: list[str] = []
    all_matched: list[str] = []
    for prefix in title_prefixes:
        try:
            deleted, matched = delete_prefixed_teacher_courses_via_http(
                api_base_url=api_base,
                auth_token=token,
                title_prefix=prefix,
            )
            all_deleted.extend(deleted)
            all_matched.extend(matched)
        except Exception as e:
            log_integration_cleanup_error(f"Cleanup for prefix '{prefix}' failed: {e!r}")
    return all_deleted, all_matched


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Sweep test-prefixed leftover courses for ALL principals (HTTP) and their S3 prefixes.

    Cleans up courses for: primary teacher, alt teacher, and student.
    Handles both old '[TEST]' prefix and new 'integration-test-' prefix.
    S3: deletes objects only under ``{courseId}/`` for matched integration-test
    courses (shared dev buckets are not fully emptied). Never fails CI."""
    bucket = os.environ.get("INTEGRATION_VIDEO_BUCKET", "").strip()
    region = os.environ.get("INTEGRATION_AWS_REGION", "eu-west-1")
    api_base = os.environ.get("INTEGRATION_API_BASE_URL", "").strip().rstrip("/")

    if not bucket or not api_base:
        return

    all_deleted_ids: list[str] = []
    all_matched_ids: list[str] = []

    # Clean up for each principal that has a JWT configured
    # Note: student is excluded - students cannot create courses (only enroll),
    # so there's nothing to clean up via /courses/mine safety net
    tokens = [
        ("primary", os.environ.get("INTEGRATION_COGNITO_JWT", "").strip()),
        ("alt_teacher", os.environ.get("INTEGRATION_COGNITO_JWT_ALT", "").strip()),
    ]

    # Support both old '[TEST]' prefix and new 'integration-test-' prefix
    prefixes = [TEST_TITLE_PREFIX, "[TEST]"]

    for principal, token in tokens:
        if not token:
            continue
        deleted, matched = _run_cleanup_for_token(api_base, token, prefixes)
        all_deleted_ids.extend(deleted)
        all_matched_ids.extend(matched)
        if deleted:
            sys.stderr.write(f"Cleaned up {len(deleted)} courses for {principal}\n")

    # S3 cleanup for all matched course IDs
    leftover_objects: list[str] = []
    try:
        leftover_objects = delete_orphan_media_for_course_prefixes(
            bucket, region=region, course_ids=all_matched_ids
        )
    except Exception as e:
        log_integration_cleanup_error(f"S3 safety-net cleanup failed: {e!r}")

    # Report summary
    report = CleanupReport(
        courses_removed_via_api=all_deleted_ids,
        leftover_objects=leftover_objects,
    )
    summary = report.render_summary()
    sys.stderr.write(summary + "\n")

    step_summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary_path:
        try:
            with open(step_summary_path, "a", encoding="utf-8") as fh:
                fh.write(summary + "\n")
        except Exception:
            pass


# --- Slow test skip mechanism ---------------------------------------------------


def pytest_configure(config: pytest.Config) -> None:
    """Register the 'slow' marker for S3-heavy tests."""
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (S3-heavy); skipped when SKIP_SLOW_S3_TESTS=1",
    )


@pytest.fixture(autouse=True)
def skip_slow_tests(request: pytest.FixtureRequest) -> None:
    """Skip tests marked 'slow' when SKIP_SLOW_S3_TESTS=1 is set."""
    if os.environ.get("SKIP_SLOW_S3_TESTS", "") == "1":
        marker = request.node.get_closest_marker("slow")
        if marker is not None:
            pytest.skip("SKIP_SLOW_S3_TESTS=1: skipping slow S3 test")
