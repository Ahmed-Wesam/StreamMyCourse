"""W7-P7: payments-stack IAM for WS7 manage catalog invokes (verify-only).

WS7 billing edge invokes catalog internal events such as ``billing.cancel_at_period_end``
via the same ``CATALOG_LAMBDA_ARN`` / ``lambda:InvokeFunction``
path as ``billing.checkout`` (see ``billing_edge/catalog_invoke.py``). IAM is granted
on the catalog Lambda **ARN**, not per internal event name — no separate stack policy
is required for manage vs checkout.

If these tests pass against the current ``payments-stack.yaml``, **no YAML change**
is needed for W7-P7.
"""

from __future__ import annotations

import re
from pathlib import Path


def _payments_stack_text() -> str:
    path = (
        Path(__file__).resolve().parents[2]
        / "infrastructure"
        / "templates"
        / "payments-stack.yaml"
    )
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def _billing_edge_catalog_invoke_policy_block(text: str) -> str:
    assert "BillingEdgeCatalogInvokePolicy:" in text
    start = text.index("  BillingEdgeCatalogInvokePolicy:")
    end = text.index("  BillingEdge:", start)
    return text[start:end]


def test_billing_edge_role_can_invoke_catalog_lambda_arn() -> None:
    """BillingEdgeRole receives lambda:InvokeFunction on CatalogLambdaArn."""
    text = _payments_stack_text()
    block = _billing_edge_catalog_invoke_policy_block(text)
    assert "BillingEdgeRole" in block
    assert "HasCatalogLambdaArn" in block
    assert "lambda:InvokeFunction" in block
    assert "Resource: !Ref CatalogLambdaArn" in block


def test_single_catalog_invoke_policy_for_all_internal_billing_events() -> None:
    """Manage and checkout share one catalog ARN policy — no event-specific IAM."""
    text = _payments_stack_text()
    assert text.count("BillingEdgeCatalogInvokePolicy:") == 1
    block = _billing_edge_catalog_invoke_policy_block(text)
    assert block.count("lambda:InvokeFunction") == 1
    assert block.count("!Ref CatalogLambdaArn") == 1

    # IAM must not branch on internal event names (those live in invoke payload only).
    iam_tail = text.split("BillingEdgeCatalogInvokePolicy:")[1]
    assert "billing.checkout" not in iam_tail
    assert "billing.cancel_at_period_end" not in iam_tail

    # No second catalog invoke policy on BillingEdgeRole.
    role_attach_pattern = re.compile(
        r"Roles:\s*\n\s*-\s*!Ref\s+BillingEdgeRole",
        re.MULTILINE,
    )
    catalog_invoke_role_attachments = [
        m.start()
        for m in role_attach_pattern.finditer(text)
        if "lambda:InvokeFunction" in text[max(0, m.start() - 400) : m.start() + 200]
    ]
    assert len(catalog_invoke_role_attachments) == 1
