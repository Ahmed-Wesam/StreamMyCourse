---
name: security-scans
description: Run StreamMyCourse security scanners for CI parity. Use when changing CI/CD, CloudFormation, dependencies, requirements files, secrets-sensitive code, deploy workflows, or when the user asks for Checkov, Gitleaks, npm audit, pip-audit, vulnerability scanning, secret scanning, or security gates.
disable-model-invocation: true
---

# Security Scans

Run the same security gates as `.github/workflows/ci.yml` job `security`.

## Commands

From the repository root unless noted:

```bash
cd frontend
npm ci
npm audit --audit-level=high
cd ..
```

Use Python 3.11 to match CI:

```bash
pip install checkov pip-audit
checkov --config-file .checkov.yaml --skip-download
pip-audit \
  -r infrastructure/lambda/catalog/requirements.txt \
  -r infrastructure/lambda/cognito_user_profile_sync/requirements.txt \
  -r infrastructure/lambda/catalog_token_authorizer/requirements.txt \
  -r tests/unit/requirements.txt \
  -r tests/integration/requirements.txt
```

Run Gitleaks if installed locally:

```bash
gitleaks git . --config .gitleaks.toml --redact --no-banner --verbose --log-opts=HEAD
```

This scans the tracked Git tree for the current commit, matching CI. If Gitleaks is not installed locally, either install it from the latest GitHub release or rely on CI for that slice and report the local skip clearly.

## Notes

- `.checkov.yaml` contains the current MVP baseline skips. Do not add a skip without a clear reason and a follow-up hardening path.
- `.gitleaks.toml` allowlists only intentional fixtures; do not allowlist real secrets or local `.env` files.
- Fix dependency vulnerabilities rather than lowering audit severity unless the user explicitly accepts the risk.
- Never print or paste secret values while investigating scanner output.
