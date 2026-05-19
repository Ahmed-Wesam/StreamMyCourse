"""W6-P1d: catalog lambda_handler internal billing.checkout invoke branch."""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from index import lambda_handler

DEV_PLAN_ID = "a0000000-0000-4000-8000-000000000011"


@pytest.fixture
def mock_internal_billing() -> MagicMock:
    with patch("index._handle_internal_billing_event") as handler:
        yield handler


class TestInternalBillingCheckoutInvoke:
    def test_internal_event_dispatched_before_apigw_routing(self) -> None:
        expected: Dict[str, Any] = {
            "blockReason": None,
            "plan": {"amount_minor": 50000, "currency": "JOD", "plan_key": "monthly_all_access"},
        }
        with patch("index._handle_internal_billing_event", return_value=expected) as mock:
            event = {
                "internal": "billing.checkout",
                "userSub": "cognito-sub-1",
                "planId": DEV_PLAN_ID,
            }
            out = lambda_handler(event, None)
            mock.assert_called_once_with(event)
            assert out == expected

    def test_already_subscribed_block_reason(self) -> None:
        with patch(
            "index._handle_internal_billing_event",
            return_value={"blockReason": "already_subscribed"},
        ):
            out = lambda_handler(
                {"internal": "billing.checkout", "userSub": "u", "planId": DEV_PLAN_ID},
                None,
            )
            assert out == {"blockReason": "already_subscribed"}

    def test_apigw_event_not_treated_as_internal(self, make_lambda_event) -> None:
        with patch("index._handle_internal_billing_event") as mock_internal:
            with patch("index.load_config") as mock_cfg:
                mock_cfg.return_value.allowed_origins = []
                event = make_lambda_event(method="GET", path="/courses")
                lambda_handler(event, None)
                mock_internal.assert_not_called()
