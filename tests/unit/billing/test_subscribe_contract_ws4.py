"""W4-P5 — subscribe contract: no payout gate on billing_edge checkout (WS4 operator Q4).

Normative contract: plans/billing/subscribe-contract-v1.md
Regression: any ``payout_not_ready`` / ``PAYOUT_READY`` on the edge checkout path must fail here.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Workstream 6 implements the check; WS4 documents the response shape only.
ALREADY_OWNED_STATUS = 409
ALREADY_OWNED_CODE = "already_owned"

_FORBIDDEN_HANDLER_TOKENS = ("payout_not_ready", "PAYOUT_READY")
_FORBIDDEN_EDGE_CONFIG_TOKENS = ("PAYOUT_READY",)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _billing_edge_dir() -> Path:
    return _repo_root() / "infrastructure" / "lambda" / "billing_edge"


def _read_billing_edge_source(filename: str) -> str:
    path = _billing_edge_dir() / filename
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def _assert_no_forbidden_tokens(source: str, *, path_label: str, tokens: tuple[str, ...]) -> None:
    hits = [token for token in tokens if token in source]
    assert not hits, (
        f"{path_label} must not reference payout subscribe gates {hits!r} "
        f"(see plans/billing/subscribe-contract-v1.md)"
    )


def test_handler_source_has_no_payout_subscribe_gates() -> None:
    """Checkout handler must not gate on payout_ready (WS4 Q4)."""
    source = _read_billing_edge_source("handler.py")
    _assert_no_forbidden_tokens(
        source,
        path_label="billing_edge/handler.py",
        tokens=_FORBIDDEN_HANDLER_TOKENS,
    )


def test_edge_config_has_no_payout_ready_env() -> None:
    """Edge config must not read PAYOUT_READY from the environment (v1)."""
    source = _read_billing_edge_source("edge_config.py")
    _assert_no_forbidden_tokens(
        source,
        path_label="billing_edge/edge_config.py",
        tokens=_FORBIDDEN_EDGE_CONFIG_TOKENS,
    )


def test_billing_edge_python_tree_has_no_payout_not_ready() -> None:
    """Regression: no payout_not_ready anywhere under billing_edge/."""
    edge_dir = _billing_edge_dir()
    offenders: list[str] = []
    for path in sorted(edge_dir.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "payout_not_ready" in text:
            offenders.append(str(path.relative_to(_repo_root())))
    assert not offenders, (
        "billing_edge must not reference payout_not_ready; offenders: "
        + ", ".join(offenders)
    )


@pytest.mark.parametrize(
    ("status", "code", "message"),
    [
        (
            ALREADY_OWNED_STATUS,
            ALREADY_OWNED_CODE,
            "You already own this course or bundle",
        ),
    ],
)
def test_already_owned_contract_shape(
    status: int,
    code: str,
    message: str,
) -> None:
    """RS-5: duplicate purchase checkout response."""
    assert status == 409
    assert code == "already_owned"
    assert message


def test_handler_emits_already_owned_gate() -> None:
    """RS-5: handler returns 409 already_owned when catalog blocks."""
    source = _read_billing_edge_source("handler.py")
    assert "already_owned" in source
    assert re.search(
        r'_manage_conflict_response\s*\(\s*["\']already_owned["\']',
        source,
    )


def test_handler_checkout_errors_match_subscribe_contract_gates() -> None:
    """Handler exposes billing_unconfigured (503) and duplicate-sub gates before redirect."""
    source = _read_billing_edge_source("handler.py")
    assert '"billing_unconfigured"' in source or "'billing_unconfigured'" in source
    assert re.search(r'_error_response\s*\(\s*503\s*,\s*["\']billing_unconfigured["\']', source)
    assert "reactivation_required" not in source

