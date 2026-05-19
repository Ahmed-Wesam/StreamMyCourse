"""Contract tests: WS7 manage subscription routes on api-stack (W7-P6)."""

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


def test_api_stack_billing_subscription_get_on_catalog() -> None:
    text = _api_stack_text()
    assert "BillingSubscriptionResource:" in text
    assert "PathPart: subscription" in text
    assert "BillingSubscriptionGetMethod:" in text
    assert "BillingSubscriptionOptionsMethod:" in text

    get_block = text[text.index("BillingSubscriptionGetMethod:") : text.index(
        "BillingSubscriptionOptionsMethod:"
    )]
    assert "HttpMethod: GET" in get_block
    assert "AuthorizationType: COGNITO_USER_POOLS" in get_block
    assert "AuthorizerId: !Ref CatalogApiTokenAuthorizer" in get_block
    assert "${CatalogLambda.Arn}/invocations" in get_block
    assert "${BillingEdgeLambdaArn}/invocations" not in get_block


def test_api_stack_billing_cancel_and_reactivate_on_edge() -> None:
    text = _api_stack_text()
    assert "BillingCancelSubscriptionResource:" in text
    assert "PathPart: cancel-subscription" in text
    assert "BillingReactivateSubscriptionResource:" in text
    assert "PathPart: reactivate-subscription" in text

    for post_name, options_name in (
        ("BillingCancelSubscriptionPostMethod", "BillingCancelSubscriptionOptionsMethod"),
        (
            "BillingReactivateSubscriptionPostMethod",
            "BillingReactivateSubscriptionOptionsMethod",
        ),
    ):
        assert f"{post_name}:" in text
        assert f"{options_name}:" in text
        post_block = text[text.index(f"{post_name}:") : text.index(f"{options_name}:")]
        assert "HttpMethod: POST" in post_block
        assert "AuthorizationType: COGNITO_USER_POOLS" in post_block
        assert "AuthorizerId: !Ref CatalogApiTokenAuthorizer" in post_block
        assert "${BillingEdgeLambdaArn}/invocations" in post_block

    options_blocks = [
        text.split("BillingCancelSubscriptionOptionsMethod:")[1].split(
            "BillingReactivateSubscriptionPostMethod:"
        )[0],
        text.split("BillingReactivateSubscriptionOptionsMethod:")[1].split(
            "WebhooksPaytabsPostMethod:"
        )[0],
    ]
    for block in options_blocks:
        assert "HttpMethod: OPTIONS" in block
        assert "AuthorizationType: NONE" in block
        assert "${BillingEdgeLambdaArn}/invocations" in block


def test_api_stack_billing_manage_deployment_v30() -> None:
    text = _api_stack_text()
    assert "CatalogApiDeploymentV30:" in text
    assert "CatalogApiDeploymentV29:" not in text
    deployment_block = text.split("CatalogApiDeploymentV30:")[1].split("CatalogApiStage:")[0]
    # Conditional billing methods must not be in DependsOn (cfn-lint E3005).
    for name in (
        "BillingSubscriptionGetMethod",
        "BillingSubscriptionOptionsMethod",
        "BillingCancelSubscriptionPostMethod",
        "BillingCancelSubscriptionOptionsMethod",
        "BillingReactivateSubscriptionPostMethod",
        "BillingReactivateSubscriptionOptionsMethod",
    ):
        assert name not in deployment_block
    assert "DeploymentId: !Ref CatalogApiDeploymentV30" in text
