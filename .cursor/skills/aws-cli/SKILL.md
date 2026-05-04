---
name: aws-cli
description: Fetches AWS resource IDs, ARNs, endpoints, and stack outputs via the AWS CLI instead of asking the user to open the console, find values, and paste them into chat. Use when Cognito, CloudFormation, S3, Lambda, IAM, or regional settings are needed for local env, debugging, or docs—and whenever a value exists in AWS and can be queried non-interactively.
disable-model-invocation: false
---

# /aws-cli

Use the **AWS CLI** to obtain values the agent needs. Prefer running it yourself over asking the user to open the AWS console, locate a field, and paste it into the session.

## Executable path (do not rely on PATH alone)

Cursor agents on **Windows** often run with a minimal PATH where `aws` is not found even when AWS CLI v2 is installed. **Resolve the binary explicitly** before running subcommands.

**Windows (PowerShell)** — default AWS CLI v2 location (call with `&` because the path contains spaces if you ever use `Program Files` literally):

```powershell
$aws = Join-Path $env:ProgramFiles 'Amazon\AWSCLIV2\aws.exe'
if (-not (Test-Path -LiteralPath $aws)) {
  $found = (where.exe aws 2>$null | Select-Object -First 1)
  if ($found) { $aws = $found } else { $aws = 'aws' }
}
```

Then run commands as `& $aws <subcommand> ...` (for example `& $aws sts get-caller-identity`).

**macOS / Linux** — try full paths if `aws` is missing: `/usr/local/bin/aws`, `/opt/homebrew/bin/aws`, or `command -v aws`.

In examples below, **`aws` means the resolved executable** (`& $aws` on Windows PowerShell, or the same path in one line).

## Principles

1. **Default to execution** — If a value is discoverable with the AWS CLI (describe/list/get/query), run the command from the user’s machine (or the documented profile/region) and use the output.
2. **Non-interactive** — Use `--output json` or `--output text`, `--query` (JMESPath), and avoid commands that open a browser or require TTY unless the user already chose that flow.
3. **Region and profile** — Respect `AWS_REGION`, `AWS_DEFAULT_REGION`, and `AWS_PROFILE` if set. Otherwise pick the region the repo uses (this project: commonly `eu-west-1`) or infer from stack/script names; if ambiguous, run `configure list` and `sts get-caller-identity` once via the **resolved** binary (Windows PowerShell: `& $aws ...`; Unix: `"$(command -v aws)" ...` or a known full path).
4. **Secrets** — Do not paste long-lived secrets into chat or commit them. Prefer referencing secret names/ARNs. For one-off verification, use CLI output locally and redact when summarizing.

## Preconditions

- **CLI available** — After resolving `$aws` (or equivalent), if the binary does not exist and `where.exe aws` finds nothing, say to install [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html); do not pretend values were fetched.
- **Auth** — Run `sts get-caller-identity` via the resolved binary (for example `& $aws sts get-caller-identity` on Windows PowerShell). If it fails, report the error; only ask the user to run SSO / `aws sso login` / keys when the CLI indicates auth is the blocker.

## Common mappings (prefer these over “please copy from the console”)

| Goal | Typical commands (prefix with `& $aws` on Windows PowerShell) |
|------|------------------|
| Account / principal | `aws sts get-caller-identity` |
| CloudFormation stack outputs | `aws cloudformation describe-stacks --stack-name <name> --query 'Stacks[0].Outputs'` |
| Single output value | `aws cloudformation describe-stacks --stack-name <name> --query "Stacks[0].Outputs[?OutputKey=='<Key>'].OutputValue \| [0]" --output text` |
| List stacks (name discovery) | `aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE --query 'StackSummaries[].StackName'` |
| SSM Parameter Store | `aws ssm get-parameter --name <path> --with-decryption` (only when decryption is appropriate) |
| S3 bucket / object metadata | `aws s3api head-bucket --bucket <name>`, `aws s3 ls s3://...` |
| Lambda function config | `aws lambda get-function --function-name <name>` |
| Cognito pools (when not from CF outputs) | `aws cognito-idp list-user-pools --max-results 20` (then describe as needed) |

## This repository

- Auth stack outputs (Cognito user pool, clients, hosted UI) for **dev** / **prod**: run `scripts/print-auth-stack-outputs.sh` (POSIX) or `scripts/print-auth-stack-outputs.ps1` (Windows). Stack name pattern: `StreamMyCourse-Auth-<env>`.
- Prefer these scripts when the task is “fill `.env` / secrets from the auth stack” so output stays aligned with documented variable names.

## When the CLI is not enough

- **Console-only or human approval** — Reserved capacity purchases, some support cases, or actions that require console MFA in a way the CLI cannot mirror: say what is blocked and the smallest user action needed.
- **No permission** — If `AccessDenied` appears, report the missing API/action; do not ask the user to paste IAM policy JSON unless they offered to share it for debugging.
