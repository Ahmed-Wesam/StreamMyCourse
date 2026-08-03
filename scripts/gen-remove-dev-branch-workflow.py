"""Generate .github/workflows/remove-dev-stack-prod-only.yml (CI + prod deploy, no dev)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
deploy = (ROOT / ".github/workflows/deploy-backend.yml").read_text(encoding="utf-8")

ci_jobs_start = ci.index("jobs:\n") + len("jobs:\n")
ci_jobs = ci[ci_jobs_start:].rstrip() + "\n"

CI_JOB_NAMES = [
    "frontend",
    "lambda",
    "cloudformation",
    "security",
    "workflow-lint",
    "integration-tests-static",
    "lambda-unit-tests",
]
ci_needs = "\n".join(f"      - {n}" for n in CI_JOB_NAMES)

deploy_jobs_start = deploy.index("jobs:\n") + len("jobs:\n")
deploy_body = deploy[deploy_jobs_start:]

deploy_body = re.sub(
    r"  gate:.*?(?=  # Pin repo-level OIDC)",
    "",
    deploy_body,
    count=1,
    flags=re.S,
)

replacements = [
    (r"needs: \[gate, ([^\]]+)\]", r"needs: [\1]"),
    (r"needs: \[gate\]", f"needs:\n{ci_needs.strip()}"),
    (r"needs:\n      - gate\n", ""),
    (r"needs\.gate\.outputs\.should_deploy == 'true'\s*&&\s*", ""),
    (r"always\(\) &&\s*", "success() && "),
    (r"\$\{\{ needs\.gate\.outputs\.checkout_sha \}\}", "${{ github.sha }}"),
    (r"needs\.gate\.outputs\.checkout_sha", "github.sha"),
    (
        r"\(github\.event_name == 'workflow_run' \|\| github\.event_name == 'workflow_dispatch'\)",
        "true",
    ),
    (r"missing gate checkout_sha", "missing github.sha"),
]
for pat, rep in replacements:
    deploy_body = re.sub(pat, rep, deploy_body)
deploy_body = re.sub(r"\s*&&\s*true\s*$", "", deploy_body, flags=re.M)

# deploy-backend-prod waits on infra jobs only (CI is transitive via edge/rds/schema).
deploy_body = re.sub(
    r"(  deploy-backend-prod:\n.*?    needs:\n)(?:      - frontend\n"
    r"      - lambda\n"
    r"      - cloudformation\n"
    r"      - security\n"
    r"      - workflow-lint\n"
    r"      - integration-tests-static\n"
    r"      - lambda-unit-tests\n)",
    r"\1",
    deploy_body,
    count=1,
    flags=re.S,
)

deploy_body = deploy_body.replace(
    "  resolve-oidc-deploy-role:\n"
    "    name: Resolve repo OIDC deploy role ARN\n"
    "    runs-on: ubuntu-latest\n"
    "    needs: gate\n"
    "    if: needs.gate.outputs.should_deploy == 'true'",
    "  resolve-oidc-deploy-role:\n"
    "    name: Resolve repo OIDC deploy role ARN\n"
    "    runs-on: ubuntu-latest\n"
    "    needs:\n"
    f"{ci_needs}\n"
    "    if: success()",
)

header = """\
# Push to remove-dev-stack-prod-only: full CI parity, then prod-only deploy (no dev stacks).
# Uses this branch's workflow file (not main). Does not modify main's CI/Deploy workflows.
name: remove-dev-stack-prod-only

on:
  push:
    branches: [remove-dev-stack-prod-only]
  workflow_dispatch:

permissions:
  contents: read
  id-token: write

concurrency:
  group: remove-dev-stack-prod-only
  cancel-in-progress: false

env:
  AWS_REGION: eu-west-1

jobs:
"""

out = header + ci_jobs + deploy_body
out_path = ROOT / ".github/workflows/remove-dev-stack-prod-only.yml"
out_path.write_text(out, encoding="utf-8")
print(f"Wrote {out_path} ({len(out.splitlines())} lines)")

for forbidden in (
    "deploy-edge-dev",
    "deploy-backend-dev",
    "environment: dev",
    "Environment=dev",
    "gate",
):
    if forbidden in out:
        raise SystemExit(f"forbidden {forbidden!r} in output")
for required in ("deploy-edge-prod", "frontend:"):
    if required not in out:
        raise SystemExit(f"missing {required!r}")
print("Sanity OK")
