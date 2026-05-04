from __future__ import annotations

import ast
import glob
import os
import sys
from dataclasses import dataclass
from typing import Iterable, List, Set, Tuple


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LAMBDA_GLOB = os.path.join(ROOT, "infrastructure", "lambda", "catalog", "**", "*.py")
COGNITO_SYNC_GLOB = os.path.join(ROOT, "infrastructure", "lambda", "cognito_user_profile_sync", "**", "*.py")


@dataclass(frozen=True)
class Violation:
    path: str
    message: str


def _norm_path(path: str) -> str:
    return os.path.normpath(path).replace("\\", "/")


def _module_path_from_file(path: str) -> str:
    rel = _norm_path(os.path.relpath(path, ROOT))
    return rel


def _collect_imports(tree: ast.AST) -> Tuple[Set[str], Set[str]]:
    """
    Returns:
      - absolute module names from `import x`
      - absolute module names from `from x import y` (x only)
    """
    imports: Set[str] = set()
    from_imports: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                # relative imports are allowed within package; still record module if absolute provided
                if node.module:
                    from_imports.add(node.module.split(".")[0])
            elif node.module:
                from_imports.add(node.module.split(".")[0])
    return imports, from_imports


def _all_roots(imports: Set[str], from_imports: Set[str]) -> Set[str]:
    return set(imports) | set(from_imports)


def _is_under(rel: str, prefix: str) -> bool:
    return rel.replace("\\", "/").startswith(prefix.rstrip("/") + "/")


def check_file(path: str) -> List[Violation]:
    rel = _module_path_from_file(path)
    violations: List[Violation] = []

    with open(path, "rb") as f:
        src = f.read()
    tree = ast.parse(src, filename=path)
    imports, from_imports = _collect_imports(tree)
    roots = _all_roots(imports, from_imports)

    # Global: boto3 only in adapters + the composition root (bootstrap fetches
    # RDS credentials from Secrets Manager via boto3 before building the repos).
    allowed_boto3_files = {
        _norm_path(os.path.join(ROOT, "infrastructure/lambda/catalog/bootstrap.py")),
        _norm_path(os.path.join(ROOT, "infrastructure/lambda/catalog/services/course_management/repo.py")),
        _norm_path(os.path.join(ROOT, "infrastructure/lambda/catalog/services/course_management/storage.py")),
        _norm_path(os.path.join(ROOT, "infrastructure/lambda/catalog/services/auth/repo.py")),
        _norm_path(os.path.join(ROOT, "infrastructure/lambda/catalog/services/enrollment/repo.py")),
        _norm_path(os.path.join(ROOT, "infrastructure/lambda/cognito_user_profile_sync/repo.py")),
    }
    if "boto3" in roots and _norm_path(path) not in allowed_boto3_files:
        violations.append(Violation(rel, "boto3 may only be imported in bootstrap.py, repo.py, or storage.py"))

    # Global: psycopg2 only in the RDS adapters + the composition root
    # (bootstrap.py opens the connection). No other module should reach for
    # psycopg2 directly.
    allowed_psycopg2_files = {
        _norm_path(os.path.join(ROOT, "infrastructure/lambda/catalog/bootstrap.py")),
        _norm_path(os.path.join(ROOT, "infrastructure/lambda/catalog/services/course_management/rds_repo.py")),
        _norm_path(os.path.join(ROOT, "infrastructure/lambda/catalog/services/auth/rds_repo.py")),
        _norm_path(os.path.join(ROOT, "infrastructure/lambda/catalog/services/enrollment/rds_repo.py")),
        _norm_path(os.path.join(ROOT, "infrastructure/lambda/cognito_user_profile_sync/repo.py")),
    }
    if "psycopg2" in roots and _norm_path(path) not in allowed_psycopg2_files:
        violations.append(
            Violation(rel, "psycopg2 may only be imported in bootstrap.py or rds_repo.py")
        )

    # Cross bounded-context imports (course_management <-> auth)
    if _is_under(rel, "infrastructure/lambda/catalog/services/course_management"):
        if "services.auth" in roots:
            violations.append(Violation(rel, "course_management must not import services.auth"))
    if _is_under(rel, "infrastructure/lambda/catalog/services/auth"):
        if "services.course_management" in roots:
            violations.append(Violation(rel, "auth must not import services.course_management"))

    # Service must not depend on HTTP/controller layers
    if rel.endswith("/services/course_management/service.py"):
        forbidden = {"services.common.http"}
        bad = sorted(forbidden & roots)
        if bad:
            violations.append(Violation(rel, f"service must not import: {', '.join(bad)}"))

    if rel.endswith("/services/auth/service.py"):
        forbidden = {"services.common.http"}
        bad = sorted(forbidden & roots)
        if bad:
            violations.append(Violation(rel, f"auth service must not import: {', '.join(bad)}"))

    # Controller must not import boto3 (belt + suspenders)
    if rel.endswith("/services/course_management/controller.py") and "boto3" in roots:
        violations.append(Violation(rel, "controller must not import boto3"))

    if rel.endswith("/services/auth/controller.py") and "boto3" in roots:
        violations.append(Violation(rel, "auth controller must not import boto3"))

    # Repo/storage must not import HTTP helpers (covers both DynamoDB repos and
    # the new PostgreSQL rds_repo.py adapters).
    is_persistence_adapter = (
        rel.endswith("/services/course_management/repo.py")
        or rel.endswith("/services/course_management/storage.py")
        or rel.endswith("/services/course_management/rds_repo.py")
        or rel.endswith("/services/auth/repo.py")
        or rel.endswith("/services/auth/rds_repo.py")
        or rel.endswith("/services/enrollment/repo.py")
        or rel.endswith("/services/enrollment/rds_repo.py")
    )
    if is_persistence_adapter and "services.common.http" in roots:
        violations.append(Violation(rel, "repo/storage must not import services.common.http"))

    return violations


def main() -> int:
    paths = sorted(
        set(glob.glob(LAMBDA_GLOB, recursive=True) + glob.glob(COGNITO_SYNC_GLOB, recursive=True))
    )
    all_violations: List[Violation] = []
    for p in paths:
        all_violations.extend(check_file(p))

    if all_violations:
        print("Boundary check FAILED", file=sys.stderr)
        for v in all_violations:
            print(f"- {v.path}: {v.message}", file=sys.stderr)
        return 1

    print(f"Boundary check OK ({len(paths)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
