"""HyperPay: deploy-payments.sh must fail when access token / entity id empty after hydration."""

from __future__ import annotations

from pathlib import Path


def _deploy_payments_text() -> str:
    path = Path(__file__).resolve().parents[2] / "scripts" / "deploy-payments.sh"
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def test_deploy_payments_documents_hyperpay_sm_hydration() -> None:
    text = _deploy_payments_text()
    assert "streammycourse/hyperpay/" in text
    assert "access_token" in text


def test_deploy_payments_passes_billing_fulfillment_alert_email() -> None:
    text = _deploy_payments_text()
    assert "BILLING_FULFILLMENT_ALERT_EMAIL" in text
    assert "BillingFulfillmentAlertEmail=${BILLING_FULFILLMENT_ALERT_EMAIL}" in text


def test_deploy_payments_exits_when_access_token_empty_after_hydration() -> None:
    text = _deploy_payments_text()
    hydration = text.index("# Hydrate HyperPay")
    guard = text.index("HYPERPAY_ACCESS_TOKEN is empty", hydration)
    assert "exit 1" in text[guard : guard + 500]


def test_deploy_payments_entity_id_guard_in_script() -> None:
    text = _deploy_payments_text()
    assert "HYPERPAY_ENTITY_ID is empty after hydration" in text
