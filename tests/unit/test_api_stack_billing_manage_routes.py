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


def _block_between(text: str, start_id: str, end_id: str) -> str:
    return text.split(f"{start_id}:", 1)[1].split(f"{end_id}:", 1)[0]


def test_api_stack_no_legacy_subscription_manage_routes() -> None:
    text = _api_stack_text()
    assert "BillingSubscriptionResource:" not in text
    assert "BillingCancelSubscriptionResource:" not in text
    assert "PathPart: subscription" not in text
    assert "PathPart: cancel-subscription" not in text


def test_api_stack_billing_checkout_on_edge() -> None:
    text = _api_stack_text()
    assert "BillingCheckoutSessionResource:" in text
    post_block = _block_between(
        text, "BillingCheckoutSessionPostMethod", "BillingCheckoutSessionOptionsMethod"
    )
    assert "HttpMethod: POST" in post_block
    assert "Condition: HasBillingEdgeLambdaArn" in post_block
    assert "${BillingEdgeLambdaArn}/invocations" in post_block


def test_api_stack_catalog_billing_methods_unconditional() -> None:
    """DSQL-5 S5: catalog-owned billing routes publish without payments edge."""
    text = _api_stack_text()
    pairs = (
        ("BillingBundleGetMethod", "BillingBundleOptionsMethod"),
        ("BillingBundleOptionsMethod", "BillingBundlePatchMethod"),
        ("BillingBundlePatchMethod", "BillingPurchasesGetMethod"),
        ("BillingPurchasesGetMethod", "BillingPurchasesOptionsMethod"),
        ("BillingPurchasesOptionsMethod", "BillingCoursesCourseIdPricePatchMethod"),
        (
            "BillingCoursesCourseIdPricePatchMethod",
            "BillingCoursesCourseIdPriceOptionsMethod",
        ),
        ("BillingCoursesCourseIdPriceOptionsMethod", "WebhooksHyperpayPostMethod"),
    )
    for start_id, end_id in pairs:
        block = _block_between(text, start_id, end_id)
        assert "Condition:" not in block, start_id

    for patch_id, end_id in (
        ("BillingBundleGetMethod", "BillingBundleOptionsMethod"),
        ("BillingPurchasesGetMethod", "BillingPurchasesOptionsMethod"),
        ("BillingBundlePatchMethod", "BillingPurchasesGetMethod"),
        (
            "BillingCoursesCourseIdPricePatchMethod",
            "BillingCoursesCourseIdPriceOptionsMethod",
        ),
    ):
        block = _block_between(text, patch_id, end_id)
        assert "Condition:" not in block, patch_id


def test_api_stack_billing_manage_deployment_v47() -> None:
    text = _api_stack_text()
    assert "CatalogApiDeploymentV46:" not in text
    assert "CatalogApiDeploymentV47:" in text
    deployment_block = text.split("CatalogApiDeploymentV47:", 1)[1].split(
        "CatalogApiStage:", 1
    )[0]
    for legacy in (
        "BillingSubscriptionGetMethod",
        "BillingSubscriptionOptionsMethod",
        "BillingCancelSubscriptionPostMethod",
        "BillingCancelSubscriptionOptionsMethod",
    ):
        assert legacy not in deployment_block
    for required_method in (
        "BillingBundleGetMethod",
        "BillingBundleOptionsMethod",
        "BillingBundlePatchMethod",
        "BillingPurchasesGetMethod",
        "BillingPurchasesOptionsMethod",
        "BillingCoursesCourseIdPricePatchMethod",
        "BillingCoursesCourseIdPriceOptionsMethod",
    ):
        assert required_method in deployment_block, required_method
    for required in (
        "BillingPurchasesResource:",
        "BillingBundleResource:",
        "BillingPurchasesGetMethod:",
        "BillingBundleGetMethod:",
    ):
        assert required in text
    assert "DeploymentId: !Ref CatalogApiDeploymentV47" in text
