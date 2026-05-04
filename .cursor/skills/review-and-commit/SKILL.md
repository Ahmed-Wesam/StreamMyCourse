---
name: review-and-commit
description: >-
  Runs a code review on pending changes (bugs, regressions, security, missing tests;
  findings by severity), implements fixes for issues found, then performs the /commit
  workflow (CI-parity checks, conventional commits, /update-docs when warranted).
  Use when the user invokes /review_and_commit or asks to review then commit without pushing.
disable-model-invocation: true
---

# /review_and_commit

Combine **code review** and **`/commit`** in one workflow: review first, fix what the review finds, then commit—**without** `git push` unless the user also explicitly asks to push in the same message.

**Invocation counts as explicit consent to commit** after the review phase passes (overrides the generic “only commit when asked” caution in the commit skill for this session only).

## Phase 1 — Review

1. **Scope** — Use `git status`, `git diff`, and read touched files as needed. Focus on what changed in this working tree / branch.

2. **Mindset** — Code review: prioritize **bugs**, **behavioral regressions**, **security**, and **missing or inadequate tests**.

3. **Output** — Report findings as the **primary** content, **ordered by severity** (critical first). Keep narrative minimal; findings matter most.

4. **Fixes** — If there are issues worth fixing, **implement the fixes** in the repo (tests or code as appropriate). Do not stop at advice unless the issue truly needs a product decision.

5. **Loop** — Re-check the changed code after edits (quick second pass or targeted re-review). Repeat until there are **no remaining issues** you would block on for merge—or until only documented acceptable risks remain.

6. **No drive-by scope** — Fix only what the review surfaces or what is required for those fixes; do not expand unrelated refactors.

## Phase 2 — Commit (`/commit`)

When Phase 1 is complete, follow **[`.cursor/skills/commit/SKILL.md`](../commit/SKILL.md)** end-to-end:

- Analyze changes, **CI parity** checks (same as `ci.yml` jobs: frontend, lambda, cloudformation, workflow-lint, lambda-unit-tests; **not** `integ-tests-static`), group commits, conventional messages, **`/update-docs`** when warranted.
- Obey **Git safety** and **never push** rules from that skill.

**Push:** Do **not** run `git push` unless the user explicitly requested push in the same instruction or a clear follow-up.

## Quick reference — Review severity ordering

1. **Critical / high** — Correctness bugs, security flaws, data loss, broken auth or trust boundaries.
2. **Medium** — Regressions, wrong API contracts, error-handling gaps that surface to users.
3. **Lower** — Tests, clarity, minor consistency—still address when they affect maintainability or coverage of new behavior.

---

When the user only wanted review without commit, they should use a plain review request—not this skill.
