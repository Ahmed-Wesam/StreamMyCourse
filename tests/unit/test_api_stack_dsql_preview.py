"""DSQL-1 / DSQL-9 — api stack preview lane (name token + DSQL env, no RDS)."""

from __future__ import annotations

import re
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


def _parameters_block(text: str) -> str:
    match = re.search(r"(?ms)^Parameters:\n(.*?)^Conditions:", text)
    assert match, "Parameters section not found"
    return match.group(1)


def _conditions_block(text: str) -> str:
    match = re.search(r"(?ms)^Conditions:\n(.*?)^Resources:", text)
    assert match, "Conditions section not found"
    return match.group(1)


def test_dsql_preview_parameters_exist_with_empty_defaults() -> None:
    params = _parameters_block(_api_stack_text())
    for name in ("DsqlEndpoint", "DsqlClusterArn", "ResourceNameSuffix"):
        assert re.search(rf"^\s+{name}:\s*$", params, re.MULTILINE), f"missing Parameters.{name}"
        section = re.search(rf"(?ms)^\s+{name}:\s*\n(.*?)(?=^\s+\w+:\s*$|\Z)", params)
        assert section, f"could not parse Parameters.{name}"
        assert re.search(r"^\s+Default:\s+''\s*$", section.group(1), re.MULTILINE), (
            f"Parameters.{name} must default to empty string"
        )


def test_no_use_rds_or_use_dsql_conditions() -> None:
    cond = _conditions_block(_api_stack_text())
    assert re.search(r"^\s+HasResourceNameSuffix:\s*", cond, re.MULTILINE)
    assert "UseDsql" not in cond
    assert "UseRds" not in cond


def test_empty_suffix_name_token_resolves_to_environment() -> None:
    text = _api_stack_text()
    assert "HasResourceNameSuffix" in text
    assert re.search(
        r"NameToken:\s*!If\s*\n\s*-\s*HasResourceNameSuffix\s*\n\s*-\s*!Ref ResourceNameSuffix\s*\n\s*-\s*!Ref Environment",
        text,
    ), "NameToken must use ResourceNameSuffix when set, else Environment"
    assert re.search(
        r"StreamMyCourse-CatalogLambdaRole-\$\{NameToken\}",
        text,
    )
    assert re.search(
        r"StreamMyCourse-Catalog-\$\{NameToken\}",
        text,
    )


def test_catalog_sets_dsql_env_unconditionally() -> None:
    text = _api_stack_text()
    assert "VpcConfig" not in text
    assert "RdsStackName" not in text
    assert re.search(
        r"DSQL_ENDPOINT:\s*!Ref DsqlEndpoint",
        text,
    )
    assert re.search(
        r"DSQL_USER:\s*smc_app",
        text,
    )
    assert re.search(
        r"dsql:DbConnect",
        text,
    )
    assert "DsqlClusterArn" in text
