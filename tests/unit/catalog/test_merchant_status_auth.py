"""W4-P1: teacher-only auth for GET /billing/merchant/status."""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from services.billing_merchant.controller import handle_merchant_status


def _body(resp: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(resp["body"])


def test_merchant_status_forbidden_when_sub_not_billing_teacher(
    make_lambda_event,
) -> None:
    evt = make_lambda_event(method="GET", path="/billing/merchant/status")
    evt["requestContext"]["authorizer"] = {"claims": {"sub": "student-sub-123"}}

    merchant_svc = MagicMock()
    resp = handle_merchant_status(
        evt,
        origin="*",
        merchant_svc=merchant_svc,
        billing_teacher_sub="teacher-sub-abc",
    )

    assert resp["statusCode"] == 403
    assert _body(resp) == {"message": "Forbidden", "code": "forbidden"}
    merchant_svc.get_merchant_status.assert_not_called()


def test_merchant_status_billing_unconfigured_when_teacher_sub_unset(
    make_lambda_event,
) -> None:
    evt = make_lambda_event(method="GET", path="/billing/merchant/status")
    evt["requestContext"]["authorizer"] = {"claims": {"sub": "teacher-sub-abc"}}

    merchant_svc = MagicMock()
    resp = handle_merchant_status(
        evt,
        origin="*",
        merchant_svc=merchant_svc,
        billing_teacher_sub="",
    )

    assert resp["statusCode"] == 503
    assert _body(resp)["code"] == "billing_unconfigured"
    merchant_svc.get_merchant_status.assert_not_called()


def test_merchant_status_200_when_sub_matches_billing_teacher(
    make_lambda_event,
) -> None:
    evt = make_lambda_event(method="GET", path="/billing/merchant/status")
    evt["requestContext"]["authorizer"] = {"claims": {"sub": "teacher-sub-abc"}}

    merchant_svc = MagicMock()
    merchant_svc.get_merchant_status.return_value = {
        "provider": "paytabs",
        "providerProfileId": "profile-1",
        "payoutReady": False,
        "payoutReadyAt": None,
        "setupChecklist": {"profileIdConfigured": True},
    }

    resp = handle_merchant_status(
        evt,
        origin="*",
        merchant_svc=merchant_svc,
        billing_teacher_sub="teacher-sub-abc",
    )

    assert resp["statusCode"] == 200
    assert _body(resp)["provider"] == "paytabs"
    merchant_svc.get_merchant_status.assert_called_once()
