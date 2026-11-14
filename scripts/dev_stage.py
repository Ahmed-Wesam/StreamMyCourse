"""Dev stage guards and deploy helpers."""

from __future__ import annotations

import hashlib
import os
import sys

PROD_CLUSTER_DENY_ID = "cfuhjrrzy65ngud25rdqqso5t4"

_DEFAULT_DEV_COGNITO_DOMAIN_PREFIX = "streammycourse-auth-dev"

_DEV_LOCALHOST_CORS = (
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:5174,http://127.0.0.1:5174"
)
_DEV_GATEWAY_RESPONSE_ORIGIN = "http://localhost:5173"

_MISSING_GOOGLE_SECRETS = (
    "Set GitHub Environment dev secrets "
    "GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET"
)
_DEV_GOOGLE_MATCHES_PROD = (
    "dev Google client id matches the prod client id; "
    "refusing to create StreamMyCourse-Auth-dev"
)


def refuse_unless_dev(environment: str) -> None:
    """Exit when the target stage is not dev (used by deploy-dev entrypoints)."""
    if environment != "dev":
        print(f"Environment must be dev, got: {environment}", file=sys.stderr)
        raise SystemExit(1)


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def guard_google(
    dev_client_id: str,
    dev_client_secret: str,
    prod_client_id_sha256: str,
) -> None:
    """Ensure dev Google OAuth credentials differ from prod (digest comparison only)."""
    if not dev_client_id.strip() or not dev_client_secret.strip():
        raise ValueError(_MISSING_GOOGLE_SECRETS)
    digest = _sha256_hex(dev_client_id)
    if digest == prod_client_id_sha256.strip().lower():
        raise ValueError(_DEV_GOOGLE_MATCHES_PROD)


def assert_not_prod_cluster(value: str) -> None:
    """Reject empty values and any string that references the prod DSQL cluster id."""
    if not value or not value.strip():
        raise ValueError("DSQL cluster value must be non-empty")
    if PROD_CLUSTER_DENY_ID in value:
        raise ValueError("DSQL cluster value must not reference the prod cluster")


def assert_endpoints_differ(dev_endpoint: str, prod_endpoint: str) -> None:
    """Reject when dev and prod DSQL endpoints are the same host."""
    if dev_endpoint.strip() == prod_endpoint.strip():
        raise ValueError("Dev and prod DSQL endpoints must differ")


def _dev_dsql_guard(endpoint: str, cluster_arn: str) -> None:
    assert_not_prod_cluster(endpoint)
    assert_not_prod_cluster(cluster_arn)


def auth_parameter_overrides(
    *,
    google_client_id: str,
    google_client_secret: str,
    dsql_endpoint: str,
    dsql_cluster_arn: str,
    profile_sync_bucket: str,
    profile_sync_key: str,
    pre_signup_bucket: str,
    pre_signup_key: str,
    cognito_domain_prefix: str | None = None,
    student_cognito_client_id: str = "",
    teacher_cognito_client_id: str = "",
) -> list[str]:
    """CloudFormation --parameter-overrides for StreamMyCourse-Auth-dev."""
    _dev_dsql_guard(dsql_endpoint, dsql_cluster_arn)
    domain = (cognito_domain_prefix or _DEFAULT_DEV_COGNITO_DOMAIN_PREFIX).strip()
    overrides = [
        "Environment=dev",
        f"CognitoDomainPrefix={domain}",
        f"GoogleClientId={google_client_id}",
        f"GoogleClientSecret={google_client_secret}",
        "EnableUserProfileSync=true",
        f"DsqlEndpoint={dsql_endpoint}",
        f"DsqlClusterArn={dsql_cluster_arn}",
        f"CognitoUserProfileSyncCodeS3Bucket={profile_sync_bucket}",
        f"CognitoUserProfileSyncCodeS3Key={profile_sync_key}",
        f"CognitoPreSignUpCodeS3Bucket={pre_signup_bucket}",
        f"CognitoPreSignUpCodeS3Key={pre_signup_key}",
    ]
    if student_cognito_client_id.strip():
        overrides.append(f"StudentCognitoClientId={student_cognito_client_id}")
    if teacher_cognito_client_id.strip():
        overrides.append(f"TeacherCognitoClientId={teacher_cognito_client_id}")
    return overrides


def api_parameter_overrides(
    *,
    video_bucket_name: str,
    dsql_endpoint: str,
    dsql_cluster_arn: str,
    cognito_user_pool_arn: str,
    cognito_client_id: str,
    student_cognito_client_id: str,
    lambda_code_bucket: str,
    lambda_code_key: str,
    token_authorizer_key: str,
    video_url: str = "",
    media_cleanup_queue_url: str = "",
    media_cleanup_queue_arn: str = "",
) -> list[str]:
    """CloudFormation --parameter-overrides for StreamMyCourse-Api-dev."""
    _dev_dsql_guard(dsql_endpoint, dsql_cluster_arn)
    overrides = [
        "Environment=dev",
        f"LambdaCodeS3Bucket={lambda_code_bucket}",
        f"LambdaCodeS3Key={lambda_code_key}",
        f"TokenAuthorizerCodeS3Key={token_authorizer_key}",
        "VideoProvider=s3",
        f"VideoBucketName={video_bucket_name}",
        f"DsqlEndpoint={dsql_endpoint}",
        f"DsqlClusterArn={dsql_cluster_arn}",
        f"CorsAllowOrigin={_DEV_LOCALHOST_CORS}",
        f"GatewayResponseAllowOrigin={_DEV_GATEWAY_RESPONSE_ORIGIN}",
        f"CognitoUserPoolArn={cognito_user_pool_arn}",
        f"CognitoClientId={cognito_client_id}",
        f"StudentCognitoClientId={student_cognito_client_id}",
    ]
    if video_url.strip():
        overrides.append(f"VideoUrl={video_url}")
    queue_url = media_cleanup_queue_url.strip()
    queue_arn = media_cleanup_queue_arn.strip()
    if queue_url and queue_arn:
        overrides.append(f"MediaCleanupQueueUrl={queue_url}")
        overrides.append(f"MediaCleanupQueueArn={queue_arn}")
    return overrides


def _cli_hash_client_id() -> int:
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
    if not client_id.strip():
        print("GOOGLE_OAUTH_CLIENT_ID is not set", file=sys.stderr)
        return 1
    sys.stdout.write(_sha256_hex(client_id))
    sys.stdout.write("\n")
    return 0


def _cli_guard_google() -> int:
    dev_client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
    dev_client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
    prod_digest = os.environ.get("PROD_GOOGLE_CLIENT_ID_SHA256", "")
    try:
        guard_google(dev_client_id, dev_client_secret, prod_digest)
    except ValueError as err:
        print(str(err), file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("usage: dev_stage.py <hash-client-id|guard-google>", file=sys.stderr)
        return 1
    command = args[0]
    if command == "hash-client-id":
        return _cli_hash_client_id()
    if command == "guard-google":
        return _cli_guard_google()
    print(f"unknown command: {command}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())