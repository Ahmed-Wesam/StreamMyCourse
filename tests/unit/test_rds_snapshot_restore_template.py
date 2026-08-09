"""Contract tests: rds-stack.yaml snapshot restore wiring (TDD Red → Green).

Assert CloudFormation supports optional restore from DbSnapshotIdentifier before
implementing template changes in a later slice.
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


def _section(text: str, start_marker: str, end_markers: tuple[str, ...]) -> str:
    start = text.index(start_marker)
    end = len(text)
    for marker in end_markers:
        idx = text.find(marker, start + len(start_marker))
        if idx != -1:
            end = min(end, idx)
    return text[start:end]


def _parameters_block(text: str) -> str:
    return _section(text, "Parameters:", ("\nConditions:", "\nResources:"))


def _conditions_block(text: str) -> str:
    return _section(text, "Conditions:", ("\nResources:",))


def _db_instance_block(text: str) -> str:
    start = text.index("  DbInstance:")
    end = text.index("\n  # -------------------------- VPC Endpoints", start)
    return text[start:end]


def _parameter_block(params: str, name: str) -> str:
    match = re.search(rf"^\s{re.escape(name)}:\s*$", params, re.MULTILINE)
    assert match, f"parameter {name!r} not found under Parameters"
    start = match.end()
    next_param = re.search(r"^\n  [A-Za-z]", params[start:], re.MULTILINE)
    end = start + next_param.start() if next_param else len(params)
    return params[start:end]


def _restore_snapshot_condition_name(conditions: str) -> str:
    """Return a Conditions key that is true when DbSnapshotIdentifier is non-empty."""
    for match in re.finditer(r"^  ([A-Za-z0-9]+):\s*$", conditions, re.MULTILINE):
        name = match.group(1)
        start = match.end()
        next_cond = re.search(r"^\n  [A-Za-z]", conditions[start:], re.MULTILINE)
        end = start + next_cond.start() if next_cond else len(conditions)
        block = conditions[start:end]
        if "DbSnapshotIdentifier" not in block:
            continue
        if re.search(r"!Not\s*\n\s*- !Equals", block):
            return name
        if "Fn::Not" in block and "Fn::Equals" in block and "DbSnapshotIdentifier" in block:
            return name
    return ""


def _property_snippet(props: str, prop_name: str, *, window: int = 500) -> str:
    match = re.search(rf"^\s+{re.escape(prop_name)}:\s", props, re.MULTILINE)
    assert match, f"DbInstance property {prop_name!r} not found"
    start = match.start()
    return props[start : start + window]


def test_rds_stack_has_db_snapshot_identifier_parameter_with_empty_default() -> None:
    params = _parameters_block(_rds_stack_text())
    block = _parameter_block(params, "DbSnapshotIdentifier")
    assert re.search(r"^\s+Default:\s*(['\"]?['\"]?)\s*$", block, re.MULTILINE), (
        "DbSnapshotIdentifier must default to empty string for fresh-instance deploys"
    )


def test_rds_stack_has_restore_from_snapshot_condition() -> None:
    conditions = _conditions_block(_rds_stack_text())
    name = _restore_snapshot_condition_name(conditions)
    assert name, (
        "Conditions must include a restore guard (e.g. RestoreFromSnapshot) "
        "that is true when DbSnapshotIdentifier is non-empty"
    )
    assert "Restore" in name and "Snapshot" in name, (
        f"expected a Restore*Snapshot* condition name, got {name!r}"
    )


def test_db_instance_uses_dbsnapshot_identifier_when_restoring() -> None:
    block = _db_instance_block(_rds_stack_text())
    props_start = block.index("Properties:")
    props = block[props_start:]
    snippet = _property_snippet(props, "DBSnapshotIdentifier")
    assert "DbSnapshotIdentifier" in snippet, (
        "DBSnapshotIdentifier must reference the DbSnapshotIdentifier parameter"
    )
    assert "!If" in snippet or "Fn::If" in snippet, (
        "DBSnapshotIdentifier must be conditional (set only when restoring)"
    )
    conditions = _conditions_block(_rds_stack_text())
    restore_cond = _restore_snapshot_condition_name(conditions)
    assert restore_cond in snippet, (
        f"DBSnapshotIdentifier !If must use the restore condition ({restore_cond!r})"
    )


def test_db_instance_omits_fresh_credentials_when_restoring_from_snapshot() -> None:
    """MasterUsername/MasterUserPassword must not be set unconditionally on restore."""
    block = _db_instance_block(_rds_stack_text())
    props_start = block.index("Properties:")
    props = block[props_start:]

    for prop in ("MasterUsername", "MasterUserPassword"):
        snippet = _property_snippet(props, prop)
        assert "!If" in snippet or "Fn::If" in snippet, (
            f"{prop} must be conditional so fresh-only credentials are omitted on restore"
        )
        assert "AWS::NoValue" in snippet, (
            f"{prop} must use AWS::NoValue on the snapshot-restore branch"
        )
        assert "resolve:secretsmanager" in snippet, (
            f"{prop} should still resolve from Secrets Manager on fresh-instance branch"
        )


def test_db_instance_omits_dbname_when_restoring_from_snapshot() -> None:
    """DBName must be omitted on snapshot restore (RDS rejects DBName on restore)."""
    block = _db_instance_block(_rds_stack_text())
    props_start = block.index("Properties:")
    props = block[props_start:]
    snippet = _property_snippet(props, "DBName")
    assert "!If" in snippet or "Fn::If" in snippet, (
        "DBName must be conditional so it is omitted on snapshot restore"
    )
    assert "AWS::NoValue" in snippet, (
        "DBName must use AWS::NoValue on the snapshot-restore branch"
    )
    conditions = _conditions_block(_rds_stack_text())
    restore_cond = _restore_snapshot_condition_name(conditions)
    assert restore_cond in snippet, (
        f"DBName !If must use the restore condition ({restore_cond!r})"
    )
