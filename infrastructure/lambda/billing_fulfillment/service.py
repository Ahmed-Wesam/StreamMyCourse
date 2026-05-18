"""Billing fulfillment application service (WS3)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from fulfillment_config import FulfillmentConfig
from domain_events import BillingDomainEvent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FulfillmentResult:
    recorded: bool = False
    subscription_updated: bool = False
    skipped_environment: bool = False


class FulfillmentRepository(Protocol):
    def process_event(self, event: BillingDomainEvent) -> FulfillmentResult:
        """Persist webhook idempotently and apply subscription mutation when new."""


def process_domain_event(
    event: BillingDomainEvent,
    config: FulfillmentConfig,
    repo: FulfillmentRepository,
) -> FulfillmentResult:
    if event.environment != config.deployment_environment:
        logger.error(
            "billing_fulfillment environment mismatch message_env=%s deployment_env=%s "
            "provider_event_id=%s",
            event.environment,
            config.deployment_environment,
            event.provider_event_id,
        )
        return FulfillmentResult(skipped_environment=True)
    return repo.process_event(event)
