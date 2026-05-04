---
name: commit
description: Commit local changes in small logical groupings with conventional commit messages. Use when the user asks to commit changes, save work, or create commits from modified files. Before committing, run CI-parity checks from ci.yml (frontend, lambda, cloudformation, actionlint, lambda unit tests) except integ-tests-static. After committing, follow /update-docs (design.md, roadmap.md, ImplementationHistory.md) when the session warrants it. Does not push unless the user explicitly asks to push.
disable-model-invocation: true
---

# /commit

Commit unstaged and staged changes as small, logical commits using conventional commit format.

**Do not run `git push` unless the user explicitly asks to push** (e.g. “commit and push”, “push to origin”). After committing and any doc sync, stop unless a push was requested.

## Workflow

1. **Analyze changes** - Check git status and diff to understand what changed
2. **Run pre-deploy checks (CI parity)** - Run the same gates as GitHub Actions **CI** (see [`.github/workflows/ci.yml`](../../../.github/workflows/ci.yml)) for every job **except** **`integ-tests-static`** (the integration test tree: install integ deps, `py_compile` on `tests/integration/**/*.py`, and `pytest --collect-only` under `tests/integration`). That means: **frontend**, **lambda**, **cloudformation**, **workflow-lint** (actionlint on `.github/workflows`), and **lambda-unit-tests**. Fix failures before committing. Skip individual commands that clearly do not apply to the touched files only when it saves time and risk is low (e.g. skip frontend installs if the diff is doc-only); otherwise run the full set.
3. **Group logically** - Organize files into related groups (by feature, module, or change type)
4. **Stage and commit each group** - Create focused commits with conventional commit messages
5. **Update project docs (`/update-docs`)** - After commits, follow [`.cursor/skills/update-docs/SKILL.md`](../update-docs/SKILL.md): refresh `design.md`, `roadmap.md`, and `ImplementationHistory.md` when the session’s changes warrant it (features, APIs, infra, CI/CD, security, shipped behavior). If you edit those files, commit them (e.g. `docs: sync project docs` or a scoped `docs(...)`). Skip when nothing material changed (e.g. typo-only or the three files were already the only commits).
6. **Push (only if asked)** - Run `git push` only when the user explicitly requested a push in the same instruction or follow-up

## Instructions

### Step 1: Analyze changes

Run these commands to understand the current state:

```bash
git status
git diff --stat
git diff HEAD
```

### Step 2: Pre-deploy checks (matches CI, excluding integration test static job only)

Run from the **repository root** unless noted. Mirrors [`.github/workflows/ci.yml`](../../../.github/workflows/ci.yml) jobs **`frontend`**, **`lambda`**, **`cloudformation`**, **`workflow-lint`**, and **`lambda-unit-tests`**. The only CI job **not** run here is **`integ-tests-static`** (integration test package install, compile, and collect-only).

**Prerequisites:** Node 20+, Python 3.11+, `pip` available, **bash** (for actionlint install script; Git Bash on Windows is fine).

**Frontend** (same as CI job `frontend`; working directory `frontend/`):

```bash
npm ci
npm run lint
npm run knip
npm run build:all
```

**Lambda** (same as CI job `lambda`; repo root):

```bash
python - <<'PY'
import glob, py_compile
paths = glob.glob("infrastructure/lambda/catalog/**/*.py", recursive=True)
for p in paths:
    py_compile.compile(p, doraise=True)
print("OK", len(paths))
PY
python scripts/check_lambda_boundaries.py
pip install vulture radon
python -m vulture infrastructure/lambda/catalog --min-confidence 61
python -m radon cc infrastructure/lambda/catalog -a -nc
```

The **Radon** step matches CI (there it has `continue-on-error: true`); treat a noisy Radon report as informational unless the team decides otherwise.

**CloudFormation** (same as CI job `cloudformation`; repo root):

```bash
pip install pyyaml
python scripts/parse_cloudformation_yaml.py infrastructure/templates/api-stack.yaml
python scripts/parse_cloudformation_yaml.py infrastructure/templates/auth-stack.yaml
python scripts/parse_cloudformation_yaml.py infrastructure/templates/video-stack.yaml
python scripts/parse_cloudformation_yaml.py infrastructure/templates/edge-hosting-stack.yaml
python scripts/parse_cloudformation_yaml.py infrastructure/templates/github-deploy-role-stack.yaml
python scripts/parse_cloudformation_yaml.py infrastructure/templates/billing-alarm.yaml
```

**GitHub Actions workflow lint** (same as CI job `workflow-lint`; repo root). You **do not** need a committed `actionlint` binary: either install **actionlint** on your **`PATH`** once (e.g. [releases](https://github.com/rhysd/actionlint/releases), `go install github.com/rhysd/actionlint/cmd/actionlint@v1.7.7`, or a package manager), or download per run (ignored by git — see root [`.gitignore`](../../../.gitignore) **`/actionlint`** / **`/actionlint.exe`**).

From repo root, pin **`v1.7.7`** to match `ci.yml`:

```bash
set -euo pipefail
if command -v actionlint >/dev/null 2>&1; then
  actionlint -color
elif command -v actionlint.exe >/dev/null 2>&1; then
  actionlint.exe -color
else
  bash <(curl -fsSL https://raw.githubusercontent.com/rhysd/actionlint/v1.7.7/scripts/download-actionlint.bash)
  if [[ -f ./actionlint.exe ]]; then ./actionlint.exe -color; else ./actionlint -color; fi
fi
```

On **Windows** without `actionlint` on `PATH`, run the block in **Git Bash** / MSYS so `bash` and the download script work; the dropped **`actionlint.exe`** stays untracked (gitignored). No need to delete it after each run unless you prefer a clean tree.

**Lambda unit tests** (same as CI job `lambda-unit-tests`; repo root; not integration tests):

```bash
pip install -r tests/unit/requirements.txt
coverage run -m pytest tests/unit -q --junitxml=tests/unit/results.xml
coverage report --include="infrastructure/lambda/catalog/**" -m
```

**Excluded — entire CI job `integ-tests-static` (do not run for /commit):**

- `pip install -r tests/integration/requirements.txt`
- `py_compile` on `tests/integration/**/*.py`
- `cd tests/integration && pytest --collect-only` (or `working-directory: tests/integration` equivalent)

**IAM policy JSON / GitHub deploy stack (before `git push`):** If the diff touches [`infrastructure/iam-policy-github-deploy-backend.json`](../../../infrastructure/iam-policy-github-deploy-backend.json), [`infrastructure/iam-policy-github-deploy-web.json`](../../../infrastructure/iam-policy-github-deploy-web.json), [`infrastructure/templates/github-deploy-role-stack.yaml`](../../../infrastructure/templates/github-deploy-role-stack.yaml), or [`infrastructure/iam-trust-github-oidc.json`](../../../infrastructure/iam-trust-github-oidc.json), or adds/changes workflow steps that need **new AWS permissions**, run locally (admin credentials) **before** pushing so GitHub Actions does not fail mid-**Deploy**:

- Preferred: `./scripts/deploy-github-iam-stack.sh` or `.\scripts\deploy-github-iam-stack.ps1` (CloudFormation; see [`infrastructure/README.md`](../../../infrastructure/README.md)).
- Policy-only on an existing role: `./scripts/apply-github-deploy-role-policies.sh` or `.\scripts\apply-github-deploy-role-policies.ps1`

See [`infrastructure/README.md`](../../../infrastructure/README.md) (GitHub OIDC deploy role). Trust-policy updates still use the JSON file as source of truth but may require a separate `update-assume-role-policy-document` step if not scripted yet.

### Step 3: Group changes

Group files by:
- **Feature/functional area** (e.g., auth-related files, UI components)
- **File type** (e.g., all CSS changes, all documentation)
- **Change type** (e.g., new files vs. modifications)

Aim for commits that:
- Are 1-10 files each (smaller is better)
- Represent a single logical change
- Can be described in one clear sentence

### Step 4: Stage and commit

For each logical group:

1. Stage the files:
   ```bash
   git add <files-in-group>
   ```

2. Generate a conventional commit message:
   - Type: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
   - Scope: optional module/component name in parentheses
   - Description: brief imperative summary

   Format: `<type>(<scope>): <description>`

   Examples:
   - `feat(auth): add JWT token validation`
   - `fix(api): handle null response in user endpoint`
   - `docs(readme): update installation instructions`
   - `refactor(utils): simplify date formatting logic`
   - `style(button): fix indentation in component`
   - `test(login): add unit tests for form validation`
   - `chore(deps): update dependency versions`

3. Commit:
   ```bash
   git commit -m "<type>(<scope>): <description>"
   ```

### Step 5: Update docs (`/update-docs`)

After the code/infra commits above, keep the project index docs aligned with what shipped in **this session**. Full procedure: [`.cursor/skills/update-docs/SKILL.md`](../update-docs/SKILL.md).

1. **Before editing:** Read [`AGENTS.md`](../../../AGENTS.md) at the repo root and load [`design.md`](../../../design.md) first so updates stay consistent with the MVP contract.
2. **Update these files** when the session’s commits warrant it:
   - **`design.md`** — MVP contract: deployment (e.g. §10), backlog (e.g. §13), security/S3/Lambda bullets if behavior or infra changed.
   - **`roadmap.md`** — Phase 2+ vision: MVP baseline (shipped) or bridge table only when what exists vs future work changed materially.
   - **`ImplementationHistory.md`** — Add a dated section (`## YYYY-MM-DD — short title`) with completed items, decisions, and links to files/workflows.
3. **Style:** Factual bullets; link paths and workflow names; do not invent shipped features that are not in the repo or AWS.
4. **Git:** If any of the three files changed, stage and commit them (separate commit from feature work is fine), e.g. `docs: sync design, roadmap, and implementation history`.
5. **Skip** when the session’s commits are too small to affect contract/history (typos, formatting-only) and the three files need no change.

Re-run **Step 2** (or the relevant slice: e.g. frontend/lambda only) if doc edits could affect CI assumptions; usually doc-only commits need no re-run.

### Step 6: Push (only when the user says so)

**Skip this step by default.** Only after the user explicitly asks to push (same message or clear follow-up):

```bash
git push
```

When pushing:

1. **Never force push** (`git push --force`) unless the user explicitly requests it (warn on main/master)
2. **Check current branch** before pushing when appropriate

## Safety Rules

1. **Never push without explicit user request** — commits stay local until the user says to push
2. **Never force push** (`git push --force`)
3. **Verify no secrets** in staged files before committing
4. **Review large diffs** - if a file has significant changes, consider splitting further

## Git Safety Protocol

Follow these when committing:

- NEVER update the git config
- NEVER run destructive/irreversible git commands (like push --force, hard reset, etc) unless the user explicitly requests them
- NEVER skip hooks (--no-verify, --no-gpg-sign, etc) unless the user explicitly requests it
- NEVER run force push to main/master, warn the user if they request it
- Avoid git commit --amend. ONLY use --amend when ALL conditions are met:
  1. User explicitly requested amend, OR commit SUCCEEDED but pre-commit hook auto-modified files that need including
  2. HEAD commit was created by you in this conversation (verify: git log -1 --format='%an %ae')
  3. Commit has NOT been pushed to remote (verify: git status shows "Your branch is ahead")
- CRITICAL: If commit FAILED or was REJECTED by hook, NEVER amend - fix the issue and create a NEW commit
- CRITICAL: If you already pushed to remote, NEVER amend unless user explicitly requests it (requires force push)
- NEVER commit changes unless the user explicitly asks you to. It is VERY IMPORTANT to only commit when explicitly asked, otherwise the user will feel that you are being too proactive.
- NEVER push (`git push`) unless the user explicitly asks you to push. Commits are local until then.
- IMPORTANT: Never use git commands with the -i flag (like git rebase -i or git add -i) since they require interactive input which is not supported.
- NEVER commit files that likely contain secrets (.env, credentials.json, etc). Warn the user if they specifically request to commit those files

## Commit Message Format

```
<type>(<scope>): <short summary>
  │       │             │
  │       │             └─> Summary in present tense. Not capitalized. No period at the end.
  │       │
  │       └─> Scope: noun describing section of codebase (optional)
  │
  └─> Type: feat|fix|docs|style|refactor|test|chore
```

### Types

| Type | Description |
|------|-------------|
| feat | A new feature |
| fix | A bug fix |
| docs | Documentation only changes |
| style | Changes that don't affect code meaning (formatting, semicolons, etc) |
| refactor | Code change that neither fixes a bug nor adds a feature |
| test | Adding or correcting tests |
| chore | Changes to build process, dependencies, tooling, etc |

## Example Session

**Changes detected:**
- `src/auth/login.js` (modified)
- `src/auth/utils.js` (modified)
- `src/components/Button.jsx` (modified)
- `src/components/Input.jsx` (modified)
- `README.md` (modified)

**Logical groups:**
1. Auth changes: `src/auth/login.js`, `src/auth/utils.js`
2. UI component changes: `src/components/Button.jsx`, `src/components/Input.jsx`
3. Documentation: `README.md`

**Resulting commits:**
```
feat(auth): implement password reset flow

refactor(components): extract common input styling

docs(readme): add deployment instructions
```

**Do not push** unless the user also asked to push. If they did: `git push` (after verifying branch and safety rules above).

After feature commits, apply **Step 5** (`/update-docs`) when appropriate, then push if requested (so docs can ride with the same push).
