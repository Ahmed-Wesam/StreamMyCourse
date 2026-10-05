"""RS-14: research team API Gateway methods, public requirements, deployment V44."""

from __future__ import annotations

from pathlib import Path

_API_STACK = (
    Path(__file__).resolve().parents[3] / "infrastructure" / "templates" / "api-stack.yaml"
)

_COGNITO_METHODS = (
    "MeResearchTeamGetMethod",
    "MeResearchTeamApplicationsPostMethod",
    "ResearchTeamApplicationsGetMethod",
    "ResearchTeamApplicationIdGetMethod",
    "ResearchTeamApplicationIdPatchMethod",
    "ResearchTeamAllowReapplyPostMethod",
    "CourseResearchTeamRequirementPutMethod",
    "CourseResearchTeamRequirementGetMethod",
)

_PUBLIC_GET_METHODS = ("ResearchTeamRequirementsGetMethod",)

_OPTIONS_METHODS = (
    "ResearchTeamRequirementsOptionsMethod",
    "ResearchTeamApplicationsOptionsMethod",
    "ResearchTeamApplicationIdOptionsMethod",
    "ResearchTeamAllowReapplyOptionsMethod",
    "MeResearchTeamOptionsMethod",
    "MeResearchTeamApplicationsOptionsMethod",
    "CourseResearchTeamRequirementOptionsMethod",
)

_DEPLOYMENT_METHODS = _COGNITO_METHODS + _PUBLIC_GET_METHODS + _OPTIONS_METHODS


def test_rs14_research_team_cognito_and_public_methods() -> None:
    text = _API_STACK.read_text(encoding="utf-8")
    for logical_id in _COGNITO_METHODS:
        block = text.split(f"{logical_id}:", 1)[1].split("\n\n", 1)[0]
        assert "AuthorizationType: COGNITO_USER_POOLS" in block, logical_id
        assert "CatalogApiTokenAuthorizer" in block, logical_id
    for logical_id in _PUBLIC_GET_METHODS:
        block = text.split(f"{logical_id}:", 1)[1].split("\n\n", 1)[0]
        assert "AuthorizationType: NONE" in block, logical_id
        assert "HttpMethod: GET" in block, logical_id
    for logical_id in _OPTIONS_METHODS:
        block = text.split(f"{logical_id}:", 1)[1].split("\n\n", 1)[0]
        assert "AuthorizationType: NONE" in block, logical_id
        assert "HttpMethod: OPTIONS" in block, logical_id


def test_rs14_research_team_paths_present() -> None:
    text = _API_STACK.read_text(encoding="utf-8")
    assert "ResearchTeamResource:" in text
    assert "ResearchTeamRequirementsResource:" in text
    assert "ResearchTeamApplicationsResource:" in text
    assert "ResearchTeamApplicationIdResource:" in text
    assert "ResearchTeamAllowReapplyResource:" in text
    assert "MeResearchTeamResource:" in text
    assert "MeResearchTeamApplicationsResource:" in text
    assert "CourseResearchTeamRequirementResource:" in text
    assert "PathPart: research-team" in text
    assert "PathPart: research-team-requirement" in text
    assert "PathPart: allow-reapply" in text


def test_rs14_research_team_methods_in_deployment_v44() -> None:
    text = _API_STACK.read_text(encoding="utf-8")
    assert "CatalogApiDeploymentV44:" in text
    assert "CatalogApiDeploymentV43:" in text
    deployment_block = text.split("CatalogApiDeploymentV44:", 1)[1].split(
        "CatalogApiStage:", 1
    )[0]
    for logical_id in _DEPLOYMENT_METHODS:
        assert logical_id in deployment_block, logical_id
    assert "DeploymentId: !Ref CatalogApiDeploymentV46" in text
    stage_block = text.split("CatalogApiStage:", 1)[1].split("\n\n", 1)[0]
    assert "CatalogApiDeploymentV43" not in stage_block
