#!/usr/bin/env bash
# Register StreamMyCourse drm-auth webhook with Kinescope (project or workspace level).
#
# Usage:
#   KINESCOPE_API_TOKEN=... ./scripts/configure-kinescope-drm-auth.sh \
#     https://<api-id>.execute-api.<region>.amazonaws.com/dev \
#     <kinescope-project-id>
#
# Args:
#   $1 - API Gateway base URL (ApiEndpoint output, no trailing slash)
#   $2 - optional Kinescope project id (KinescopeParentId); omit for workspace-level
#
# Env:
#   KINESCOPE_API_TOKEN - required
#   KINESCOPE_DRM_STRICT - optional; default true (deny when backend unreachable)
set -euo pipefail

API_BASE="${1:?Usage: configure-kinescope-drm-auth.sh <api_endpoint> [kinescope_project_id]}"
PROJECT_ID="${2:-}"
TOKEN="${KINESCOPE_API_TOKEN:-}"

if [[ -z "$TOKEN" ]]; then
  echo "Error: KINESCOPE_API_TOKEN is required." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required to build the Kinescope DRM auth request body." >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "Error: curl is required to configure Kinescope DRM auth." >&2
  exit 1
fi

API_BASE="${API_BASE%/}"
DRM_URL="${API_BASE}/webhooks/kinescope/drm-auth"
STRICT="${KINESCOPE_DRM_STRICT:-true}"

if [[ -n "$PROJECT_ID" ]]; then
  TARGET="https://api.kinescope.io/v1/drm/auth/${PROJECT_ID}"
  SCOPE="project ${PROJECT_ID}"
else
  TARGET="https://api.kinescope.io/v1/drm/auth"
  SCOPE="workspace"
fi

echo "Configuring Kinescope DRM auth (${SCOPE}) -> ${DRM_URL}"

OUT="$(mktemp)"
trap 'rm -f "$OUT"' EXIT

BODY="$(python3 - <<PY
import json
print(json.dumps({"url": "${DRM_URL}", "strict": "${STRICT}" == "true"}))
PY
)"

HTTP_CODE="$(curl -sS -o "$OUT" -w '%{http_code}' \
  -X PUT "$TARGET" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$BODY")"

if [[ "$HTTP_CODE" != "200" && "$HTTP_CODE" != "201" && "$HTTP_CODE" != "204" ]]; then
  echo "Kinescope DRM auth configure failed (HTTP ${HTTP_CODE}):" >&2
  cat "$OUT" >&2 || true
  exit 1
fi

echo "Kinescope DRM auth configured (HTTP ${HTTP_CODE})."
if [[ -s "$OUT" ]]; then
  cat "$OUT"
  echo
fi
