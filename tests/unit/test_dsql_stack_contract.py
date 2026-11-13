"""DSQL-1 S1 — Aurora DSQL cluster template and GitHub deploy-role IAM (TDD Red → Green)."""

from __future__ import annotations

import re
from pathlib import Path

DSQL_CLUSTER_ACTIONS = (
    "dsql:CreateCluster",
    "dsql:GetCluster",
    "dsql:UpdateCluster",
    "dsql:DeleteCluster",
    "dsql:ListClusters",
    "dsql:TagResource",
    "dsql:UntagResource",
    "dsql:ListTagsForResource",
    "dsql:GetClusterPolicy",
    "dsql:PutClusterPolicy",
    "dsql:DeleteClusterPolicy",
    "dsql:DbConnectAdmin",
    "dsql:DbConnect",
)

DSQL_CLUSTER_RESOURCE = (
    "arn:aws:dsql:eu-west-1:${AWS::AccountId}:cluster/*"
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _template_path(name: str) -> Path:
    return _repo_root() / "infrastructure" / "templates" / name


def _read_template(name: str) -> str:
    path = _template_path(name)
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def _cluster_resource_block(text: str) -> str:
    """YAML block for the DSQL cluster resource (through deletion policies / properties)."""
    match = re.search(
        r"(?ms)^\s+\w+:\s*\n\s+Type:\s*AWS::DSQL::Cluster.*?(?=^\s+\w+:\s*\n\s+Type:|\nOutputs:)",
        text,
    )
    assert match, "AWS::DSQL::Cluster resource block not found"
    return match.group(0)


def test_dsql_stack_file_exists_and_uses_cluster_type() -> None:
    text = _read_template("dsql-stack.yaml")
    assert "AWS::DSQL::Cluster" in text


def test_dsql_stack_deletion_protection_enabled() -> None:
    block = _cluster_resource_block(_read_template("dsql-stack.yaml"))
    assert re.search(r"^\s+DeletionProtectionEnabled:\s+true\s*$", block, re.MULTILINE), (
        "Cluster must set DeletionProtectionEnabled: true"
    )


def test_dsql_stack_cluster_deletion_policies_retain() -> None:
    block = _cluster_resource_block(_read_template("dsql-stack.yaml"))
    assert re.search(r"^\s+DeletionPolicy:\s+Retain\s*$", block, re.MULTILINE)
    assert re.search(r"^\s+UpdateReplacePolicy:\s+Retain\s*$", block, re.MULTILINE)


def test_dsql_stack_exports_endpoint_identifier_resource_arn() -> None:
    text = _read_template("dsql-stack.yaml")
    for name in ("Endpoint", "Identifier", "ResourceArn"):
        assert re.search(rf"^\s+{name}:\s*$", text, re.MULTILINE), f"missing Outputs.{name}"


def test_dsql_stack_no_multi_region_or_cluster_policy_document() -> None:
    text = _read_template("dsql-stack.yaml")
    assert "MultiRegionProperties" not in text
    assert "PolicyDocument:" not in text


def test_dsql_stack_tags_project_and_name() -> None:
    block = _cluster_resource_block(_read_template("dsql-stack.yaml"))
    assert re.search(r"Key:\s+Project\s*\n\s+Value:\s+StreamMyCourse", block)
    assert re.search(r"Key:\s+Name\s*\n\s+Value:\s+streammycourse-prod", block)


def test_github_deploy_role_dsql_cluster_management_and_connect() -> None:
    text = _read_template("github-deploy-role-stack.yaml")
    for action in DSQL_CLUSTER_ACTIONS:
        assert action in text, f"deploy role missing IAM action {action!r}"
    assert DSQL_CLUSTER_RESOURCE in text


def test_github_deploy_role_dsql_service_linked_role() -> None:
    text = _read_template("github-deploy-role-stack.yaml")
    assert "iam:CreateServiceLinkedRole" in text
    dsql_slr = re.search(
        r"(?ms)Sid:\s*IamDsqlServiceLinkedRole.*?iam:AWSServiceName:\s*dsql\.amazonaws\.com",
        text,
    )
    assert dsql_slr, (
        "expected Sid IamDsqlServiceLinkedRole with iam:AWSServiceName dsql.amazonaws.com"
    )
