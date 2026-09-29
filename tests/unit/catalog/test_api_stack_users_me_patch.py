"""RS-6 Slice A: PATCH /users/me API Gateway method in api-stack."""

from __future__ import annotations

from pathlib import Path

_API_STACK = (
    Path(__file__).resolve().parents[3] / "infrastructure" / "templates" / "api-stack.yaml"
)


def test_api_stack_declares_users_me_patch_method() -> None:
    text = _API_STACK.read_text(encoding="utf-8")
    assert "UsersMePatchMethod:" in text
    patch_block = text.split("UsersMePatchMethod:", 1)[1].split("UsersMeOptionsMethod:", 1)[0]
    assert "HttpMethod: PATCH" in patch_block
    assert "AuthorizationType: COGNITO_USER_POOLS" in patch_block
    assert "CatalogApiTokenAuthorizer" in patch_block


def test_users_me_patch_method_is_in_catalog_api_deployment() -> None:
    """Stage export must include PATCH /users/me (DependsOn on deployment resource)."""
    text = _API_STACK.read_text(encoding="utf-8")
    deployment_block = text.split("CatalogApiDeploymentV43:", 1)[1].split(
        "CatalogApiStage:", 1
    )[0]
    assert "UsersMePatchMethod" in deployment_block
    assert "DeploymentId: !Ref CatalogApiDeploymentV43" in text
