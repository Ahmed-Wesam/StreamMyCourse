from __future__ import annotations

import ast
import glob
import os
import sys
from dataclasses import dataclass
from typing import List, Set, Tuple


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LAMBDA_GLOB = os.path.join(ROOT, "infrastructure", "lambda", "catalog", "**", "*.py")
COGNITO_SYNC_GLOB = os.path.join(
    ROOT, "infrastructure", "lambda", "cognito_user_profile_sync", "**", "*.py"
)
BILLING_EDGE_GLOB = os.path.join(ROOT, "infrastructure", "lambda", "billing_edge", "**", "*.py")
BILLING_FULFILLMENT_GLOB = os.path.join(
    ROOT, "infrastructure", "lambda", "billing_fulfillment", "**", "*.py"
)

# Outbound HTTP (stdlib) — billing_edge WS2: only PayTabs adapter may import these.
_HTTP_CLIENT_ROOTS = frozenset({"urllib", "http", "httplib"})


def _p(*parts: str) -> str:
    return os.path.normpath(os.path.join(ROOT, *parts)).replace("\\", "/")


_CATALOG_BOTO3_ALLOWED = frozenset(
    {
        _p("infrastructure/lambda/catalog/bootstrap.py"),
        _p("infrastructure/lambda/catalog/services/course_management/storage.py"),
        _p("infrastructure/lambda/catalog/services/common/sqs_client.py"),
        _p("infrastructure/lambda/cognito_user_profile_sync/repo.py"),
    }
)

_CATALOG_PSYCOPG2_ALLOWED = frozenset(
    {
        _p("infrastructure/lambda/catalog/bootstrap.py"),
        _p("infrastructure/lambda/catalog/services/course_management/rds_repo.py"),
        _p("infrastructure/lambda/catalog/services/auth/rds_repo.py"),
        _p("infrastructure/lambda/catalog/services/enrollment/rds_repo.py"),
        _p("infrastructure/lambda/catalog/services/progress/rds_repo.py"),
        _p("infrastructure/lambda/catalog/services/question_banks/rds_repo.py"),
        _p("infrastructure/lambda/cognito_user_profile_sync/repo.py"),
    }
)

# WS2 billing_edge: boto3 only for Secrets Manager credential load.
_BILLING_EDGE_BOTO3_ALLOWED = frozenset(
    {
        _p("infrastructure/lambda/billing_edge/paytabs_secrets.py"),
        _p("infrastructure/lambda/billing_edge/queue/enqueue.py"),
    }
)

_BILLING_FULFILLMENT_BOTO3_ALLOWED = frozenset(
    {
        _p("infrastructure/lambda/billing_fulfillment/fulfillment_repo.py"),
    }
)

_BILLING_FULFILLMENT_PSYCOPG2_ALLOWED = frozenset(
    {
        _p("infrastructure/lambda/billing_fulfillment/fulfillment_repo.py"),
    }
)

_BILLING_EDGE_HTTP_ALLOWED = frozenset(
    {
        _p("infrastructure/lambda/billing_edge/providers/paytabs_adapter.py"),
    }
)


@dataclass(frozen=True)
class Violation:
    path: str
    message: str


def _norm_path(path: str) -> str:
    return os.path.normpath(path).replace("\\", "/")


def _module_path_from_file(path: str) -> str:
    rel = _norm_path(os.path.relpath(path, ROOT))
    return rel


def _lambda_package(rel: str) -> str:
    if rel.startswith("infrastructure/lambda/catalog/"):
        return "catalog"
    if rel.startswith("infrastructure/lambda/cognito_user_profile_sync/"):
        return "cognito_sync"
    if rel.startswith("infrastructure/lambda/billing_edge/"):
        return "billing_edge"
    if rel.startswith("infrastructure/lambda/billing_fulfillment/"):
        return "billing_fulfillment"
    return "unknown"


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
                if node.module:
                    from_imports.add(node.module.split(".")[0])
            elif node.module:
                from_imports.add(node.module.split(".")[0])
    return imports, from_imports


def _all_roots(imports: Set[str], from_imports: Set[str]) -> Set[str]:
    return set(imports) | set(from_imports)


def _is_under(rel: str, prefix: str) -> bool:
    return rel.replace("\\", "/").startswith(prefix.rstrip("/") + "/")


def _check_boto3(rel: str, norm: str, roots: Set[str], allowed: frozenset[str], label: str) -> List[Violation]:
    if "boto3" not in roots or norm in allowed:
        return []
    return [
        Violation(
            rel,
            f"boto3 may only be imported in {label} allowlisted files",
        )
    ]


def _check_psycopg2(rel: str, norm: str, roots: Set[str], allowed: frozenset[str], label: str) -> List[Violation]:
    if "psycopg2" not in roots or norm in allowed:
        return []
    return [
        Violation(
            rel,
            f"psycopg2 may only be imported in {label} allowlisted files",
        )
    ]


def _check_billing_edge_http(rel: str, norm: str, roots: Set[str]) -> List[Violation]:
    bad = sorted(_HTTP_CLIENT_ROOTS & roots)
    if not bad or norm in _BILLING_EDGE_HTTP_ALLOWED:
        return []
    return [
        Violation(
            rel,
            f"HTTP client imports ({', '.join(bad)}) only allowed in providers/paytabs_adapter.py",
        )
    ]


def check_file(path: str) -> List[Violation]:
    rel = _module_path_from_file(path)
    norm = _norm_path(path)
    violations: List[Violation] = []
    package = _lambda_package(rel)

    with open(path, "rb") as f:
        src = f.read()
    tree = ast.parse(src, filename=path)
    imports, from_imports = _collect_imports(tree)
    roots = _all_roots(imports, from_imports)

    if package in ("catalog", "cognito_sync"):
        violations.extend(
            _check_boto3(rel, norm, roots, _CATALOG_BOTO3_ALLOWED, "catalog/cognito")
        )
        violations.extend(
            _check_psycopg2(rel, norm, roots, _CATALOG_PSYCOPG2_ALLOWED, "catalog/cognito")
        )
    elif package == "billing_edge":
        violations.extend(
            _check_boto3(rel, norm, roots, _BILLING_EDGE_BOTO3_ALLOWED, "billing_edge")
        )
        violations.extend(
            _check_psycopg2(rel, norm, roots, frozenset(), "billing_edge")
        )
        violations.extend(_check_billing_edge_http(rel, norm, roots))
    elif package == "billing_fulfillment":
        violations.extend(
            _check_boto3(rel, norm, roots, _BILLING_FULFILLMENT_BOTO3_ALLOWED, "billing_fulfillment")
        )
        violations.extend(
            _check_psycopg2(
                rel, norm, roots, _BILLING_FULFILLMENT_PSYCOPG2_ALLOWED, "billing_fulfillment"
            )
        )

    if package != "catalog":
        return violations

    # --- catalog-only rules below ---

    if _is_under(rel, "infrastructure/lambda/catalog/services/course_management"):
        if "services.auth" in roots:
            violations.append(Violation(rel, "course_management must not import services.auth"))
    if _is_under(rel, "infrastructure/lambda/catalog/services/auth"):
        if "services.course_management" in roots:
            violations.append(Violation(rel, "auth must not import services.course_management"))

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

    if rel.endswith("/services/course_management/controller.py") and "boto3" in roots:
        violations.append(Violation(rel, "controller must not import boto3"))

    if rel.endswith("/services/auth/controller.py") and "boto3" in roots:
        violations.append(Violation(rel, "auth controller must not import boto3"))

    if rel.endswith("/services/progress/controller.py") and "boto3" in roots:
        violations.append(Violation(rel, "progress controller must not import boto3"))

    is_persistence_adapter = (
        rel.endswith("/services/course_management/storage.py")
        or rel.endswith("/services/course_management/rds_repo.py")
        or rel.endswith("/services/auth/rds_repo.py")
        or rel.endswith("/services/enrollment/rds_repo.py")
        or rel.endswith("/services/progress/rds_repo.py")
    )
    if is_persistence_adapter and "services.common.http" in roots:
        violations.append(Violation(rel, "repo/storage must not import services.common.http"))

    return violations


def main() -> int:
    paths = sorted(
        set(
            glob.glob(LAMBDA_GLOB, recursive=True)
            + glob.glob(COGNITO_SYNC_GLOB, recursive=True)
            + glob.glob(BILLING_EDGE_GLOB, recursive=True)
            + glob.glob(BILLING_FULFILLMENT_GLOB, recursive=True)
        )
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
