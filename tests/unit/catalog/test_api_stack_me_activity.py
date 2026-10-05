"""RS-16: GET /me/activity API Gateway method in api-stack."""

from __future__ import annotations

from pathlib import Path

_API_STACK = (
    Path(__file__).resolve().parents[3] / "infrastructure" / "templates" / "api-stack.yaml"
)


def test_api_stack_declares_me_activity_get_method() -> None:
    text = _API_STACK.read_text(encoding="utf-8")
    assert "MeActivityResource:" in text
    resource = text.split("MeActivityResource:", 1)[1].split("MeActivityGetMethod:", 1)[0]
    assert "PathPart: activity" in resource
    assert "ParentId: !Ref MeResource" in resource

    assert "MeActivityGetMethod:" in text
    get_block = text.split("MeActivityGetMethod:", 1)[1].split("MeActivityOptionsMethod:", 1)[0]
    assert "HttpMethod: GET" in get_block
    assert "AuthorizationType: COGNITO_USER_POOLS" in get_block
    assert "CatalogApiTokenAuthorizer" in get_block


def test_me_activity_get_method_is_in_catalog_api_deployment() -> None:
    """Stage export must include GET /me/activity (DependsOn on deployment resource)."""
    text = _API_STACK.read_text(encoding="utf-8")
    deployment_block = text.split("CatalogApiDeploymentV45:", 1)[1].split(
        "CatalogApiStage:", 1
    )[0]
    assert "MeActivityGetMethod" in deployment_block
    assert "MeActivityOptionsMethod" in deployment_block
    assert "DeploymentId: !Ref CatalogApiDeploymentV45" in text
