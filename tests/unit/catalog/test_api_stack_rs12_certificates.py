"""RS-12: certificates API Gateway methods, public verify, deployment V43."""

from __future__ import annotations

from pathlib import Path

_API_STACK = (
    Path(__file__).resolve().parents[3] / "infrastructure" / "templates" / "api-stack.yaml"
)

_COGNITO_METHODS = (
    "MeCertificatesGetMethod",
    "CourseCertificatesGetMethod",
    "CourseCertificateRevokePostMethod",
)

_PUBLIC_GET_METHODS = ("CertificatesCredentialIdGetMethod",)

_OPTIONS_METHODS = (
    "MeCertificatesOptionsMethod",
    "CertificatesCredentialIdOptionsMethod",
    "CourseCertificatesOptionsMethod",
    "CourseCertificateRevokeOptionsMethod",
)

_DEPLOYMENT_METHODS = _COGNITO_METHODS + _PUBLIC_GET_METHODS + _OPTIONS_METHODS


def test_rs12_certificate_cognito_and_public_methods() -> None:
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


def test_rs12_certificate_paths_present() -> None:
    text = _API_STACK.read_text(encoding="utf-8")
    assert "PathPart: me" in text
    assert "MeCertificatesResource:" in text
    assert "CertificatesResource:" in text
    assert "CertificatesCredentialIdResource:" in text
    assert "CourseCertificatesResource:" in text
    assert "CourseCertificateIdResource:" in text
    assert "CourseCertificateRevokeResource:" in text
    assert "PathPart: revoke" in text


def test_rs12_certificate_methods_in_deployment_v43() -> None:
    text = _API_STACK.read_text(encoding="utf-8")
    assert "CatalogApiDeploymentV43:" in text
    deployment_block = text.split("CatalogApiDeploymentV43:", 1)[1].split(
        "CatalogApiStage:", 1
    )[0]
    for logical_id in _DEPLOYMENT_METHODS:
        assert logical_id in deployment_block, logical_id
    assert "DeploymentId: !Ref CatalogApiDeploymentV43" in text
    stage_block = text.split("CatalogApiStage:", 1)[1].split("\n\n", 1)[0]
    assert "CatalogApiDeploymentV42" not in stage_block
