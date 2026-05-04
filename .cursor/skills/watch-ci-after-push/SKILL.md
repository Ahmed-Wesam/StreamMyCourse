---
name: watch-ci-after-push
description: Watches the latest GitHub Actions CI run after a push, then watches the Deploy workflow run triggered by that CI completion on main; reports success or debugs failures with GitHub and AWS CLIs, applies fixes, then follows the commit skill and pushes again until CI passes (and deploy passes on the follow-up push). Use after pushing to main, when verifying remote CI and deploy, or when the user asks to watch the pipeline, follow the workflow, or fix a failed Actions run.
disable-model-invocation: true
---

# /watch-ci-after-push

After a **push** (or when the user asks to verify remote CI), **watch the repository CI workflow**, confirm **all jobs succeeded**, then **watch the Deploy workflow** that GitHub starts when that CI run **completes** (on **`main`**, the gate deploys only after **successful** CI). Either **report both green** or **debug, fix, `/commit`, and push** in a loop until CI passes (and deploy passes on the next cycle) or a hard blocker remains.

| Stage | Workflow file | `name` in Actions |
|-------|----------------|-------------------|
| 1 | [`.github/workflows/ci.yml`](../../../.github/workflows/ci.yml) | **CI** |
| 2 | [`.github/workflows/deploy-backend.yml`](../../../.github/workflows/deploy-backend.yml) | **Deploy** |

`Deploy` uses `on.workflow_run` for **`CI`** with `types: [completed]`, so a **Deploy** run is queued as soon as **CI** finishes (success or failure). This skill’s **default** is to watch **Deploy** only after **CI** **succeeds**, because that is when real deploy jobs run; if **CI** fails, skip deploy watching unless the user explicitly wants closure on the skipped gate run.

SPA deploys run only via **[`deploy-backend.yml`](../../../.github/workflows/deploy-backend.yml)** after CI; there is no separate manual web workflow.

## Preconditions

1. **Repository root** — Run `gh` and `git` from the clone that was pushed.
2. **GitHub CLI** — Resolve `gh` per [`.cursor/skills/github-cli/SKILL.md`](../github-cli/SKILL.md) (Windows: full path to `gh.exe` when PATH is minimal).
3. **Auth** — `gh auth status` must succeed; if not, say what blocked (SSO, login) after the CLI reports it.
4. **Branch** — For post-push monitoring, the pushed branch should be the one that triggered CI (here: **`main`** on push).

## When to run

- Immediately after **`git push`** when the user asked to **watch CI**, **wait for CI**, **wait for deploy**, or **fix until green**.
- When the user reports **CI or Deploy failed on GitHub** and wants it **fixed and pushed**.

Prefer execution over asking the user to open the Actions UI; use [`.cursor/skills/use-cli/SKILL.md`](../use-cli/SKILL.md) and the GitHub/AWS leaf skills for queries and logs.

## Step 1 — Identify the CI run to watch

After a push, the newest run for this workflow is usually correct. Prefer **JSON** for stable parsing:

```bash
gh run list --workflow ci.yml --branch "$(git rev-parse --abbrev-ref HEAD)" --limit 5 --json databaseId,status,conclusion,name,displayTitle,createdAt,url
```

Pick the **most recent** run that matches the push (same branch, recent `createdAt`). If nothing appears yet, **wait a few seconds** and list again (Actions scheduling delay).

**Run id** below means `databaseId` from that JSON.

## Step 2 — Watch CI until completion

Block until the run finishes, and propagate failure to the agent:

```bash
gh run watch <CI_RUN_ID> --exit-status
```

- **Exit code 0** — CI completed successfully → go to **Step 3** (deploy).
- **Non-zero** — CI failed or was cancelled → go to **CI failure** below.

**Alternative** if `watch` is unsuitable: poll with `gh run view <CI_RUN_ID> --json status,conclusion` until `status` is `completed`, then treat `conclusion == success` as success.

## Step 3 — After CI success: find and watch Deploy

1. **Head SHA** — Same commit as CI (used to pick the correct Deploy run among concurrent activity):
   ```bash
   gh run view <CI_RUN_ID> --json headSha,url,displayTitle,conclusion -q .
   ```
2. **Resolve the Deploy run** — List recent **`deploy-backend.yml`** runs and take the newest whose **`headSha`** equals the CI run’s **`headSha`**:
   ```bash
   gh run list --workflow deploy-backend.yml --limit 20 --json databaseId,headSha,status,conclusion,displayTitle,createdAt,url
   ```
   If no row matches yet, **wait a few seconds** and repeat ( **`workflow_run`** can be delayed).
3. **Watch Deploy**:
   ```bash
   gh run watch <DEPLOY_RUN_ID> --exit-status
   ```
   - **Exit code 0** — go to **Pipeline success** below.
   - **Non-zero** — go to **Deploy failure** below.

## Pipeline success

1. Confirm **CI** passed and **Deploy** passed (workflow names, branch, conclusions).
2. Optionally paste both run **URLs** (`gh run view <id> --json url -q .url`).
3. **Continue** with any follow-on work the user requested.

## CI failure (debug → fix → commit → push)

1. **Logs** — Inspect what broke (job names match `ci.yml`):
   ```bash
   gh run view <CI_RUN_ID> --log-failed
   ```
   If that is insufficient:
   ```bash
   gh run view <CI_RUN_ID> --log
   ```
2. **Reproduce locally** — Mirror the failing job (frontend, lambda, CloudFormation parse, actionlint, unit tests) using the same commands as in [`.cursor/skills/commit/SKILL.md`](../commit/SKILL.md) **Step 2** (CI parity, excluding `integ-tests-static` unless the failure is clearly in integration — then run the integration checks from `ci.yml` for that job).
3. **Use CLIs** — For AWS-side causes (deploy role, stack, etc.), follow [`.cursor/skills/use-cli/SKILL.md`](../use-cli/SKILL.md) and [`.cursor/skills/aws-cli/SKILL.md`](../aws-cli/SKILL.md) where relevant. For GitHub-side causes (permissions, workflow, org policy), use `gh api`, `gh run view`, and repo workflow files — not the browser — unless blocked.
4. **Implement fixes** — Minimal, targeted code or config changes.
5. **Commit** — Read and follow [`.cursor/skills/commit/SKILL.md`](../commit/SKILL.md) in full: analyze diff, run the same **CI parity** gates, split logical commits, conventional messages. **Push** is expected in this skill’s loop (see **Push** below).
6. **Push** — `git push` (no `--force` unless the user explicitly asked). Then return to **Step 1** with a **new** CI run id for the new commit (then **Step 3** deploy again when CI is green).
7. **Stop with a clear report** if after a fix the failure is **outside the repo** (org policy, secrets not available to the agent, flaky infrastructure) after one retry cycle — say what the user must change.

## Deploy failure

1. **Logs** — Deploy jobs live in **`deploy-backend.yml`**:
   ```bash
   gh run view <DEPLOY_RUN_ID> --log-failed
   ```
   Broaden with `gh run view <DEPLOY_RUN_ID> --log` if needed.
2. **Diagnose** — Often **AWS** (OIDC role, stack, CloudFormation, S3, Lambda). Use [`.cursor/skills/aws-cli/SKILL.md`](../aws-cli/SKILL.md) and [`.cursor/skills/use-cli/SKILL.md`](../use-cli/SKILL.md). Workflow **`if:`** / gate logic is in-repo; misconfiguration can be fixed like CI failures.
3. **Fix and re-run the pipeline** — If the fix is in the repo: implement minimally, **`/commit`** (CI parity where applicable), **push**, then restart from **Step 1** (new CI → new Deploy). If the fix is **only** in AWS (console/IAM), say so clearly after one attempt.

## Push

- **This skill assumes push is allowed** when the user invoked it for “watch CI after push” / “fix CI and push”. Use the same **branch** they were using; do not force-push.
- If the user only asked to **watch** without permission to push, **stop after reporting** and ask before pushing.

## Safety (align with `commit` and `github-cli` skills)

- Do **not** `git push --force` or rewrite remote history unless the user explicitly requests it.
- Do **not** skip git hooks (`--no-verify`) unless the user explicitly requests it.
- Do **not** commit secrets (`.env`, credentials); warn if asked.
- **Never** update `git config` for the user.

## Summary checklist

- [ ] Resolve `gh` and confirm auth.
- [ ] List/watch the correct **`ci.yml`** run for the current branch.
- [ ] On **CI** success: resolve **`deploy-backend.yml`** run by matching **`headSha`**, **`gh run watch`** deploy.
- [ ] On **CI** failure: logs → local repro → **commit** skill (full CI parity) → **push** → re-watch from Step 1.
- [ ] On **Deploy** failure: logs → AWS/workflow diagnosis → repo fix + push if applicable.
- [ ] Stop on unrecoverable external blockers with a concise handoff.
