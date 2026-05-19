"""W6-P4 — subscribe checkout gate order in handler source."""

from __future__ import annotations

import re
from pathlib import Path


def _handler_source() -> str:
    path = (
        Path(__file__).resolve().parents[3]
        / "infrastructure"
        / "lambda"
        / "billing_edge"
        / "handler.py"
    )
    return path.read_text(encoding="utf-8")


def test_handler_checkout_gate_order_billing_unconfigured_before_catalog() -> None:
    source = _handler_source()
    checkout_fn = source[source.find("def _handle_checkout") : source.find("def _webhook_signature_header")]
    unconfigured = checkout_fn.find("billing_unconfigured")
    catalog_invoke = checkout_fn.find("precheck = _invoke_billing_checkout")
    assert unconfigured != -1
    assert catalog_invoke != -1
    assert unconfigured < catalog_invoke


def test_handler_checkout_gate_order_already_subscribed_before_in_progress() -> None:
    source = _handler_source()
    checkout_fn = source[source.find("def _handle_checkout") : source.find("def _webhook_signature_header")]
    already = checkout_fn.find("already_subscribed")
    in_progress = checkout_fn.find("checkout_in_progress")
    create_session = checkout_fn.find("create_subscribe_session")
    assert already != -1
    assert in_progress != -1
    assert create_session != -1
    assert already < in_progress < create_session
    assert "reactivation_required" not in checkout_fn


def test_handler_checkout_gate_order_catalog_before_paytabs() -> None:
    source = _handler_source()
    checkout_fn = source[source.find("def _handle_checkout") : source.find("def _webhook_signature_header")]
    catalog_invoke = checkout_fn.find("precheck = _invoke_billing_checkout")
    create_session = checkout_fn.find("create_subscribe_session")
    assert catalog_invoke < create_session


def test_handler_emits_subscribe_contract_error_codes() -> None:
    source = _handler_source()
    for code in (
        "billing_unconfigured",
        "already_subscribed",
        "checkout_in_progress",
    ):
        assert code in source
    assert "reactivation_required" not in source
    assert re.search(
        r'_error_response\s*\(\s*503\s*,\s*["\']billing_unconfigured["\']',
        source,
    )
    assert re.search(
        r'_error_response\s*\(\s*409\s*,\s*["\']already_subscribed["\']',
        source,
    )
    assert re.search(
        r'_error_response\s*\(\s*409\s*,\s*["\']checkout_in_progress["\']',
        source,
    )
