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


def test_api_stack_billing_cancel_on_edge_no_reactivate() -> None:
    text = _api_stack_text()
    assert "BillingCancelSubscriptionResource:" in text
    assert "PathPart: cancel-subscription" in text
    assert "BillingReactivateSubscriptionResource:" not in text
    assert "PathPart: reactivate-subscription" not in text

    post_block = text[
        text.index("BillingCancelSubscriptionPostMethod:")
        : text.index("BillingCancelSubscriptionOptionsMethod:")
    ]
    assert "HttpMethod: POST" in post_block
    assert "AuthorizationType: COGNITO_USER_POOLS" in post_block
    assert "AuthorizerId: !Ref CatalogApiTokenAuthorizer" in post_block
    assert "${BillingEdgeLambdaArn}/invocations" in post_block

    options_block = text.split("BillingCancelSubscriptionOptionsMethod:")[1].split(
        "WebhooksPaytabsPostMethod:"
    )[0]
    assert "HttpMethod: OPTIONS" in options_block
    assert "AuthorizationType: NONE" in options_block
    assert "${BillingEdgeLambdaArn}/invocations" in options_block


def test_api_stack_billing_manage_deployment_v31() -> None:
    text = _api_stack_text()
    assert "CatalogApiDeploymentV31:" in text
    assert "CatalogApiDeploymentV30:" not in text
    deployment_block = text.split("CatalogApiDeploymentV31:")[1].split("CatalogApiStage:")[0]
    # Conditional billing methods must not be in DependsOn (cfn-lint E3005).
    for name in (
        "BillingSubscriptionGetMethod",
        "BillingSubscriptionOptionsMethod",
        "BillingCancelSubscriptionPostMethod",
        "BillingCancelSubscriptionOptionsMethod",
    ):
        assert name not in deployment_block
    assert "DeploymentId: !Ref CatalogApiDeploymentV31" in text
