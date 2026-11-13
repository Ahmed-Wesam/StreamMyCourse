"""DSQL-2 S6: contact rate limit 429 on preview API (honeypot avoids enqueue)."""

from __future__ import annotations

import os
from typing import Iterator

import httpx
import pytest

from helpers.api import ApiClient

_CONTACT_BODY = {
    "name": "Rate Limit Probe",
    "email": "ratelimit@example.com",
    "category": "General Question",
    "subject": "DSQL-2 rate limit",
    "message": "Integration rate limit probe",
    "rs_hp": "bot",
}


def _is_preview_stack() -> bool:
    stack = os.environ.get("INTEGRATION_API_STACK", "").strip()
    return stack.endswith("Api-dsql")


pytestmark = pytest.mark.skipif(
    not _is_preview_stack(),
    reason="contact 429 gate runs only on StreamMyCourse-Api-dsql",
)


@pytest.fixture(scope="session")
def api_base_url() -> str:
    value = os.environ.get("INTEGRATION_API_BASE_URL", "").strip()
    if not value:
        pytest.skip("INTEGRATION_API_BASE_URL not set")
    return value.rstrip("/")


@pytest.fixture(scope="session")
def http_client(api_base_url: str) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=api_base_url, timeout=30.0) as client:
        yield client


@pytest.fixture
def api(http_client: httpx.Client) -> ApiClient:
    return ApiClient(http_client)


def test_contact_rate_limit_returns_429_with_retry_after(api: ApiClient) -> None:
    """Loops POST /contact with honeypot; expects 202 until one 429.

    Spends preview ``contact.ip`` (5 per 10 minutes) and a few global hits;
    prod ``contact.global`` is not exercised because this test skips off preview.
    """
    saw_429 = False
    for _ in range(8):
        resp = api.post_contact(body=_CONTACT_BODY)
        if resp.status_code == 429:
            saw_429 = True
            retry_after = resp.headers.get("Retry-After")
            assert retry_after is not None
            assert int(retry_after) >= 1
            payload = resp.json()
            assert payload.get("code") == "rate_limited"
            break
        assert resp.status_code == 202, resp.text
    assert saw_429, "expected at least one 429 from contact.ip rate limit"
