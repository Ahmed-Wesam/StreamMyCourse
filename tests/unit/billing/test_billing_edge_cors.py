"""Billing edge CORS for browser-facing checkout manage routes."""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from billing._imports import billing_handler
from cors import parse_allowed_origins, pick_origin
from edge_config import BillingEdgeConfig
from providers.mock_adapter import MockHyperPayAdapter
from tests.unit.billing.test_billing_edge_handler import (
    _CHECKOUT_BILLING,
    _COURSE_ID,
    _USER_SUB,
    _catalog_ok,
    _edge_config,
)


def test_parse_allowed_origins_csv() -> None:
    assert parse_allowed_origins("https://a.example, https://b.example") == [
        "https://a.example",
        "https://b.example",
    ]


def test_pick_origin_matches_request() -> None:
    allowed = ["https://researchspectrum.org", "https://teach.researchspectrum.org"]
    assert pick_origin(allowed, "https://researchspectrum.org") == "https://researchspectrum.org"


def test_checkout_post_includes_cors_for_allowed_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(
        billing_handler,
        "_get_payment_provider",
        lambda _cfg: MockHyperPayAdapter(),
    )
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_checkout",
        lambda **_kw: _catalog_ok(),
    )

    evt: Dict[str, Any] = {
        "httpMethod": "POST",
        "path": "/billing/checkout-session",
        "requestContext": {
            "resourcePath": "/billing/checkout-session",
            "authorizer": {
                "claims": {"sub": _USER_SUB, "email": "student@example.com"},
            },
        },
        "headers": {
            "content-type": "application/json",
            "Origin": "https://researchspectrum.org",
        },
        "body": json.dumps(
            {
                "productType": "course",
                "courseId": _COURSE_ID,
                "billing": _CHECKOUT_BILLING,
            }
        ),
    }
    resp = billing_handler.lambda_handler(evt, None)
    assert resp["statusCode"] == 200
    headers = resp.get("headers") or {}
    assert headers.get("Access-Control-Allow-Origin") == "https://researchspectrum.org"
