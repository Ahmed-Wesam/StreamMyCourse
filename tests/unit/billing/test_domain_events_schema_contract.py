"""Edge vs fulfillment BillingDomainEvent SQS contract (WS3)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_EDGE_SRC = Path(__file__).resolve().parents[3] / "infrastructure" / "lambda" / "billing_edge"
_FULFILL_SRC = Path(__file__).resolve().parents[3] / "infrastructure" / "lambda" / "billing_fulfillment"

if str(_EDGE_SRC) not in sys.path:
    sys.path.append(str(_EDGE_SRC))
if str(_FULFILL_SRC) not in sys.path:
    sys.path.append(str(_FULFILL_SRC))

from domain.events import BillingDomainEvent as EdgeEvent  # noqa: E402
from domain_events import BillingDomainEvent as FulfillmentEvent  # noqa: E402

_REQUIRED_SQS_KEYS = frozenset(
    {
        "schema_version",
        "event_type",
        "provider",
        "provider_event_id",
        "environment",
        "user_sub",
        "plan_id",
        "payload_digest",
    }
)


def test_edge_and_fulfillment_sqs_required_keys_match() -> None:
    sample = EdgeEvent(
        event_type="purchase.paid",
        provider="hyperpay",
        provider_event_id="hyperpay:T1:000.000.000",
        environment="dev",
        user_sub="sub-1",
        plan_id="",
        payload_digest="d" * 64,
        purchase_id="c0000000-0000-4000-8000-000000000001",
        amount_minor=50_000,
        currency="JOD",
    )
    edge_body = sample.to_sqs_dict()
    assert _REQUIRED_SQS_KEYS <= frozenset(edge_body.keys())

    restored = FulfillmentEvent.from_sqs_dict(json.loads(json.dumps(edge_body)))
    assert restored.event_type == sample.event_type
    assert restored.provider_event_id == sample.provider_event_id
    assert restored.purchase_id == sample.purchase_id

    round_trip = FulfillmentEvent.from_sqs_dict(restored.to_sqs_dict())
    assert round_trip == restored
