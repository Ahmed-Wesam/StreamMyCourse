---
name: github-cli
description: Runs GitHub operations via the gh CLI in the terminal instead of delegating browser or manual steps to the user. Use for pull requests, issues, Actions workflow runs, releases, repository metadata, and any task that would otherwise say open GitHub or click in the UI.
disable-model-invocation: false
---

# /github-cli

Use the **GitHub CLI** to complete GitHub-hosted work in the shell. Prefer running it yourself over asking the user to open the website, copy links, or click through unless the action is impossible or unsafe without their explicit intent.

## Executable path (do not rely on PATH alone)

Cursor agents on **Windows** often run with a minimal PATH where `gh` is not found even when GitHub CLI is installed. **Resolve the binary explicitly** before running subcommands.

**Windows (PowerShell)** — default GitHub CLI install location:

```powershell
$gh = Join-Path $env:ProgramFiles 'GitHub CLI\gh.exe'
if (-not (Test-Path -LiteralPath $gh)) {
  $found = (where.exe gh 2>$null | Select-Object -First 1)
  if ($found) { $gh = $found } else { $gh = 'gh' }
}
```

Then run commands as `& $gh <subcommand> ...` (for example `& $gh auth status`).

**macOS / Linux** — try `/usr/local/bin/gh`, `/opt/homebrew/bin/gh`, or `command -v gh` if bare `gh` fails.

In examples below, **`gh` means the resolved executable** (`& $gh` on Windows PowerShell, or the same path in one line).

## Principles

1. **Default to execution** — If a task maps to a `gh` command (or `gh api`), run it from the project repo (or the relevant clone) and report the outcome.
2. **Non-interactive flags** — Use flags that avoid prompts where supported (for example `--title`, `--body`, `--fill`, `--yes`, `--json` with a field list) so automation does not hang.
3. **Same safety as git** — Do not `git push --force` or rewrite remote history unless the user explicitly requests it. Do not merge PRs, delete branches, or close issues unless the user asked for that outcome.
4. **Secrets** — Never paste tokens into chat or commit them. Rely on `gh auth` (via the resolved `gh` binary) and environment/GitHub Actions secrets; do not ask the user to expose credentials for convenience.

## Preconditions

- **CLI available** — After resolving `$gh` (or equivalent), if the binary does not exist and `where.exe gh` finds nothing, say to install [GitHub CLI](https://cli.github.com/) or fix the install path; do not loop silently.
- **Auth** — Run `auth status` via the resolved binary (for example `& $gh auth status` on Windows PowerShell; on Unix use the full path or `command -v gh`). If not logged in, run `auth login` the same way only when the session can complete it (otherwise tell the user to run it once in a terminal they control). For operations that need SSO or device approval, say what is blocking after the CLI reports it.

## Common mappings (prefer these over “please do X on GitHub”)

| Goal | Typical commands (prefix with `& $gh` on Windows PowerShell) |
|------|-------------------|
| Current repo / default branch | `gh repo view --json nameWithOwner,defaultBranchRef` |
| PRs for this branch | `gh pr status`, `gh pr list` |
| Inspect a PR | `gh pr view <n>`, `gh pr diff <n>`, `gh pr checks <n>` |
| Create a PR | `gh pr create` with `--title` / `--body` / `--fill` as appropriate |
| Merge (only if user asked) | `gh pr merge <n>` with the merge strategy the user wants or repo default |
| Actions runs | `gh run list`, `gh run view <id>`, `gh run watch <id>` |
| Dispatch workflow | `gh workflow run <name> -f key=value` (only if user asked) |
| Issues | `gh issue list`, `gh issue view <n>`, `gh issue create` with `--title` / `--body` |
| Arbitrary REST | `gh api repos/{owner}/{repo}/...` (discover `owner/repo` from `gh repo view` or `git remote -v`) |

Use `--json` with explicit fields when you need structured output for decisions or summaries.

## When not to substitute the GitHub CLI

- The user must approve in a browser (org policy, OAuth consent you cannot complete).
- The operation needs **their** interactive choice (which of three PRs to merge) and they did not specify — ask one short clarifying question instead of guessing.
- **Destructive or irreversible** actions (delete repo, force-push, admin branch protection) without explicit user instruction.

## Output

After GitHub CLI commands, summarize what changed or what was read (PR number, URL, check conclusion) in plain language so the user does not need to open GitHub unless they want to.
