"""Preview Api-dsql stack integration modules must not exist after stack teardown."""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Modules that only targeted deleted preview stack StreamMyCourse-Api-dsql.
_REMOVED_PREVIEW_STACK_MODULES = (
    "tests/integration/test_dsql_foundation.py",
    "tests/unit/test_dsql_foundation_skip.py",
    "tests/integration/test_billing_checkout_precheck_dsql.py",
    "tests/integration/test_billing_fulfillment_dsql.py",
    "tests/integration/test_question_bank_concurrency.py",
    "tests/integration/test_rate_limit_contact.py",
    "tests/integration/test_user_deletion.py",
)


@pytest.mark.parametrize("relative_path", _REMOVED_PREVIEW_STACK_MODULES)
def test_preview_stack_module_absent(relative_path: str) -> None:
    path = _REPO_ROOT / relative_path
    assert not path.is_file(), f"preview-only module still present: {relative_path}"