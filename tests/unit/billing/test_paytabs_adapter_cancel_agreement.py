"""W8-P3 — PayTabs agreement cancel (mocked HTTP)."""

from __future__ import annotations

import json
from io import BytesIO
from typing import Any
from unittest.mock import patch

import pytest
from urllib.error import HTTPError

from providers.paytabs_adapter import BillingUnconfiguredError, PayTabsAdapter

_AGREEMENT_ID = "agreement-123"
_SERVER_KEY = "sk-test"
_PROFILE_ID = "987654"
_API_DOMAIN = "secure-jordan.paytabs.com"


def _adapter() -> PayTabsAdapter:
    return PayTabsAdapter(
        server_key=_SERVER_KEY,
        profile_id=_PROFILE_ID,
        api_domain=_API_DOMAIN,
        deployment_environment="dev",
    )


def test_cancel_agreement_posts_with_auth_and_body() -> None:
    adapter = _adapter()
    captured: dict[str, Any] = {}

    def fake_urlopen(req: Any, timeout: float = 0) -> Any:
        captured["url"] = req.full_url
        captured["headers"] = dict(req.header_items())
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return BytesIO(json.dumps({"code": 200, "message": "Success"}).encode("utf-8"))

    with patch("providers.paytabs_adapter.urlopen", side_effect=fake_urlopen):
        adapter.cancel_agreement(_AGREEMENT_ID)

    assert captured["url"] == f"https://{_API_DOMAIN}/payment/agreement/cancel"
    headers = {k.lower(): v for k, v in captured["headers"].items()}
    assert headers.get("authorization") == _SERVER_KEY
    assert headers.get("content-type") == "application/json"
    body = captured["body"]
    assert body["profile_id"] == int(_PROFILE_ID)
    assert body["agreement_id"] == _AGREEMENT_ID


def test_cancel_agreement_raises_on_non_2xx() -> None:
    adapter = _adapter()

    def fake_urlopen(req: Any, timeout: float = 0) -> Any:
        raise HTTPError(
            req.full_url,
            400,
            "Bad Request",
            hdrs=None,
            fp=BytesIO(b'{"message":"invalid agreement"}'),
        )

    with patch("providers.paytabs_adapter.urlopen", side_effect=fake_urlopen):
        with pytest.raises(BillingUnconfiguredError):
            adapter.cancel_agreement(_AGREEMENT_ID)


def test_cancel_agreement_raises_when_keys_missing() -> None:
    adapter = PayTabsAdapter(
        server_key="",
        profile_id="",
        api_domain=_API_DOMAIN,
        deployment_environment="dev",
    )
    with pytest.raises(BillingUnconfiguredError):
        adapter.cancel_agreement(_AGREEMENT_ID)
