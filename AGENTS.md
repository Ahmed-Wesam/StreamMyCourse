# Agent context — start here

Use this file as the **index** for project intent. Before non-trivial planning or implementation, read the linked docs (or refresh if the task spans product scope, APIs, or deployment). Read the design.md and roadmap.md before starting

| Doc | Role |
|-----|------|
| [design.md](./design.md) | **MVP contract:** goals, architecture, APIs, data model, security, deployment, near-term §13 backlog |
| [roadmap.md](./roadmap.md) | **Phase 2+ vision:** monetization, DRM option, scale; bridge order mirrors design §13 |
| [ImplementationHistory.md](./ImplementationHistory.md) | **What shipped / how:** engineering history and decisions in practice |
| [plans/architecture/](./plans/architecture/) | **ADRs** and module map for backend layering |
| [.cursor/rules/clean-architecture-boundaries.mdc](./.cursor/rules/clean-architecture-boundaries.mdc) | **Lambda layering:** controller → service → repo |
| [.cursor/skills/update-docs/SKILL.md](./.cursor/skills/update-docs/SKILL.md) | **Session doc sync:** invoke `/update_docs` to refresh `design.md`, `roadmap.md`, `ImplementationHistory.md` |

**Code anchors:** `frontend/` (Vite React app), `infrastructure/lambda/catalog/` (Python API Lambda), `infrastructure/templates/api-stack.yaml` (CloudFormation), `infrastructure/templates/edge-hosting-stack.yaml` (unified student + teacher SPA + ACM in `us-east-1`), `infrastructure/templates/github-deploy-role-stack.yaml` (manual bootstrap IAM for GitHub OIDC; not in CI/CD), `infrastructure/deploy-environment.ps1` and `scripts/deploy-backend.sh` (mirrored dev/prod backends), `scripts/deploy-github-iam-stack.sh` (preferred IAM bootstrap) and `scripts/apply-github-deploy-role-policies.sh` (optional inline-policy-only sync **before push**), `.github/workflows/ci.yml` + `deploy-web-reusable.yml` + `deploy-teacher-web-reusable.yml` + `deploy-backend.yml` (CI runs on `main` pushes; **Deploy** runs only after CI succeeds, then dev then prod).

**Deploy / OIDC:** Repository **Actions variable** `AWS_DEPLOY_ROLE_ARN` must match the IAM role ARN from the GitHub OIDC bootstrap stack output (`StreamMyCourse-GitHubDeployIam` → `GitHubDeployRoleArn`). **`verify-rds-reusable.yml`** receives it via `workflow_call` `with:` (`secrets`/`env` contexts are not allowed there). Environment secrets on **dev**/**prod** still supply Cognito verify credentials inside that reusable job.

**Before merging (matches CI):** from `frontend/`, run `npm ci`, `npm run lint`, `npm run knip`, `npm run build:all`, `npm run test`; from repo root, `python -m vulture infrastructure/lambda/catalog --min-confidence 61` (after `pip install vulture`) and `python scripts/check_lambda_boundaries.py`.
