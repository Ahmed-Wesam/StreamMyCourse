"""W3-P3 — SQS enqueue for billing domain events."""

from __future__ import annotations

import json
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from domain.events import BillingDomainEvent
from queue_shim import EnqueueError, enqueue_domain_events

_DIGEST = "e" * 64
_QUEUE_URL = "https://sqs.eu-west-1.amazonaws.com/123456789012/billing-fulfillment"


def _event(event_type: str = "subscription.activated") -> BillingDomainEvent:
    return BillingDomainEvent(
        event_type=event_type,
        provider="paytabs",
        provider_event_id="paytabs:TST1:A",
        environment="dev",
        user_sub="user-1",
        plan_id="00000000-0000-4000-8000-000000000001",
        payload_digest=_DIGEST,
    )


class _FakeSqsClient:
    def __init__(self, *, fail_on_index: int | None = None) -> None:
        self.messages: List[Dict[str, Any]] = []
        self._fail_on_index = fail_on_index
        self._call_count = 0

    def send_message(self, *, QueueUrl: str, MessageBody: str) -> Dict[str, Any]:  # noqa: N803
        self._call_count += 1
        if self._fail_on_index is not None and self._call_count == self._fail_on_index:
            raise RuntimeError("SQS unavailable")
        self.messages.append({"QueueUrl": QueueUrl, "MessageBody": MessageBody})
        return {"MessageId": f"msg-{self._call_count}", "ResponseMetadata": {"HTTPStatusCode": 200}}


def test_enqueue_sends_sequential_messages() -> None:
    client = _FakeSqsClient()
    events = [_event("subscription.activated"), _event("subscription.renewed")]
    enqueue_domain_events(events, queue_url=_QUEUE_URL, sqs_client=client)
    assert len(client.messages) == 2
    assert client.messages[0]["QueueUrl"] == _QUEUE_URL


def test_enqueue_body_is_domain_json_without_paytabs_keys() -> None:
    client = _FakeSqsClient()
    enqueue_domain_events([_event()], queue_url=_QUEUE_URL, sqs_client=client)
    body = json.loads(client.messages[0]["MessageBody"])
    assert body["schema_version"] == 1
    assert body["event_type"] == "subscription.activated"
    assert "tran_ref" not in body
    assert "cart_id" not in body
    assert "payment_result" not in body


def test_enqueue_failure_on_first_message_raises_without_sending() -> None:
    client = _FakeSqsClient(fail_on_index=1)
    with pytest.raises(EnqueueError):
        enqueue_domain_events(
            [_event(), _event("subscription.renewed")],
            queue_url=_QUEUE_URL,
            sqs_client=client,
        )
    assert len(client.messages) == 0


def test_enqueue_failure_on_second_message_leaves_first_sent() -> None:
    client = _FakeSqsClient(fail_on_index=2)
    with pytest.raises(EnqueueError):
        enqueue_domain_events(
            [_event("subscription.activated"), _event("subscription.renewed")],
            queue_url=_QUEUE_URL,
            sqs_client=client,
        )
    assert len(client.messages) == 1


def test_enqueue_empty_queue_url_raises() -> None:
    with pytest.raises(EnqueueError):
        enqueue_domain_events([_event()], queue_url="", sqs_client=MagicMock())
