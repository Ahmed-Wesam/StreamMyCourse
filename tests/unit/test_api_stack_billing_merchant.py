"""Contract tests: GET /billing/merchant/status on catalog Lambda (WS4 Phase D)."""

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


def test_api_stack_billing_merchant_status_route_on_catalog() -> None:
    text = _api_stack_text()
    assert "BillingMerchantStatusGetMethod:" in text
    assert "BillingMerchantStatusOptionsMethod:" in text
    assert "PathPart: merchant" in text
    assert "PathPart: status" in text
    assert "BillingMerchantStatusResource:" in text

    get_block = text[text.index("BillingMerchantStatusGetMethod:") : text.index(
        "BillingMerchantStatusOptionsMethod:"
    )]
    assert "AuthorizationType: COGNITO_USER_POOLS" in get_block
    assert "AuthorizerId: !Ref CatalogApiTokenAuthorizer" in get_block
    assert "${CatalogLambda.Arn}/invocations" in get_block
    assert "${BillingEdgeLambdaArn}/invocations" not in get_block

    assert "BILLING_TEACHER_SUB: !Ref BillingTeacherSub" in text
    assert "DEPLOYMENT_ENVIRONMENT: !Ref Environment" in text
    assert "BillingTeacherSub:" in text

    assert "CatalogApiDeploymentV30:" in text
    deployment_block = text.split("CatalogApiDeploymentV30:")[1].split("CatalogApiStage:")[0]
    # Conditional billing methods must not be in DependsOn (cfn-lint E3005).
    assert "BillingMerchantStatusGetMethod" not in deployment_block
    assert "BillingMerchantStatusOptionsMethod" not in deployment_block
    assert "DeploymentId: !Ref CatalogApiDeploymentV30" in text
