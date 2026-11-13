"""Lambda SG must allow HTTPS egress to the regional S3 gateway prefix list.

VPC gateway endpoints route to public S3 CIDRs in the prefix list; restricting
egress to 10.0.0.0/16 alone hangs head_object and similar calls from the catalog Lambda.
"""

from __future__ import annotations

import re
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _rds_stack_text() -> str:
    path = _repo_root() / "infrastructure" / "templates" / "rds-stack.yaml"
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def test_rds_stack_maps_s3_gateway_prefix_list_per_region() -> None:
    text = _rds_stack_text()
    assert "Mappings:" in text
    assert re.search(
        r"^\s+eu-west-1:\s*$[\s\S]*?^\s+S3Gateway:\s+pl-6da54004\s*$",
        text,
        re.MULTILINE,
    ), "RegionPrefixLists must map eu-west-1 S3Gateway to pl-6da54004"


def _lambda_security_group_block(text: str) -> str:
    start = text.index("  LambdaSecurityGroup:")
    end = text.index("  RdsSecurityGroup:", start)
    return text[start:end]


def test_rds_stack_lambda_sg_egress_allows_s3_prefix_list_https() -> None:
    text = _rds_stack_text()
    block = _lambda_security_group_block(text)
    assert "DestinationPrefixListId" in block, (
        "LambdaSecurityGroup must egress to S3 via DestinationPrefixListId"
    )
    assert re.search(
        r"DestinationPrefixListId:\s*!FindInMap",
        block,
    ), "S3 egress must use FindInMap (RegionPrefixLists), not a bare prefix id"
    assert re.search(
        r"FromPort:\s+443\s*$\s*\n\s+ToPort:\s+443",
        block,
        re.MULTILINE,
    ), "S3 gateway egress must be tcp/443"
