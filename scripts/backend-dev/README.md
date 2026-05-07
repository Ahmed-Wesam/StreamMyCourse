# Deploy backend dev (GitHub only)

Triggers [`.github/workflows/deploy-backend-dev-only.yml`](../../.github/workflows/deploy-backend-dev-only.yml): same work as **Deploy → Backend (dev) — Video + API** (Cognito auth + `./scripts/deploy-backend.sh dev`). Uses GitHub Environment **dev** secrets; values are never read onto your machine.

```bash
./scripts/backend-dev/Backend-dev-via-GitHub.sh          # current branch
./scripts/backend-dev/Backend-dev-via-GitHub.sh main
```

PowerShell:

```powershell
.\scripts\backend-dev\Backend-dev-via-GitHub.ps1
.\scripts\backend-dev\Backend-dev-via-GitHub.ps1 main
```

Needs [GitHub CLI](https://cli.github.com/) (`gh auth login`). The workflow file must exist on the default branch before `gh workflow run` finds it.

For the **full** `Deploy` workflow (edge, RDS, tests, SPAs, …), dispatch **Deploy** from the Actions UI or `gh workflow run Deploy --ref main`.
