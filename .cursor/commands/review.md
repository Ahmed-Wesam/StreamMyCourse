---
description: Code review mindset — findings by severity only; no fixes unless requested
---

Review the relevant code with a code review mindset. Prioritize bugs, behavioral regressions, security issues, and missing tests. Findings must be the primary focus, ordered by severity. Do not make code changes unless the user explicitly asks for them.

Edits applied: do **not** list severity-ranked findings (Critical/Medium/Low) whose only rationale is a hypothetical future change—for example “if callers later switch tokens,” “if someone misconfigures X later,” unless the user explicitly asks for speculative or roadmap risk review. Omit those. If something is still worth a single note and is unsupported by today’s codebase or imminent in-repo intent, optionally add **at the end**, with **no severity label**: `Out of scope (not counted as findings): …` — otherwise omit entirely.
