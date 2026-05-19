"""W6-P1c: payments-stack catalog invoke IAM and billing edge env vars."""

from __future__ import annotations

from pathlib import Path


def _payments_stack_text() -> str:
    path = Path(__file__).resolve().parents[2] / "infrastructure" / "templates" / "payments-stack.yaml"
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def test_payments_stack_catalog_lambda_arn_parameter() -> None:
    text = _payments_stack_text()
    assert "CatalogLambdaArn:" in text
    assert "Type: String" in text


def test_payments_stack_billing_edge_env_catalog_and_return_urls() -> None:
    text = _payments_stack_text()
    start = text.index("  BillingEdge:")
    end = text.index("  BillingFulfillmentRole:", start)
    block = text[start:end]
    assert "CATALOG_LAMBDA_ARN:" in block
    assert "SUBSCRIPTION_PLAN_ID:" in block
    assert "BILLING_RETURN_SUCCESS_URL:" in block
    assert "BILLING_RETURN_CANCEL_URL:" in block
    assert "CatalogLambdaArn" in block


def test_payments_stack_billing_edge_role_can_invoke_catalog() -> None:
    text = _payments_stack_text()
    assert "BillingEdgeCatalogInvokePolicy:" in text
    start = text.index("  BillingEdgeCatalogInvokePolicy:")
    end = text.index("  BillingEdge:", start)
    block = text[start:end]
    assert "HasCatalogLambdaArn" in block
    assert "lambda:InvokeFunction" in block
    assert "CatalogLambdaArn" in block
