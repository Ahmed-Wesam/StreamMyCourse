"""DSQL-5 S6: preview HTTPS catalog billing routes (D8 bundle GET, course price PATCH)."""

from __future__ import annotations

import os
from typing import Iterator

import httpx
import pytest

from helpers.api import ApiClient
from helpers.factories import build_course_factory

_JOD_FILS_STEP = 1000
_COURSE_PRICE_FILS = 2000


def _is_preview_stack() -> bool:
    return os.environ.get("INTEGRATION_API_STACK", "").strip().endswith("Api-dsql")


pytestmark = pytest.mark.skipif(
    not _is_preview_stack(),
    reason="billing catalog HTTPS tests require StreamMyCourse-Api-dsql (S5 deployed)",
)


@pytest.fixture(scope="session")
def api_base_url() -> str:
    value = os.environ.get("INTEGRATION_API_BASE_URL", "").strip()
    if not value:
        pytest.skip("INTEGRATION_API_BASE_URL not set")
    return value.rstrip("/")


@pytest.fixture
def teacher_api(api_base_url: str) -> Iterator[ApiClient]:
    token = os.environ.get("INTEGRATION_COGNITO_JWT", "").strip()
    if not token:
        pytest.skip("INTEGRATION_COGNITO_JWT not set")
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(base_url=api_base_url, timeout=30.0, headers=headers) as client:
        yield ApiClient(client)


def test_get_billing_bundle_jod_whole_fils(api_base_url: str) -> None:
    with httpx.Client(base_url=api_base_url, timeout=30.0) as client:
        resp = client.get("/billing/bundle")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert str(body.get("currency") or "").upper() == "JOD"
    amount = body.get("amountMinor")
    assert amount is not None
    amount_minor = int(amount)
    assert amount_minor > 0
    assert amount_minor % _JOD_FILS_STEP == 0


def test_teacher_patch_course_price_visible_on_get_course(teacher_api: ApiClient) -> None:
    course_ids: list[str] = []
    factory = build_course_factory(teacher_api, course_ids.append)
    try:
        course = factory(label="billing-price-patch")
        patch = teacher_api.raw.patch(
            f"/billing/courses/{course.course_id}/price",
            json={"amountMinor": _COURSE_PRICE_FILS},
        )
        assert patch.status_code == 200, patch.text
        get = teacher_api.get_course(course.course_id)
        assert get.status_code == 200, get.text
        payload = get.json()
        assert int(payload.get("priceAmountMinor") or 0) == _COURSE_PRICE_FILS
    finally:
        for course_id in course_ids:
            try:
                teacher_api.delete_course(course_id)
            except Exception:
                pass
