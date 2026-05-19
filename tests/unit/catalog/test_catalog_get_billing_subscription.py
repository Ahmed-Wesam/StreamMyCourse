"""W7-P2: GET /billing/subscription — catalog Lambda (manage-contract-v1)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

import index as index_mod
from config import AppConfig
from services.subscription.controller import handle_get_subscription
from services.subscription.repo import SubscriptionSummary

_MANAGE_RESPONSE_KEYS = frozenset(
    {
        "status",
        "currentPeriodEnd",
        "cancelAtPeriodEnd",
        "canCancel",
        "canReactivate",
        "nextBillingDate",
        "amountMinor",
        "currency",
        "planLabel",
        "pastDue",
    }
)

_PERIOD_END = datetime(2026, 6, 18, 0, 0, 0, tzinfo=timezone.utc)


def _body(resp: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(resp["body"])


def _active_summary() -> SubscriptionSummary:
    return SubscriptionSummary(
        status="active",
        current_period_end=_PERIOD_END,
        cancel_at_period_end=False,
        can_cancel=True,
        can_reactivate=False,
        next_billing_date=_PERIOD_END,
        amount_minor=50000,
        currency="JOD",
        plan_label="50 JOD / month",
        past_due=False,
    )


@pytest.fixture(autouse=True)
def _allowed_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOWED_ORIGINS", "*")


def _cfg() -> AppConfig:
    return AppConfig(
        video_bucket="b",
        default_mp4_url="",
        video_url="",
        allowed_origins=["*"],
        db_host="rds.example.com",
        db_name="smc",
        db_secret_arn="arn:aws:secretsmanager:eu-west-1:123:secret:x",
        deployment_environment="dev",
    )


def _bootstrap_returning(cfg: AppConfig, *, manage_svc: Any):
    def _stub():
        return (
            cfg,
            MagicMock(name="course_svc"),
            MagicMock(name="auth_svc"),
            MagicMock(name="progress_svc"),
            MagicMock(name="qb_svc"),
            MagicMock(name="merchant_svc"),
            manage_svc,
        )

    return _stub


class TestGetBillingSubscriptionController:
    def test_200_json_shape_camel_case(self, make_lambda_event) -> None:
        evt = make_lambda_event(method="GET", path="/billing/subscription")
        evt["requestContext"]["authorizer"] = {"claims": {"sub": "student-sub-1"}}

        manage_svc = MagicMock()
        manage_svc.get_subscription_summary.return_value = _active_summary()

        resp = handle_get_subscription(evt, origin="*", manage_svc=manage_svc)

        assert resp["statusCode"] == 200
        body = _body(resp)
        assert set(body.keys()) == _MANAGE_RESPONSE_KEYS
        assert body["status"] == "active"
        assert body["currentPeriodEnd"] == "2026-06-18T00:00:00.000Z"
        assert body["cancelAtPeriodEnd"] is False
        assert body["canCancel"] is True
        assert body["canReactivate"] is False
        assert body["nextBillingDate"] == "2026-06-18T00:00:00.000Z"
        assert body["amountMinor"] == 50000
        assert body["currency"] == "JOD"
        assert body["planLabel"] == "50 JOD / month"
        assert body["pastDue"] is False
        manage_svc.get_subscription_summary.assert_called_once_with(user_sub="student-sub-1")

    def test_404_not_subscribed(self, make_lambda_event) -> None:
        evt = make_lambda_event(method="GET", path="/billing/subscription")
        evt["requestContext"]["authorizer"] = {"claims": {"sub": "student-sub-1"}}

        manage_svc = MagicMock()
        manage_svc.get_subscription_summary.return_value = None

        resp = handle_get_subscription(evt, origin="*", manage_svc=manage_svc)

        assert resp["statusCode"] == 404
        assert _body(resp) == {
            "code": "not_subscribed",
            "message": "No active subscription to manage",
        }

    def test_401_without_jwt(self, make_lambda_event) -> None:
        evt = make_lambda_event(method="GET", path="/billing/subscription")

        manage_svc = MagicMock()
        resp = handle_get_subscription(evt, origin="*", manage_svc=manage_svc)

        assert resp["statusCode"] == 401
        assert _body(resp) == {
            "code": "unauthorized",
            "message": "Authentication required",
        }
        manage_svc.get_subscription_summary.assert_not_called()


class TestGetBillingSubscriptionRouting:
    def test_index_routes_get_billing_subscription(self, make_lambda_event) -> None:
        cfg = _cfg()
        manage_svc = MagicMock()
        evt = make_lambda_event(method="GET", path="/billing/subscription")
        evt["requestContext"]["authorizer"] = {"claims": {"sub": "student-sub-1"}}

        with patch.object(
            index_mod, "lambda_bootstrap", _bootstrap_returning(cfg, manage_svc=manage_svc)
        ):
            with patch.object(
                index_mod,
                "handle_get_subscription",
                return_value={"statusCode": 200, "headers": {}, "body": "{}"},
            ) as mock_handler:
                resp = index_mod.lambda_handler(evt, None)

        assert resp["statusCode"] == 200
        mock_handler.assert_called_once()
        _args, kwargs = mock_handler.call_args
        assert kwargs["manage_svc"] is manage_svc
