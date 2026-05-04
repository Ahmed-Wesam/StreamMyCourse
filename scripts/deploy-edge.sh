#!/usr/bin/env bash
# Deploy unified edge hosting (ACM + student + teacher S3/CloudFront/R53) in us-east-1.
# Used by .github/workflows/deploy-backend.yml (deploy-edge-dev / deploy-edge-prod).
# Required env: ROUTE53_HOSTED_ZONE_ID, STUDENT_WEB_DOMAIN, TEACHER_WEB_DOMAIN
# Optional: WEB_CERT_DOMAIN (primary name on cert; defaults to STUDENT_WEB_DOMAIN), WEB_CERT_SANS (comma-separated SANs)
# Optional: EDGE_ATTACH_CF_ALIASES=false while legacy Web/TeacherWeb CloudFront distributions still
#   hold the same alternate domain names (otherwise CloudFront returns 409). Default true.
set -euo pipefail

ENV="${1:?usage: deploy-edge.sh <dev|prod>}"
case "$ENV" in
dev | prod) ;;
*)
  echo "Environment must be dev or prod, got: $ENV" >&2
  exit 1
  ;;
esac

EDGE_REGION="us-east-1"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATES="$ROOT/infrastructure/templates"

: "${ROUTE53_HOSTED_ZONE_ID:?ROUTE53_HOSTED_ZONE_ID is required}"
: "${STUDENT_WEB_DOMAIN:?STUDENT_WEB_DOMAIN is required}"
: "${TEACHER_WEB_DOMAIN:?TEACHER_WEB_DOMAIN is required}"

CERT_PRIMARY_DOMAIN="${WEB_CERT_DOMAIN:-$STUDENT_WEB_DOMAIN}"
EDGE_STACK="StreamMyCourse-EdgeHosting-${ENV}"
ATTACH_CF_ALIASES="${EDGE_ATTACH_CF_ALIASES:-true}"

echo "=== Edge deploy: env=$ENV stack=$EDGE_STACK region=$EDGE_REGION ==="
echo "Cert primary DomainName: $CERT_PRIMARY_DOMAIN"
echo "Student web DomainName:  $STUDENT_WEB_DOMAIN"
echo "Teacher web DomainName:  $TEACHER_WEB_DOMAIN"
echo "AttachCloudFrontAliases: $ATTACH_CF_ALIASES"

EDGE_OVERRIDES=(
  "Environment=$ENV"
  "HostedZoneId=$ROUTE53_HOSTED_ZONE_ID"
  "CertPrimaryDomain=$CERT_PRIMARY_DOMAIN"
  "StudentDomainName=$STUDENT_WEB_DOMAIN"
  "TeacherDomainName=$TEACHER_WEB_DOMAIN"
  "PriceClass=PriceClass_100"
  "AttachCloudFrontAliases=$ATTACH_CF_ALIASES"
)
if [[ -n "${WEB_CERT_SANS:-}" ]]; then
  EDGE_OVERRIDES+=("SubjectAlternativeNames=$WEB_CERT_SANS")
fi

edge_deploy_dump_events() {
  echo "=== CloudFormation failure details: $EDGE_STACK ($EDGE_REGION) ===" >&2
  aws cloudformation describe-stack-events \
    --stack-name "$EDGE_STACK" \
    --region "$EDGE_REGION" \
    --query 'StackEvents[?contains(ResourceStatus, `FAILED`)].[Timestamp,LogicalResourceId,ResourceStatus,ResourceStatusReason]' \
    --output text 2>/dev/null | head -n 20 >&2 || true
  echo "=== Last 20 stack events (newest first) ===" >&2
  aws cloudformation describe-stack-events \
    --stack-name "$EDGE_STACK" \
    --region "$EDGE_REGION" \
    --max-items 20 \
    --output table 2>/dev/null >&2 || true
  ts_ms="$(date +%s)000"
  printf '%s\n' "{\"sessionId\":\"07a1cb\",\"hypothesisId\":\"H_edge_cfn\",\"location\":\"deploy-edge.sh:edge_deploy_dump_events\",\"message\":\"edge stack deploy failed\",\"data\":{\"stack\":\"$EDGE_STACK\",\"region\":\"$EDGE_REGION\"},\"timestamp\":$ts_ms}" >>"${ROOT}/debug-07a1cb.log" 2>/dev/null || true
}

echo "=== CloudFormation: $EDGE_STACK ==="
if ! aws cloudformation deploy \
  --template-file "$TEMPLATES/edge-hosting-stack.yaml" \
  --stack-name "$EDGE_STACK" \
  --region "$EDGE_REGION" \
  --capabilities CAPABILITY_IAM \
  --no-fail-on-empty-changeset \
  --parameter-overrides "${EDGE_OVERRIDES[@]}"; then
  export EDGE_STACK EDGE_REGION ROOT
  edge_deploy_dump_events
  exit 1
fi

CERT_ARN="$(aws cloudformation describe-stacks \
  --stack-name "$EDGE_STACK" \
  --region "$EDGE_REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`CertificateArn`].OutputValue' \
  --output text)"
if [[ -z "$CERT_ARN" || "$CERT_ARN" == "None" ]]; then
  echo "Failed to read CertificateArn from $EDGE_STACK" >&2
  exit 1
fi
echo "CertificateArn: $CERT_ARN"
echo "[OK] Edge hosting stack updated for $ENV"
