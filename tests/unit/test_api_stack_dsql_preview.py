"""DSQL-1 S5 — preview API stack contract (UseDsql / name token / conditional VPC + DB)."""

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


def test_use_dsql_and_use_rds_conditions() -> None:
    cond = _conditions_block(_api_stack_text())
    assert re.search(r"^\s+UseDsql:\s*", cond, re.MULTILINE)
    assert re.search(r"^\s+UseRds:\s*", cond, re.MULTILINE)
    assert re.search(r"^\s+HasResourceNameSuffix:\s*", cond, re.MULTILINE)
    assert "DsqlEndpoint" in cond
    assert "!Condition UseDsql" in cond


def test_empty_suffix_name_token_resolves_to_environment() -> None:
    text = _api_stack_text()
    assert "HasResourceNameSuffix" in text
    assert re.search(
        r"NameToken:\s*!If\s*\n\s*-\s*HasResourceNameSuffix\s*\n\s*-\s*!Ref ResourceNameSuffix\s*\n\s*-\s*!Ref Environment",
        text,
    ), "NameToken must use ResourceNameSuffix when set, else Environment"
    # Prod path: empty suffix still produces *-${Environment} via the name token.
    assert re.search(
        r"StreamMyCourse-CatalogLambdaRole-\$\{NameToken\}",
        text,
    )
    assert re.search(
        r"StreamMyCourse-Catalog-\$\{NameToken\}",
        text,
    )


def test_vpc_config_and_rds_imports_gated_on_use_rds() -> None:
    text = _api_stack_text()
    assert re.search(
        r"VpcConfig:\s*!If\s*\n\s*-\s*UseRds",
        text,
    ), "VpcConfig must be conditional on UseRds"
    assert re.search(
        r"DB_HOST:\s*!If\s*\n\s*-\s*UseRds\s*\n\s*-\s*!ImportValue",
        text,
    ), "DB_HOST ImportValue must be inside UseRds"
    assert re.search(
        r"PolicyName:\s*LambdaVpcEni",
        text,
    )
    vpc_policy = re.search(
        r"PolicyName:\s*LambdaVpcEni.*?(?=PolicyName:|Tags:)",
        text,
        re.DOTALL,
    )
    assert vpc_policy and "!If" in vpc_policy.group(0) and "UseRds" in vpc_policy.group(0)


def test_dsql_branch_sets_dsql_endpoint_not_db_secret() -> None:
    text = _api_stack_text()
    assert re.search(
        r"DSQL_ENDPOINT:\s*!If\s*\n\s*-\s*UseDsql",
        text,
    )
    assert re.search(
        r"DSQL_USER:\s*!If\s*\n\s*-\s*UseDsql",
        text,
    )
    assert "smc_app" in text
    db_secret = re.search(
        r"DB_SECRET_ARN:\s*!If\s*\n\s*-\s*UseRds",
        text,
    )
    assert db_secret, "DB_SECRET_ARN must only be set on UseRds"
    assert re.search(
        r"dsql:DbConnect",
        text,
    )
    assert re.search(
        r"DsqlClusterArn",
        text,
    )


def test_db_host_port_name_also_conditional_on_use_rds() -> None:
    text = _api_stack_text()
    for key in ("DB_PORT", "DB_NAME"):
        assert re.search(
            rf"{key}:\s*!If\s*\n\s*-\s*UseRds\s*\n\s*-\s*!ImportValue",
            text,
        ), f"{key} must ImportValue only under UseRds"
