"""W6-P1d / RS-5: catalog lambda_handler internal billing.checkout invoke branch."""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import patch

from index import lambda_handler

_COURSE_ID = "b0000000-0000-4000-8000-000000000001"


class TestInternalBillingCheckoutInvoke:
    def test_internal_event_dispatched_before_apigw_routing(self) -> None:
        expected: Dict[str, Any] = {
            "blockReason": None,
            "product": {
                "amount_minor": 9900,
                "currency": "USD",
                "course_id": _COURSE_ID,
                "purchase_id": "c0000000-0000-4000-8000-000000000001",
            },
        }
        with patch("index._handle_internal_billing_event", return_value=expected) as mock:
            event = {
                "internal": "billing.checkout",
                "userSub": "cognito-sub-1",
                "productType": "course",
                "courseId": _COURSE_ID,
            }
            out = lambda_handler(event, None)
            mock.assert_called_once_with(event)
            assert out == expected

    def test_already_owned_block_reason(self) -> None:
        with patch(
            "index._handle_internal_billing_event",
            return_value={"blockReason": "already_owned"},
        ):
            out = lambda_handler(
                {
                    "internal": "billing.checkout",
                    "userSub": "u",
                    "productType": "bundle",
                },
                None,
            )
            assert out == {"blockReason": "already_owned"}

    def test_apigw_event_not_treated_as_internal(self, make_lambda_event) -> None:
        with patch("index._handle_internal_billing_event") as mock_internal:
            with patch("index.load_config") as mock_cfg:
                mock_cfg.return_value.allowed_origins = []
                event = make_lambda_event(method="GET", path="/courses")
                lambda_handler(event, None)
                mock_internal.assert_not_called()
