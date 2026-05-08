---
description: Code review mindset — findings by severity only; no fixes unless requested
---

Review the relevant code with a code review mindset. Prioritize bugs, behavioral regressions, security issues, and missing tests. Findings must be the primary focus, ordered by severity. Do not make code changes unless the user explicitly asks for them.

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

### Allowed optional tail (never severity-ranked)

If something peripheral is unsupported by today’s codebase or imminent in-repo intent, optionally add **at the end**, with **no severity label**:

`Out of scope (not counted as findings): …`

Otherwise omit entirely.

### Legacy shorthand (still in force)

Do **not** list severity-ranked findings whose **only** rationale is a hypothetical future change—for example “if callers later switch tokens,” “if someone misconfigures X later,” unless the user explicitly asks for speculative or roadmap risk review.
