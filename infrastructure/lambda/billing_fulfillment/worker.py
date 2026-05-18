"""SQS-triggered billing fulfillment worker (WS3)."""

from __future__ import annotations

import _vendor_bootstrap  # noqa: F401  # must precede fulfillment_repo -> psycopg2

import json
import logging
import os
from typing import Any, Dict, List

from domain_events import BillingDomainEvent
from fulfillment_config import FulfillmentConfig, load_fulfillment_config
from fulfillment_repo import get_cached_repository
from service import FulfillmentRepository, process_domain_event

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())

_config_loader = load_fulfillment_config
_repo_factory = get_cached_repository


def _parse_record_body(body: str) -> BillingDomainEvent:
    data = json.loads(body)
    if not isinstance(data, dict):
        raise ValueError("SQS body must be a JSON object")
    return BillingDomainEvent.from_sqs_dict(data)


def process_sqs_record(
    record: Dict[str, Any],
    *,
    config: FulfillmentConfig,
    repo: FulfillmentRepository,
) -> None:
    message_id = str(record.get("messageId") or "")
    body = record.get("body") or ""
    if not isinstance(body, str):
        raise ValueError("SQS record body must be a string")
    event = _parse_record_body(body)
    result = process_domain_event(event, config, repo)
    if result.skipped_environment:
        raise ValueError(
            f"billing fulfillment environment mismatch: message={event.environment!r} "
            f"deployment={config.deployment_environment!r}"
        )
    logger.info(
        "billing_fulfillment processed message_id=%s provider_event_id=%s event_type=%s "
        "recorded=%s subscription_updated=%s skipped_environment=%s",
        message_id,
        event.provider_event_id,
        event.event_type,
        result.recorded,
        result.subscription_updated,
        result.skipped_environment,
    )


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    config = _config_loader()
    if not config.deployment_environment:
        raise RuntimeError("DEPLOYMENT_ENVIRONMENT is required")
    if not config.db_secret_arn or not config.db_host:
        raise RuntimeError("DB_SECRET_ARN and DB_HOST are required")

    repo = _repo_factory(config)
    failures: List[Dict[str, str]] = []

    for record in event.get("Records") or []:
        message_id = str(record.get("messageId") or "")
        try:
            process_sqs_record(record, config=config, repo=repo)
        except Exception:
            logger.exception(
                "billing_fulfillment failed message_id=%s",
                message_id,
            )
            if message_id:
                failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": failures}
