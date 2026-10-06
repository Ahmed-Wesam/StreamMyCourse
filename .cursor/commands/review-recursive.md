---
description: Review, fix every real finding, and repeat until a pass is clean
---

Review the relevant code, fix every real finding, then review again. Repeat until a full pass reports no findings. Do not stop after one fix cycle.

No nits. Only real findings backed by data. Do not commit or push.

## Evidence only (no hypothetical severity findings)

**Do not invent merge-blocking noise.** Severity labels (**Critical**, **Medium**, **Low**, etc.) are **only** for findings you can defend with **concrete evidence**:

- Something **wrong or inconsistent in the actual diff or current repo** (cite paths; point to specific logic, guards, wiring, or tests).
- A **broken contract** versus existing in-repo callers, tests, or docs you actually read—not “some client might…”
- A **demonstrated** bug path (logical contradiction, missing check on a branch that exists today, failing test scenario implied by assertions already in-repo).

If you lack evidence and are **guessing** (e.g. “API Gateway might 403,” “later someone might pass an access token,” “operators might misconfigure X”), **do not** attach **any** severity label to it. Omit it entirely unless the user explicitly asked for speculative or roadmap-risk review—in that narrow case you may brief it **without** severity, under **Out of scope (not counted as findings):** below.

When uncertain after reading the code: say **you found no issue** or ask **one** factual clarifying question—do **not** pad the review with a **Medium/Low** “just in case” bullet.

### Anti-patterns (refuse these as severity-ranked findings)

- Rationale that is essentially **“if \<future change outside this diff\> …”**.
- Hand-wavy dependency on external behavior **not shown** via failing test, log, or pinned doc—you did not reproduce or cite a failing line in code/tests.
- **Same concern restated** as both “might happen” and “verify in CI”; pick one: either it is proven (severity) or it is omitted.
- Nits: naming taste, formatting, comments, drive-by refactors, and “could be cleaner” notes with no broken behavior, broken contract, security hole, or missing test that the diff’s behavior requires.

### Allowed optional tail (never severity-ranked)

If something peripheral is unsupported by today’s codebase or imminent in-repo intent, optionally add **at the end**, with **no severity label**:

`Out of scope (not counted as findings): …`

Otherwise omit entirely. Out-of-scope notes are **not** findings and must **not** be fixed in this loop.

### Legacy shorthand (still in force)

Do **not** list severity-ranked findings whose **only** rationale is a hypothetical future change—for example “if callers later switch tokens,” “if someone misconfigures X later,” unless the user explicitly asks for speculative or roadmap risk review.

## Loop

1. **Scope** — Use `git status`, `git diff`, and read the touched files. Review the working tree and branch changes, including fixes from earlier passes in this run.
2. **Review** — Prioritize bugs, behavioral regressions, security issues, and missing tests. Order findings by severity. Each finding needs a path and the evidence you read or ran.
3. **Cost impact** — After the findings, follow **`.cursor/rules/review-aws-cost-alerts.mdc`**: add **`## Cost impact`**. Use **None identified in this diff.** when no paid always-on resources are added or materially changed. Cost notes are not severity-ranked findings; do not “fix” spend unless the diff introduced a concrete cost bug you can prove.
4. **Fix** — If this pass has severity-ranked findings, implement the fixes (code and tests as appropriate). Fix only what this pass proved. Do not expand into unrelated refactors.
5. **Repeat** — Re-review the updated diff from scratch. A previous “fixed” note is not proof the next pass is clean. Do not lower the evidence bar on later passes to invent findings, and do not raise it to skip a bug you can still prove.
6. **Stop** — End only when a full pass has **zero** severity-ranked findings, or when a fix needs a product decision you cannot make. In that case stop, report the open finding with evidence, and ask one question. Do not guess.

## Output

For each pass, lead with the findings (or **No findings.**), then **`## Cost impact`**.

When the loop ends, state how many passes you ran, what you fixed, and that the last pass had no findings. Do not commit or push.