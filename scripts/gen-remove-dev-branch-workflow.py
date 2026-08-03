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
ci_needs_block = "needs:\n" + "\n".join(f"      - {n}" for n in CI_JOB_NAMES)

deploy_jobs_start = deploy.index("jobs:\n") + len("jobs:\n")
deploy_body = deploy[deploy_jobs_start:]

# Drop CI gate job (main-only workflow_run gate).
deploy_body = re.sub(
    r"  gate:.*?(?=  # Pin repo-level OIDC)",
    "",
    deploy_body,
    count=1,
    flags=re.S,
)

# Single-line needs: [gate] -> full CI needs block (edge/rds parallel after CI).
deploy_body = re.sub(r"    needs: \[gate\]", f"    {ci_needs_block}", deploy_body)

# Single-line needs: [gate, ...] -> drop gate only.
deploy_body = re.sub(r"needs: \[gate, ", "needs: [", deploy_body)

# Multi-line needs lists that started with gate.
deploy_body = re.sub(r"(\n      - gate\n)", "\n", deploy_body)

deploy_body = deploy_body.replace("${{ needs.gate.outputs.checkout_sha }}", "${{ github.sha }}")
deploy_body = deploy_body.replace("needs.gate.outputs.checkout_sha", "github.sha")
deploy_body = deploy_body.replace("missing gate checkout_sha", "missing github.sha")

deploy_body = re.sub(
    r"needs\.gate\.outputs\.should_deploy == 'true'\s*&&\s*",
    "",
    deploy_body,
)
deploy_body = re.sub(r"always\(\) &&\s*", "success() && ", deploy_body)
deploy_body = re.sub(
    r"\(github\.event_name == 'workflow_run' \|\| github\.event_name == 'workflow_dispatch'\)",
    "true",
    deploy_body,
)
deploy_body = re.sub(r"\s*&&\s*true\s*$", "", deploy_body, flags=re.M)

deploy_body = deploy_body.replace(
    "  resolve-oidc-deploy-role:\n"
    "    name: Resolve repo OIDC deploy role ARN\n"
    "    runs-on: ubuntu-latest\n"
    "    needs: gate\n"
    "    if: needs.gate.outputs.should_deploy == 'true'",
    "  resolve-oidc-deploy-role:\n"
    "    name: Resolve repo OIDC deploy role ARN\n"
    "    runs-on: ubuntu-latest\n"
    f"    {ci_needs_block}\n"
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
    "  gate:",
    "needs.gate",
):
    if forbidden in out:
        raise SystemExit(f"forbidden {forbidden!r} in output")
for required in ("deploy-edge-prod", "frontend:", "    needs:\n      - deploy-edge-prod"):
    if required not in out:
        raise SystemExit(f"missing {required!r}")
print("Sanity OK")
