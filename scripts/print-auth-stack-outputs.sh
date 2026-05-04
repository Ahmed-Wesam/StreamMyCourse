#!/usr/bin/env bash
# Print Cognito auth stack outputs and map to GitHub secrets / .env (POSIX; aws CLI only).
# Usage: ./scripts/print-auth-stack-outputs.sh [dev|prod] [region]
set -euo pipefail
ENV="${1:-dev}"
REGION="${2:-eu-west-1}"
case "$ENV" in dev | prod) ;; *)
  echo "Usage: $0 [dev|prod] [region]" >&2
  exit 1
  ;;
esac
STACK="StreamMyCourse-Auth-${ENV}"

q() {
  aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue | [0]" --output text
}

user_pool_id="$(q UserPoolId)"
student_id="$(q StudentUserPoolClientId)"
teacher_id="$(q TeacherUserPoolClientId)"
hosted="$(q HostedUIDomain)"

echo ""
echo "=== CloudFormation: $STACK ($REGION) ==="
echo "UserPoolId                  : $user_pool_id"
echo "StudentUserPoolClientId     : $student_id"
echo "TeacherUserPoolClientId     : $teacher_id"
echo "HostedUIDomain              : $hosted"
echo ""
echo "=== GitHub Actions secrets ==="
echo "VITE_COGNITO_USER_POOL_ID       = $user_pool_id"
echo "VITE_COGNITO_STUDENT_CLIENT_ID  = $student_id"
echo "VITE_COGNITO_TEACHER_CLIENT_ID  = $teacher_id"
echo "VITE_COGNITO_DOMAIN             = $hosted"
echo ""
echo "=== frontend/.env (local; do not commit) ==="
echo "VITE_COGNITO_USER_POOL_ID=$user_pool_id"
echo "VITE_COGNITO_USER_POOL_CLIENT_ID=$student_id"
echo "VITE_COGNITO_DOMAIN=$hosted"
echo ""
echo "Next: set GitHub Environment secrets, then push main (Deploy workflow rebuilds both SPAs)."
