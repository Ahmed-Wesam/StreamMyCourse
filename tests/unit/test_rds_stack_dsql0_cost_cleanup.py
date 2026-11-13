"""DSQL-0 Slice 2 — RDS stack cost cleanup contract (TDD Red → Green).

Assert rds-stack.yaml drops the CloudWatch Logs VPC interface endpoint and sets
backup retention to 1 day while keeping required endpoints and data protection.
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


def _db_instance_block(text: str) -> str:
    start = text.index("  DbInstance:")
    end = text.index("\n  # -------------------------- VPC Endpoints", start)
    return text[start:end]


def test_rds_stack_has_no_logs_vpc_endpoint_service_name() -> None:
    text = _rds_stack_text()
    assert "com.amazonaws.${AWS::Region}.logs" not in text, (
        "Logs VPC interface endpoint must be removed (DSQL-0 cost cleanup)"
    )


def test_rds_stack_backup_retention_period_is_one() -> None:
    block = _db_instance_block(_rds_stack_text())
    match = re.search(r"^\s+BackupRetentionPeriod:\s+(\d+)\s*$", block, re.MULTILINE)
    assert match, "DbInstance.BackupRetentionPeriod not found"
    assert match.group(1) == "1", (
        f"BackupRetentionPeriod must be 1 (operator override), got {match.group(1)!r}"
    )


def test_rds_stack_keeps_required_vpc_endpoint_services() -> None:
    text = _rds_stack_text()
    required = (
        "com.amazonaws.${AWS::Region}.secretsmanager",
        "com.amazonaws.${AWS::Region}.sqs",
        "com.amazonaws.${AWS::Region}.s3",
        "com.amazonaws.${AWS::Region}.dynamodb",
    )
    for service in required:
        assert service in text, f"expected VPC endpoint service {service!r} to remain"


def test_rds_stack_db_instance_deletion_protection_true() -> None:
    block = _db_instance_block(_rds_stack_text())
    assert re.search(r"^\s+DeletionProtection:\s+true\s*$", block, re.MULTILINE), (
        "DbInstance.DeletionProtection must be true"
    )


def test_rds_stack_db_instance_deletion_policy_snapshot() -> None:
    block = _db_instance_block(_rds_stack_text())
    assert re.search(r"^\s+DeletionPolicy:\s+Snapshot\s*$", block, re.MULTILINE), (
        "DbInstance.DeletionPolicy must be Snapshot"
    )
