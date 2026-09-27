"""Contract tests: RS-5 purchase checkout routes on api-stack."""

from __future__ import annotations

from pathlib import Path


def _api_stack_text() -> str:
    path = (
        Path(__file__).resolve().parents[2]
        / "infrastructure"
        / "templates"
        / "api-stack.yaml"
    )
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def test_api_stack_no_legacy_subscription_manage_routes() -> None:
    text = _api_stack_text()
    assert "BillingSubscriptionResource:" not in text
    assert "BillingCancelSubscriptionResource:" not in text
    assert "PathPart: subscription" not in text
    assert "PathPart: cancel-subscription" not in text


def test_api_stack_billing_checkout_on_edge() -> None:
    text = _api_stack_text()
    assert "BillingCheckoutSessionResource:" in text
    post_block = text.split("BillingCheckoutSessionPostMethod:")[1].split(
        "BillingCheckoutSessionOptionsMethod:"
    )[0]
    assert "HttpMethod: POST" in post_block
    assert "${BillingEdgeLambdaArn}/invocations" in post_block


def test_api_stack_billing_manage_deployment_v37() -> None:
    text = _api_stack_text()
    assert "CatalogApiDeploymentV37:" in text
    assert "CatalogApiDeploymentV36:" not in text
    deployment_block = text.split("CatalogApiDeploymentV37:")[1].split("CatalogApiStage:")[0]
    for legacy in (
        "BillingSubscriptionGetMethod",
        "BillingSubscriptionOptionsMethod",
        "BillingCancelSubscriptionPostMethod",
        "BillingCancelSubscriptionOptionsMethod",
    ):
        assert legacy not in deployment_block
    for required in (
        "BillingPurchasesGetMethod",
        "BillingBundleGetMethod",
        "BillingBundlePatchMethod",
        "BillingCoursesCourseIdPricePatchMethod",
    ):
        assert required in deployment_block
    assert "DeploymentId: !Ref CatalogApiDeploymentV37" in text
