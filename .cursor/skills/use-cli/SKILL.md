---
name: use-cli
description: >-
  Runs AWS CLI and GitHub CLI to complete investigation and routine ops instead of telling the user to open consoles, copy ARNs, or paste command output. Use when debugging CloudFormation or deploy failures, fetching stack outputs or resources, checking S3/Lambda/Cognito/IAM, inspecting GitHub Actions runs or PR checks, OIDC deploy-role questions, filling env from live stacks, or when the user says manual steps, do it yourself, stop asking me to run, use the CLI, /use-cli, or similar. On the first AWS or GitHub step in that thread, read .cursor/skills/aws-cli/SKILL.md and .cursor/skills/github-cli/SKILL.md for executable resolution and non-interactive patterns.
disable-model-invocation: false
---

# /use-cli

Meta-skill: **execute with CLIs** instead of delegating browser or copy-paste steps to the user.

## Default behavior

1. **Run first, ask second** — If the answer is queryable with `aws` or `gh` on the user machine, run it. Resolve binaries and flags per the leaf skills (Windows PATH is often minimal).
2. **Load the leaf skills** whenever AWS or GitHub hosted state matters:
   - [AWS CLI](../aws-cli/SKILL.md)
   - [GitHub CLI](../github-cli/SKILL.md)

## Scope

| Area | Prefer |
|------|--------|
| AWS | `describe-stack-events`, `describe-stacks` (outputs), `list-stacks`, S3/Lambda/Cognito/IAM describe, regional `--region` when the repo distinguishes `us-east-1` vs `eu-west-1` |
| GitHub | `gh run list`, `gh run view`, `gh pr status`, `gh pr checks`, `gh api`, repo metadata |

Use repo scripts (e.g. `scripts/print-auth-stack-outputs.ps1`) when they match the task and reduce error-prone hand-assembly of queries.

## When asking the user is appropriate

- **CLI missing** or **auth failed** after a short diagnostic (`sts get-caller-identity`, `gh auth status`) — state the fix (install, `aws sso login`, `gh auth login`).
- **AccessDenied** — report the missing IAM action or resource; do not ask for secret material.
- **Interactive-only** steps (browser-only org policy, MFA device approval the agent cannot complete).
- **Destructive or irreversible** work the user did not explicitly request (delete stack, merge PR, force push).

## Anti-patterns

- "Open the AWS console and find X" when `aws cloudformation describe-stacks` (or a narrower query) suffices.
- "Open GitHub Actions and tell me if it passed" when `gh run list` / `gh run view` suffices.
- Long instruction lists of commands for the user to run manually when the agent shell can run the same commands.

## Safety

Same constraints as the leaf skills and project rules: no secrets in chat, no force push unless asked, no merges/deletes unless asked.
