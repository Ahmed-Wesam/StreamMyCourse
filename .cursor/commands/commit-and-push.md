---
description: Review, fix, commit, push, then watch CI and Deploy until both are green
---

Run **`/review-and-commit`**, then **`git push`**, then **`/watch-ci-after-push`**, in that order, in this session. Do not stop after commit.

**Invocation is explicit consent to commit and to push** (including later pushes in the CI/Deploy fix loop). That overrides the “do not push” rules in [`.cursor/skills/review-and-commit/SKILL.md`](../skills/review-and-commit/SKILL.md) and [`.cursor/skills/commit/SKILL.md`](../skills/commit/SKILL.md).

## 1. Review and commit

Read and follow [`.cursor/skills/review-and-commit/SKILL.md`](../skills/review-and-commit/SKILL.md) end to end (review, fix, re-review, then `/commit` including CI parity and `/update-docs` when that skill says so).

Stop before push only when that skill says to stop without committing: a product decision you cannot make, or CI-parity failures you could not fix. Report that and do not push.

## 2. Push

After step 1, push the current branch:

- Run `git push` (set upstream with `-u` only if the branch has no upstream).
- Do not `git push --force` or skip hooks (`--no-verify`) unless the user explicitly asked in this message.
- If step 1 made no new commit but the branch is ahead of its upstream, still push those commits.
- If there is nothing to commit and nothing to push, say so and stop. Do not watch an older Actions run.

## 3. Watch CI and Deploy

Read and follow [`.cursor/skills/watch-ci-after-push/SKILL.md`](../skills/watch-ci-after-push/SKILL.md) for the push from step 2.

Push is allowed in that skill’s CI/Deploy failure loop. Use the same branch. Do not force-push.
