"""W4-P3: GET /billing/merchant/status wired in catalog index."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple
from unittest.mock import MagicMock, patch

import pytest

import index as index_mod
from config import AppConfig


@pytest.fixture(autouse=True)
def _allowed_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOWED_ORIGINS", "*")


def _bootstrap_returning(
    cfg: AppConfig,
    *,
    merchant_service: Optional[Any] = None,
):
    def _stub() -> Tuple[Any, ...]:
        return (
            cfg,
            MagicMock(name="course_svc"),
            MagicMock(name="auth_svc"),
            MagicMock(name="progress_svc"),
            MagicMock(name="qb_svc"),
            merchant_service,
            None,
        )

    return _stub


def _cfg() -> AppConfig:
    return AppConfig(
        video_bucket="b",
        default_mp4_url="",
        video_url="",
        allowed_origins=["*"],
        db_host="rds.example.com",
        db_name="smc",
        db_secret_arn="arn:aws:secretsmanager:eu-west-1:123:secret:x",
        billing_teacher_sub="teacher-sub-abc",
        deployment_environment="dev",
    )


def test_index_routes_get_billing_merchant_status(
    make_lambda_event,
) -> None:
    cfg = _cfg()
    merchant_svc = MagicMock()
    evt = make_lambda_event(method="GET", path="/billing/merchant/status")
    evt["requestContext"]["authorizer"] = {"claims": {"sub": "teacher-sub-abc"}}

    with patch.object(index_mod, "lambda_bootstrap", _bootstrap_returning(cfg, merchant_service=merchant_svc)):
        with patch.object(
            index_mod,
            "handle_merchant_status",
            return_value={"statusCode": 200, "headers": {}, "body": "{}"},
        ) as mock_handler:
            resp = index_mod.lambda_handler(evt, None)

    assert resp["statusCode"] == 200
    mock_handler.assert_called_once()
    _args, kwargs = mock_handler.call_args
    assert kwargs["merchant_svc"] is merchant_svc
    assert kwargs["billing_teacher_sub"] == "teacher-sub-abc"


def test_index_merchant_status_json_contract(
    make_lambda_event,
) -> None:
    cfg = _cfg()
    merchant_svc = MagicMock()
    merchant_svc.get_merchant_status.return_value = {
        "provider": "paytabs",
        "providerProfileId": "mock-profile",
        "payoutReady": False,
        "payoutReadyAt": None,
        "setupChecklist": {
            "paytabsAccountCreated": True,
            "profileIdConfigured": True,
            "repeatBillingEnabled": False,
            "termsUrlSet": False,
            "ipnRegistered": False,
            "testChargeSucceeded": False,
            "payoutMarkedReady": False,
        },
    }
    evt = make_lambda_event(method="GET", path="/billing/merchant/status")
    evt["requestContext"]["authorizer"] = {"claims": {"sub": "teacher-sub-abc"}}

    with patch.object(index_mod, "lambda_bootstrap", _bootstrap_returning(cfg, merchant_service=merchant_svc)):
        resp = index_mod.lambda_handler(evt, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert set(body.keys()) == {
        "provider",
        "providerProfileId",
        "payoutReady",
        "payoutReadyAt",
        "setupChecklist",
    }
    assert set(body["setupChecklist"].keys()) == {
        "paytabsAccountCreated",
        "profileIdConfigured",
        "repeatBillingEnabled",
        "termsUrlSet",
        "ipnRegistered",
        "testChargeSucceeded",
        "payoutMarkedReady",
    }
    assert "serverKey" not in json.dumps(body).lower()
