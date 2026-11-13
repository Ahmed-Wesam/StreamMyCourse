"""Import boundary checks for Aurora DSQL connector and db_tx."""

from __future__ import annotations

import ast
import tempfile
from pathlib import Path

from scripts import check_lambda_boundaries as boundaries


def test_aurora_dsql_only_allowed_in_dsql_connect() -> None:
    norm = boundaries._p("infrastructure/lambda/catalog/dsql_connect.py")
    assert norm in boundaries._AURORA_DSQL_ALLOWED

    with tempfile.TemporaryDirectory() as tmp:
        bad = Path(tmp) / "bad_common.py"
        bad.write_text("import aurora_dsql_psycopg2\n", encoding="utf-8")
        rel = boundaries._module_path_from_file(str(bad))
        tree = ast.parse(bad.read_text(encoding="utf-8"))
        imports, from_imports = boundaries._collect_imports(tree)
        roots = boundaries._all_roots(imports, from_imports)
        violations = boundaries._check_aurora_dsql(
            rel,
            boundaries._norm_path(str(bad)),
            roots,
            boundaries._AURORA_DSQL_ALLOWED,
            "catalog",
        )
        assert violations


def test_db_tx_does_not_import_psycopg2() -> None:
    path = boundaries._p("infrastructure/lambda/catalog/services/common/db_tx.py")
    with open(path, "rb") as f:
        tree = ast.parse(f.read(), filename=path)
    imports, from_imports = boundaries._collect_imports(tree)
    roots = boundaries._all_roots(imports, from_imports)
    assert "psycopg2" not in roots
    assert "aurora_dsql_psycopg2" not in roots
