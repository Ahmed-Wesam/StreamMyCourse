#!/usr/bin/env bash
# RS-16 prod seed. One SQL statement per invoke. Never prints SQL, user subs, or tokens.
#
# Usage (from PowerShell):
#   bash -lc 'cd /c/Users/ahmad/CascadeProjects/StreamMyCourse; ./scripts/rs16-seed/run_seed.sh'

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-eu-west-1}}"
FUNCTION="StreamMyCourse-RdsQuery-prod"
NEED_DISABLE=0
SKIP_STUDENT=0
WORKDIR="$(mktemp -d)"

AWS_DIR="/c/Program Files/Amazon/AWSCLIV2"
if [[ -d "$AWS_DIR" ]]; then
  export PATH="$AWS_DIR:$PATH"
fi

if command -v aws >/dev/null 2>&1; then
  AWS="aws"
else
  echo "[rs16-seed] aws CLI not found" >&2
  exit 1
fi

PYTHON="python"
if ! command -v python >/dev/null 2>&1; then
  PYTHON="python3"
fi

cleanup() {
  local status=$?
  rm -rf "$WORKDIR"
  if [[ "$NEED_DISABLE" == "1" ]]; then
    echo "[rs16-seed] setting ALLOW_MUTATING_SQL=false"
    ALLOW_MUTATING_SQL=false "$ROOT/scripts/deploy-rds-query-stack.sh" prod \
      || echo "[rs16-seed] disable deploy failed" >&2
  fi
  exit "$status"
}
trap cleanup EXIT

invoke_sql() {
  local sql_file="$1"
  local mode="$2"
  local payload="$WORKDIR/payload.json"
  local outfile="$WORKDIR/out.json"
  "$PYTHON" - "$sql_file" "$payload" "$mode" <<'PY'
import json, sys
sql = open(sys.argv[1], encoding="utf-8").read()
payload = {"confirm": "prod", "sql": sql}
if sys.argv[3] == "mutate":
    payload["allow_mutating_sql"] = True
with open(sys.argv[2], "w", encoding="utf-8") as handle:
    json.dump(payload, handle, ensure_ascii=False)
PY
  payload_arg="$(cygpath -m "$payload")"
  outfile_arg="$(cygpath -m "$outfile")"
  "$AWS" lambda invoke \
    --function-name "$FUNCTION" \
    --cli-binary-format raw-in-base64-out \
    --payload "fileb://${payload_arg}" \
    "$outfile_arg" \
    --region "$REGION" \
    --cli-read-timeout 120 \
    --no-cli-pager >/dev/null
  "$PYTHON" "$ROOT/scripts/rs16-seed/summarize_invoke.py" "$outfile" "$mode"
}

write_sql() {
  local dest="$1"
  local sql="$2"
  "$PYTHON" - "$dest" "$sql" <<'PY'
import sys
open(sys.argv[1], "w", encoding="utf-8").write(sys.argv[2])
PY
}

echo "[rs16-seed] checking teacher user row"
write_sql "$WORKDIR/teacher.sql" \
  "SELECT COUNT(*)::int AS teacher_count FROM users WHERE email = 'ci-rds-verify@noreply.local'"
teacher_summary="$(invoke_sql "$WORKDIR/teacher.sql" count)"
echo "[rs16-seed] teacher $teacher_summary"
teacher_n="$("$PYTHON" -c "import sys; text=sys.argv[1]; key='teacher_count='; i=text.find(key); print('' if i<0 else text[i+len(key):].split()[0])" "$teacher_summary")"
if [[ -z "$teacher_n" || "$teacher_n" == "0" ]]; then
  echo "[rs16-seed] stopped: ci-rds-verify@noreply.local is missing from users" >&2
  exit 1
fi

echo "[rs16-seed] checking student user row"
write_sql "$WORKDIR/student.sql" \
  "SELECT COUNT(*)::int AS student_count FROM users WHERE email = 'ci-student@noreply.local'"
student_summary="$(invoke_sql "$WORKDIR/student.sql" count)"
echo "[rs16-seed] student $student_summary"
student_n="$("$PYTHON" -c "import sys; text=sys.argv[1]; key='student_count='; i=text.find(key); print('' if i<0 else text[i+len(key):].split()[0])" "$student_summary")"
if [[ -z "$student_n" || "$student_n" == "0" ]]; then
  SKIP_STUDENT=1
  echo "[rs16-seed] student rows not done: ci-student@noreply.local is missing from users"
fi

echo "[rs16-seed] enabling ALLOW_MUTATING_SQL"
ALLOW_MUTATING_SQL=true "$ROOT/scripts/deploy-rds-query-stack.sh" prod
NEED_DISABLE=1

echo "[rs16-seed] generating statements"
"$PYTHON" "$ROOT/scripts/rs16-seed/build_seed_sql.py" "$WORKDIR/sql"

manifest="$WORKDIR/sql/manifest.json"
count="$("$PYTHON" -c "import json,sys; print(len(json.load(open(sys.argv[1],encoding='utf-8'))))" "$manifest")"
echo "[rs16-seed] statement_count=$count"

index=0
while IFS= read -r line; do
  index=$((index + 1))
  kind="$(printf '%s\n' "$line" | "$PYTHON" -c "import json,sys; print(json.loads(sys.stdin.read())['kind'])")"
  file="$(printf '%s\n' "$line" | "$PYTHON" -c "import json,sys; print(json.loads(sys.stdin.read())['file'])")"
  if [[ "$SKIP_STUDENT" == "1" && ( "$kind" == "purchase" || "$kind" == "progress" || "$kind" == "certificate" ) ]]; then
    echo "[rs16-seed] statement $index kind=$kind skipped"
    continue
  fi
  if ! summary="$(invoke_sql "$WORKDIR/sql/$file" mutate)"; then
    echo "[rs16-seed] statement $index kind=$kind failed $summary" >&2
    exit 1
  fi
  echo "[rs16-seed] statement $index kind=$kind $summary"
done < <("$PYTHON" -c "import json,sys; [print(json.dumps(item)) for item in json.load(open(sys.argv[1],encoding='utf-8'))]" "$manifest")

echo "[rs16-seed] setting ALLOW_MUTATING_SQL=false"
ALLOW_MUTATING_SQL=false "$ROOT/scripts/deploy-rds-query-stack.sh" prod
NEED_DISABLE=0

if [[ -f "$ROOT/.env.local" ]]; then
  sed 's/\r$//' "$ROOT/.env.local" >"$WORKDIR/env.local"
  set -a
  # shellcheck disable=SC1091
  source "$WORKDIR/env.local"
  set +a
  rm -f "$WORKDIR/env.local"
fi

API_BASE="$("$AWS" cloudformation describe-stacks \
  --stack-name StreamMyCourse-Api-prod \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
  --output text)"
export RS16_API_BASE="${API_BASE%/}"

if [[ -z "${LOCAL_COGNITO_PASSWORD:-}" ]]; then
  echo "[rs16-seed] quiz_assignment=not_done jwt_mint_failed"
else
  USER_POOL_ID="$("$AWS" cloudformation describe-stacks \
    --stack-name StreamMyCourse-Auth-prod \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" \
    --output text)"
  CLIENT_ID="$("$AWS" cloudformation describe-stacks \
    --stack-name StreamMyCourse-Auth-prod \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='TeacherUserPoolClientId'].OutputValue" \
    --output text)"
  export RS16_USER_POOL_ID="$USER_POOL_ID"
  export RS16_CLIENT_ID="$CLIENT_ID"
  auth_json="$WORKDIR/auth.json"
  "$PYTHON" - "$auth_json" <<'PY'
import json, os, sys
payload = {
    "UserPoolId": os.environ["RS16_USER_POOL_ID"],
    "ClientId": os.environ["RS16_CLIENT_ID"],
    "AuthFlow": "ADMIN_USER_PASSWORD_AUTH",
    "AuthParameters": {
        "USERNAME": os.environ.get("LOCAL_COGNITO_USERNAME", "ci-rds-verify@noreply.local"),
        "PASSWORD": os.environ["LOCAL_COGNITO_PASSWORD"],
    },
}
with open(sys.argv[1], "w", encoding="utf-8") as handle:
    json.dump(payload, handle)
PY
  token_file="$WORKDIR/token.txt"
  auth_arg="$(cygpath -m "$auth_json")"
  if "$AWS" cognito-idp admin-initiate-auth \
    --cli-input-json "file://${auth_arg}" \
    --region "$REGION" \
    --query "AuthenticationResult.IdToken" \
    --output text >"$token_file" 2>"$WORKDIR/auth.err"; then
    RS16_TEACHER_JWT="$(tr -d '\r\n' <"$token_file")"
    rm -f "$token_file" "$auth_json"
    if [[ -n "$RS16_TEACHER_JWT" && "$RS16_TEACHER_JWT" != "None" ]]; then
      export RS16_TEACHER_JWT
      "$PYTHON" "$ROOT/scripts/rs16-seed/seed_quiz_assignment.py" \
        || echo "[rs16-seed] quiz_assignment=failed"
      unset RS16_TEACHER_JWT
    else
      echo "[rs16-seed] quiz_assignment=not_done jwt_mint_failed"
    fi
  else
    rm -f "$token_file" "$auth_json"
    echo "[rs16-seed] quiz_assignment=not_done jwt_mint_failed"
  fi
  unset RS16_USER_POOL_ID RS16_CLIENT_ID
fi

echo "[rs16-seed] verifying catalog"
write_sql "$WORKDIR/verify_courses.sql" \
  "SELECT title, status, price_amount_minor FROM courses WHERE title IN ('Research Methodology', 'Statistics & SPSS', 'Scientific Writing', 'Systematic Reviews & Meta-Analysis', 'IGCSE Computer Science') ORDER BY title"
invoke_sql "$WORKDIR/verify_courses.sql" rows

write_sql "$WORKDIR/verify_counts.sql" \
  "SELECT c.title, (SELECT COUNT(*) FROM course_modules m WHERE m.course_id = c.id)::int AS modules, (SELECT COUNT(*) FROM lessons l WHERE l.course_id = c.id)::int AS lessons FROM courses c WHERE c.title IN ('Research Methodology', 'Statistics & SPSS', 'Scientific Writing', 'Systematic Reviews & Meta-Analysis') ORDER BY c.title"
invoke_sql "$WORKDIR/verify_counts.sql" rows

write_sql "$WORKDIR/verify_bundle.sql" \
  "SELECT amount_minor FROM bundle_offers WHERE environment = 'prod'"
invoke_sql "$WORKDIR/verify_bundle.sql" rows

write_sql "$WORKDIR/verify_pending.sql" \
  "SELECT COUNT(*)::int AS pending_lessons FROM lessons l JOIN courses c ON c.id = l.course_id WHERE c.title IN ('Research Methodology', 'Statistics & SPSS', 'Scientific Writing', 'Systematic Reviews & Meta-Analysis') AND l.video_key = '' AND l.video_status = 'pending' AND l.duration = 0"
invoke_sql "$WORKDIR/verify_pending.sql" count

if [[ "$SKIP_STUDENT" == "0" ]]; then
  write_sql "$WORKDIR/verify_purchase.sql" \
    "SELECT p.product_type, p.status, p.environment, p.amount_minor FROM purchases p JOIN users u ON u.user_sub = p.user_sub WHERE u.email = 'ci-student@noreply.local' AND p.product_type = 'bundle' AND p.status = 'paid'"
  invoke_sql "$WORKDIR/verify_purchase.sql" rows
  write_sql "$WORKDIR/verify_progress.sql" \
    "SELECT COUNT(*)::int AS progress_rows FROM lesson_progress lp JOIN users u ON u.user_sub = lp.user_sub WHERE u.email = 'ci-student@noreply.local' AND lp.completed = TRUE"
  invoke_sql "$WORKDIR/verify_progress.sql" count
  write_sql "$WORKDIR/verify_cert.sql" \
    "SELECT cert.credential_id, cert.status FROM certificates cert JOIN users u ON u.user_sub = cert.user_sub JOIN courses c ON c.id = cert.course_id WHERE u.email = 'ci-student@noreply.local' AND cert.status = 'valid' AND c.title = 'Research Methodology'"
  invoke_sql "$WORKDIR/verify_cert.sql" rows
fi

public_file="$WORKDIR/public_courses.json"
public_arg="$(cygpath -m "$public_file")"
curl -fsS "${RS16_API_BASE}/courses" -o "$public_arg"
"$PYTHON" - "$public_file" <<'PY'
import json, sys
rows = json.load(open(sys.argv[1], encoding="utf-8"))
if not isinstance(rows, list):
    raise SystemExit("public courses response was not a list")
titles = []
for row in rows:
    if not isinstance(row, dict):
        continue
    title = str(row.get("title") or "")
    price = row.get("priceAmountMinor")
    status = str(row.get("status") or "")
    titles.append(title)
    print("public title=" + title + " status=" + status + " price_amount_minor=" + str(price))
print("public_count=" + str(len(titles)))
required = (
    "Research Methodology",
    "Statistics & SPSS",
    "Scientific Writing",
    "Systematic Reviews & Meta-Analysis",
)
missing = [title for title in required if title not in titles]
if missing:
    raise SystemExit("missing public courses")
if "IGCSE Computer Science" in titles:
    raise SystemExit("IGCSE is still public")
PY

mut_flag="$("$AWS" lambda get-function-configuration \
  --function-name "$FUNCTION" \
  --query "Environment.Variables.ALLOW_MUTATING_SQL" \
  --output text \
  --region "$REGION" \
  --no-cli-pager)"
echo "[rs16-seed] ALLOW_MUTATING_SQL=$mut_flag"
if [[ "$mut_flag" != "false" ]]; then
  echo "[rs16-seed] ALLOW_MUTATING_SQL was not false after seed" >&2
  exit 1
fi

echo "[rs16-seed] done"
