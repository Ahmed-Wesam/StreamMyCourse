# Aurora DSQL query runbook (operator)

Ad-hoc SQL against the **`StreamMyCourse-Dsql-prod`** cluster for schema checks and investigations. Production catalog traffic still uses RDS; this database backs the preview API (`StreamMyCourse-Api-dsql`) only.

## Prerequisites

- AWS credentials with `dsql:DbConnectAdmin` on the cluster ARN (GitHub deploy role or local **Admin** user).
- Region **`eu-west-1`** unless your stack says otherwise.
- **psql 14+** (or another libpq client that sends TLS SNI). Older psql builds often fail against Aurora DSQL endpoints.
- Python path: repo `scripts/apply-dsql-schema.py` and `scripts/dsql_orphan_audit.py` use the same IAM token flow as Lambdas.

Resolve the endpoint:

```powershell
aws cloudformation describe-stacks --stack-name StreamMyCourse-Dsql-prod --region eu-west-1 --query "Stacks[0].Outputs[?OutputKey=='Endpoint'].OutputValue" --output text
```

Set it for the session (hostname only, no secrets in chat logs):

```powershell
$env:DSQL_ENDPOINT = "<identifier>.dsql.eu-west-1.on.aws"
```

## Connect with psql

Generate a short-lived admin token (default lifetime 15 minutes). **Do not paste the token into tickets, CI logs, or chat.**

```powershell
$token = aws dsql generate-db-connect-admin-auth-token --hostname $env:DSQL_ENDPOINT --region eu-west-1
$env:PGPASSWORD = $token
psql "host=$($env:DSQL_ENDPOINT) port=5432 dbname=postgres user=admin sslmode=require"
```

Inside psql:

```sql
SET search_path TO app;
SELECT 1;
```

Runtime Lambdas use IAM user **`smc_app`** (`dsql:DbConnect`, not admin). Operators troubleshooting app rows should prefer read-only `SELECT` as admin with `search_path=app`.

## Python helpers

From the repository root (after `pip install psycopg2-binary aurora-dsql-python-connector`):

```powershell
$env:DSQL_ENDPOINT = "<hostname>"
python scripts/dsql_orphan_audit.py
```

A zero-finding run prints `dsql_orphan_audit: 0 findings` and exits **0**.

Integration tests use `tests/integration/helpers/dsql_audit.py` (`admin_connect`, `fk_orphan_counts`, `run_transaction` re-export). Those helpers resolve `DSQL_ENDPOINT` or the CloudFormation **Endpoint** output; they never print tokens.

## Safety

- No cluster resource policy changes from this runbook.
- Do not log tokens, passwords, or full DSN strings. Logging **endpoint hostname** and **token length** is enough.
- Prefer read-only SQL. DDL uses `scripts/apply-dsql-schema.py` (one statement per transaction, async index waits).
- The foundation gate must not upload to the shared media bucket or enqueue prod cleanup messages.

## Related

- Schema: `infrastructure/database/dsql/0001_schema.sql`
- Apply: `scripts/apply-dsql-schema.py`
- Agent skill: `.cursor/skills/query-dsql/SKILL.md`
