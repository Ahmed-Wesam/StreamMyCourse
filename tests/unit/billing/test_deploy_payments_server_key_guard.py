"""WS3-P7: deploy-payments.sh must fail when PAYTABS_SERVER_KEY is empty after hydration."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _deploy_payments_text() -> str:
    path = Path(__file__).resolve().parents[3] / "scripts" / "deploy-payments.sh"
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def test_deploy_payments_documents_placeholder_keys_satisfy_guard() -> None:
    text = _deploy_payments_text()
    assert "placeholder" in text.lower()
    assert "streammycourse/paytabs/" in text


def test_deploy_payments_passes_billing_fulfillment_alert_email() -> None:
    text = _deploy_payments_text()
    assert "BILLING_FULFILLMENT_ALERT_EMAIL" in text
    assert "BillingFulfillmentAlertEmail=${BILLING_FULFILLMENT_ALERT_EMAIL}" in text


def test_deploy_payments_exits_when_server_key_empty_after_hydration() -> None:
    text = _deploy_payments_text()
    hydration = text.index("# Hydrate inline CFN params")
    guard = text.index("PAYTABS_SERVER_KEY is empty", hydration)
    assert "exit 1" in text[guard : guard + 400]


def test_deploy_payments_server_key_guard_fails_in_subprocess() -> None:
    script = Path(__file__).resolve().parents[3] / "scripts" / "deploy-payments.sh"
    snippet = """
set -euo pipefail
ENV=dev
PAYTABS_SERVER_KEY=""
PAYTABS_PROFILE_ID=""
if [[ -z "${PAYTABS_SERVER_KEY}" ]]; then
  echo "PAYTABS_SERVER_KEY is empty after hydration; set GitHub secret or SM streammycourse/paytabs/${ENV} with non-empty server_key" >&2
  exit 1
fi
"""
    result = subprocess.run(
        ["bash", "-c", snippet],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "PAYTABS_SERVER_KEY is empty" in result.stderr
