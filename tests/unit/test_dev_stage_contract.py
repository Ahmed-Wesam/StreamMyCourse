"""Dev stage contract — refuse/guards (D1+D3) and overrides/templates (D4)."""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO / "scripts"
_TEMPLATES = _REPO / "infrastructure" / "templates"
_DEV_STAGE_SCRIPT = _SCRIPTS / "dev_stage.py"

_FIXTURE_CLIENT_ID = "111222-fixture.apps.googleusercontent.com"
_FIXTURE_CLIENT_SECRET = "dev-client-SHOULD-NOT-LEAK"
_PROD_DENY_ID = "cfuhjrrzy65ngud25rdqqso5t4"


def _load_dev_stage():
    path = _SCRIPTS / "dev_stage.py"
    assert path.is_file(), f"missing {path}"
    spec = importlib.util.spec_from_file_location("dev_stage", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["dev_stage"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_refuse_unless_dev_rejects_prod() -> None:
    mod = _load_dev_stage()
    with pytest.raises(SystemExit) as exc_info:
        mod.refuse_unless_dev("prod")
    message = str(exc_info.value).lower()
    assert "deploy prod" not in message


def test_refuse_unless_dev_accepts_dev() -> None:
    mod = _load_dev_stage()
    mod.refuse_unless_dev("dev")


def _fixture_client_id_digest() -> str:
    return hashlib.sha256(_FIXTURE_CLIENT_ID.encode()).hexdigest()


def test_prod_cluster_deny_constant_exposed() -> None:
    mod = _load_dev_stage()
    assert getattr(mod, "PROD_CLUSTER_DENY_ID", None) == _PROD_DENY_ID


def test_guard_google_signature_has_no_raw_prod_id_param() -> None:
    mod = _load_dev_stage()
    sig = inspect.signature(mod.guard_google)
    params = list(sig.parameters)
    assert "prod_client_id_sha256" in params
    assert "prod_client_id" not in params
    assert len(params) == 3


def test_guard_google_rejects_empty_dev_id() -> None:
    mod = _load_dev_stage()
    with pytest.raises((SystemExit, ValueError)) as exc_info:
        mod.guard_google("", _FIXTURE_CLIENT_SECRET, "deadbeef" * 8)
    message = str(exc_info.value)
    assert "GOOGLE_OAUTH_CLIENT_ID" in message
    assert "GOOGLE_OAUTH_CLIENT_SECRET" in message
    assert "dev" in message.lower()
    assert _FIXTURE_CLIENT_SECRET not in message


def test_guard_google_rejects_empty_dev_secret() -> None:
    mod = _load_dev_stage()
    with pytest.raises((SystemExit, ValueError)) as exc_info:
        mod.guard_google(_FIXTURE_CLIENT_ID, "", "deadbeef" * 8)
    message = str(exc_info.value)
    assert "GOOGLE_OAUTH_CLIENT_ID" in message
    assert "GOOGLE_OAUTH_CLIENT_SECRET" in message
    assert _FIXTURE_CLIENT_SECRET not in message


def test_guard_google_rejects_dev_id_matching_prod_digest() -> None:
    mod = _load_dev_stage()
    digest = _fixture_client_id_digest()
    with pytest.raises((SystemExit, ValueError)) as exc_info:
        mod.guard_google(_FIXTURE_CLIENT_ID, _FIXTURE_CLIENT_SECRET, digest)
    message = str(exc_info.value)
    assert "refusing to create StreamMyCourse-Auth-dev" in message
    assert _FIXTURE_CLIENT_ID not in message
    assert digest not in message


def test_guard_google_accepts_different_digest_and_nonempty_secret() -> None:
    mod = _load_dev_stage()
    mod.guard_google(_FIXTURE_CLIENT_ID, _FIXTURE_CLIENT_SECRET, "0" * 64)


def test_assert_not_prod_cluster_rejects_empty() -> None:
    mod = _load_dev_stage()
    with pytest.raises((SystemExit, ValueError)) as exc_info:
        mod.assert_not_prod_cluster("")
    assert _PROD_DENY_ID not in str(exc_info.value)


def test_assert_not_prod_cluster_rejects_prod_cluster_id_in_value() -> None:
    mod = _load_dev_stage()
    host = f"{_PROD_DENY_ID}.dsql.eu-west-1.on.aws"
    with pytest.raises((SystemExit, ValueError)) as exc_info:
        mod.assert_not_prod_cluster(host)
    message = str(exc_info.value)
    assert _PROD_DENY_ID not in message
    assert host not in message


def test_assert_endpoints_differ_rejects_equal_hosts() -> None:
    mod = _load_dev_stage()
    host = "abc123.dsql.eu-west-1.on.aws"
    with pytest.raises((SystemExit, ValueError)) as exc_info:
        mod.assert_endpoints_differ(host, host)
    message = str(exc_info.value)
    assert host not in message


def test_assert_endpoints_differ_accepts_different_hosts() -> None:
    mod = _load_dev_stage()
    mod.assert_endpoints_differ(
        "devonly.dsql.eu-west-1.on.aws",
        "prodonly.dsql.eu-west-1.on.aws",
    )


def test_hash_client_id_cli_stdout_is_digest_only() -> None:
    env = {**os.environ, "GOOGLE_OAUTH_CLIENT_ID": _FIXTURE_CLIENT_ID}
    proc = subprocess.run(
        [sys.executable, str(_DEV_STAGE_SCRIPT), "hash-client-id"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert proc.returncode == 0
    expected = _fixture_client_id_digest()
    assert proc.stdout.strip() == expected
    assert _FIXTURE_CLIENT_ID not in proc.stdout
    assert _FIXTURE_CLIENT_ID not in proc.stderr


def test_guard_google_cli_refusal_does_not_leak_secrets() -> None:
    digest = _fixture_client_id_digest()
    env = {
        **os.environ,
        "GOOGLE_OAUTH_CLIENT_ID": _FIXTURE_CLIENT_ID,
        "GOOGLE_OAUTH_CLIENT_SECRET": _FIXTURE_CLIENT_SECRET,
        "PROD_GOOGLE_CLIENT_ID_SHA256": digest,
    }
    proc = subprocess.run(
        [sys.executable, str(_DEV_STAGE_SCRIPT), "guard-google"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert proc.returncode != 0
    combined = proc.stdout + proc.stderr
    assert _FIXTURE_CLIENT_ID not in combined
    assert _FIXTURE_CLIENT_SECRET not in combined


_FAKE_DEV_DSQL_HOST = "devonlycluster.dsql.eu-west-1.on.aws"
_FAKE_DEV_DSQL_ARN = (
    "arn:aws:dsql:eu-west-1:123456789012:cluster/devonlyclusterabc"
)
_FAKE_DEV_VIDEO_BUCKET = "streammycourse-devvideo-fakebucket"
_FAKE_COGNITO_POOL_ARN = (
    "arn:aws:cognito-idp:eu-west-1:123456789012:userpool/eu-west-1_DevOnly"
)
_FAKE_STUDENT_CLIENT = "aaaaaaaaaaaaaaaaaaaaaaaaaa"
_FAKE_TEACHER_CLIENT = "bbbbbbbbbbbbbbbbbbbbbbbbbb"
_LOCALHOST_CORS = (
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:5174,http://127.0.0.1:5174"
)


def _read_template(name: str) -> str:
    path = _TEMPLATES / name
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def _parameters_block(text: str) -> str:
    match = re.search(r"(?ms)^Parameters:.*?(?=^Resources:)", text)
    assert match, "Parameters section not found"
    return match.group(0)


def _overrides_to_dict(overrides: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in overrides:
        key, _, value = item.partition("=")
        assert key, f"bad override {item!r}"
        out[key] = value
    return out


def _join_overrides(overrides: list[str]) -> str:
    return "\n".join(overrides)


def test_auth_parameter_overrides_dev_shape() -> None:
    mod = _load_dev_stage()
    overrides = mod.auth_parameter_overrides(
        google_client_id=_FIXTURE_CLIENT_ID,
        google_client_secret=_FIXTURE_CLIENT_SECRET,
        dsql_endpoint=_FAKE_DEV_DSQL_HOST,
        dsql_cluster_arn=_FAKE_DEV_DSQL_ARN,
        profile_sync_bucket="artifacts-bucket",
        profile_sync_key="cognito-user-profile-sync-dev-abcd.zip",
        pre_signup_bucket="artifacts-bucket",
        pre_signup_key="cognito-pre-signup-dev-abcd.zip",
    )
    joined = _join_overrides(overrides)
    params = _overrides_to_dict(overrides)
    assert params["Environment"] == "dev"
    assert params["EnableUserProfileSync"] == "true"
    assert params["DsqlEndpoint"] == _FAKE_DEV_DSQL_HOST
    assert params["DsqlClusterArn"] == _FAKE_DEV_DSQL_ARN
    assert "ZohoSmtpSecretArn" not in joined
    assert "CognitoCustomEmailSender" not in joined
    assert "researchspectrum.org" not in joined
    assert "Kinescope" not in joined


def test_api_parameter_overrides_dev_shape() -> None:
    mod = _load_dev_stage()
    overrides = mod.api_parameter_overrides(
        video_bucket_name=_FAKE_DEV_VIDEO_BUCKET,
        dsql_endpoint=_FAKE_DEV_DSQL_HOST,
        dsql_cluster_arn=_FAKE_DEV_DSQL_ARN,
        cognito_user_pool_arn=_FAKE_COGNITO_POOL_ARN,
        cognito_client_id=f"{_FAKE_STUDENT_CLIENT},{_FAKE_TEACHER_CLIENT}",
        student_cognito_client_id=_FAKE_STUDENT_CLIENT,
        lambda_code_bucket="artifacts-bucket",
        lambda_code_key="catalog-dev-abcd.zip",
        token_authorizer_key="catalog-token-authorizer-dev-abcd.zip",
    )
    joined = _join_overrides(overrides)
    params = _overrides_to_dict(overrides)
    assert params["Environment"] == "dev"
    assert params["VideoProvider"] == "s3"
    assert params["VideoBucketName"] == _FAKE_DEV_VIDEO_BUCKET
    assert params["DsqlEndpoint"] == _FAKE_DEV_DSQL_HOST
    assert params["DsqlClusterArn"] == _FAKE_DEV_DSQL_ARN
    assert params["CorsAllowOrigin"] == _LOCALHOST_CORS
    assert "BillingEdgeLambdaArn" not in joined
    assert "MediaCleanupQueueUrl" not in joined
    assert "Kinescope" not in joined
    assert "ResourceNameSuffix" not in joined
    assert "researchspectrum.org" not in joined


def test_api_parameter_overrides_includes_media_cleanup_queue() -> None:
    mod = _load_dev_stage()
    overrides = mod.api_parameter_overrides(
        video_bucket_name=_FAKE_DEV_VIDEO_BUCKET,
        dsql_endpoint=_FAKE_DEV_DSQL_HOST,
        dsql_cluster_arn=_FAKE_DEV_DSQL_ARN,
        cognito_user_pool_arn=_FAKE_COGNITO_POOL_ARN,
        cognito_client_id=_FAKE_STUDENT_CLIENT,
        student_cognito_client_id=_FAKE_STUDENT_CLIENT,
        lambda_code_bucket="artifacts-bucket",
        lambda_code_key="catalog-dev-abcd.zip",
        token_authorizer_key="catalog-token-authorizer-dev-abcd.zip",
        media_cleanup_queue_url="https://sqs.eu-west-1.amazonaws.com/878564870560/StreamMyCourse-MediaCleanup-dev",
        media_cleanup_queue_arn="arn:aws:sqs:eu-west-1:878564870560:StreamMyCourse-MediaCleanup-dev",
    )
    params = _overrides_to_dict(overrides)
    assert params["MediaCleanupQueueUrl"].endswith("StreamMyCourse-MediaCleanup-dev")
    assert params["MediaCleanupQueueArn"].endswith(":StreamMyCourse-MediaCleanup-dev")


def test_api_parameter_overrides_rejects_empty_cluster_arn() -> None:
    mod = _load_dev_stage()
    with pytest.raises((SystemExit, ValueError)):
        mod.api_parameter_overrides(
            video_bucket_name=_FAKE_DEV_VIDEO_BUCKET,
            dsql_endpoint=_FAKE_DEV_DSQL_HOST,
            dsql_cluster_arn="",
            cognito_user_pool_arn=_FAKE_COGNITO_POOL_ARN,
            cognito_client_id=_FAKE_STUDENT_CLIENT,
            student_cognito_client_id=_FAKE_STUDENT_CLIENT,
            lambda_code_bucket="artifacts-bucket",
            lambda_code_key="catalog-dev-abcd.zip",
            token_authorizer_key="catalog-token-authorizer-dev-abcd.zip",
        )


def test_api_parameter_overrides_rejects_prod_cluster_id_in_endpoint() -> None:
    mod = _load_dev_stage()
    bad_host = f"{_PROD_DENY_ID}.dsql.eu-west-1.on.aws"
    with pytest.raises((SystemExit, ValueError)) as exc_info:
        mod.api_parameter_overrides(
            video_bucket_name=_FAKE_DEV_VIDEO_BUCKET,
            dsql_endpoint=bad_host,
            dsql_cluster_arn=_FAKE_DEV_DSQL_ARN,
            cognito_user_pool_arn=_FAKE_COGNITO_POOL_ARN,
            cognito_client_id=_FAKE_STUDENT_CLIENT,
            student_cognito_client_id=_FAKE_STUDENT_CLIENT,
            lambda_code_bucket="artifacts-bucket",
            lambda_code_key="catalog-dev-abcd.zip",
            token_authorizer_key="catalog-token-authorizer-dev-abcd.zip",
        )
    assert _PROD_DENY_ID not in str(exc_info.value)
    assert bad_host not in str(exc_info.value)


def test_auth_and_api_stack_environment_allows_dev() -> None:
    for name in ("auth-stack.yaml", "api-stack.yaml"):
        params = _parameters_block(_read_template(name))
        assert re.search(r"^\s+Environment:\s*$", params, re.MULTILINE)
        assert re.search(r"Default:\s+prod\s*$", params, re.MULTILINE)
        assert re.search(r"AllowedValues:.*\bdev\b", params) or re.search(
            r"^\s+-\s+dev\s*$", params, re.MULTILINE
        )


def test_auth_stack_google_client_id_still_required() -> None:
    params = _parameters_block(_read_template("auth-stack.yaml"))
    block = re.search(
        r"(?ms)^\s+GoogleClientId:.*?(?=^\s+\w+:\s*$)",
        params,
    )
    assert block
    g = block.group(0)
    assert re.search(r"MinLength:\s+1", g)
    assert "Default:" not in g


def test_video_stack_stays_prod_only_with_cloudfront() -> None:
    text = _read_template("video-stack.yaml")
    params = _parameters_block(text)
    env = re.search(r"(?ms)^\s+Environment:.*?(?=^\s+\w+:\s*$)", params)
    assert env
    assert "dev" not in env.group(0)
    assert "AWS::CloudFront::Distribution" in text


def test_dev_video_bucket_stack_contract() -> None:
    path = _TEMPLATES / "dev-video-bucket-stack.yaml"
    assert path.is_file(), "dev-video-bucket-stack.yaml must exist"
    text = path.read_text(encoding="utf-8")
    params = _parameters_block(text)
    assert "AWS::S3::Bucket" in text
    assert "AWS::CloudFront" not in text
    assert "AWS::EC2::NatGateway" not in text
    assert "AWS::EC2::VPC" not in text
    assert re.search(r"AllowedValues:\s*\[dev\]", params)
    assert re.search(r"Default:\s+dev\s*$", params, re.MULTILINE)
    assert "prod" not in params.split("Resources:")[0]


def test_api_stack_no_vpc_catalog_timeout_twenty() -> None:
    text = _read_template("api-stack.yaml")
    assert "VpcConfig" not in text
    assert re.search(
        r"(?ms)^\s+CatalogLambda:.*?^\s+Timeout:\s+20\s*$",
        text,
        re.MULTILINE,
    )


def test_auth_stack_has_no_vpc_config() -> None:
    assert "VpcConfig" not in _read_template("auth-stack.yaml")


def test_cfn_lint_scripts_include_dev_video_template() -> None:
    for script in (
        _SCRIPTS / "cfn-lint-templates.sh",
        _SCRIPTS / "cfn-lint-templates.ps1",
    ):
        body = script.read_text(encoding="utf-8")
        assert "dev-video-bucket-stack.yaml" in body


def test_frontend_env_example_dev_opt_in_comment() -> None:
    path = _REPO / "frontend" / ".env.example"
    text = path.read_text(encoding="utf-8")
    assert "VITE_API_PROXY_TARGET" in text
    lowered = text.lower()
    assert "/dev" in text or "stage `dev`" in lowered or "stage dev" in lowered
    assert "default" in lowered and "prod" in lowered
    assert _PROD_DENY_ID not in text


_WORKFLOWS = _REPO / ".github" / "workflows"
_MISSING_GOOGLE_SENTENCE = (
    "Set GitHub Environment dev secrets "
    "GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET"
)


def _read_deploy_dev_workflow() -> str:
    path = _WORKFLOWS / "deploy-dev.yml"
    assert path.is_file(), "deploy-dev.yml must exist for dev stage dispatch"
    return path.read_text(encoding="utf-8")


def test_deploy_dev_workflow_dispatch_and_call_only() -> None:
    text = _read_deploy_dev_workflow()
    assert "workflow_dispatch" in text
    assert "workflow_call" in text
    assert "push:" not in text
    assert "workflow_run:" not in text
    assert "pull_request:" not in text


def test_deploy_dev_workflow_concurrency() -> None:
    text = _read_deploy_dev_workflow()
    assert re.search(r"group:\s*deploy-dev\b", text)
    assert re.search(r"cancel-in-progress:\s*false", text)
    assert "deploy-${{ github.ref }}" not in text


def test_deploy_dev_workflow_forbidden_prod_artifacts() -> None:
    text = _read_deploy_dev_workflow()
    for forbidden in (
        "deploy-backend.sh",
        "deploy-payments.sh",
        "deploy-edge.sh",
        "deploy-transactional-mail.sh",
        "video-stack.yaml",
        "HYPERPAY",
        "ZOHO_SMTP",
        "KINESCOPE",
        "VpcConfig",
        "StreamMyCourse-Api-prod",
    ):
        assert forbidden not in text, f"forbidden in deploy-dev.yml: {forbidden!r}"


def _workflow_job_block(text: str, job_id: str) -> str:
    marker = f"  {job_id}:"
    start = text.index(marker)
    tail = text[start + len(marker) :]
    m = re.search(r"\n  [a-z][\w-]*:", tail)
    end = start + len(marker) + (m.start() if m else len(tail))
    return text[start:end]


def test_deploy_dev_workflow_prod_environment_only_on_hash_job() -> None:
    text = _read_deploy_dev_workflow()
    prod_env_jobs: list[str] = []
    for job_id in re.findall(r"(?m)^  ([\w-]+):\s*$", text):
        block = _workflow_job_block(text, job_id)
        if re.search(r"^\s+environment:\s*prod\s*$", block, re.M):
            prod_env_jobs.append(job_id)
    assert prod_env_jobs == ["hash-prod-google-client-id"]


def test_deploy_dev_hash_job_has_no_aws_or_cfn() -> None:
    text = _read_deploy_dev_workflow()
    block = _workflow_job_block(text, "hash-prod-google-client-id")
    assert "cloudformation" not in block
    assert "role-to-assume" not in block
    assert "aws " not in block


def test_deploy_dev_workflow_no_echo_google_secrets() -> None:
    text = _read_deploy_dev_workflow()
    assert 'echo "$GOOGLE' not in text
    assert "echo ${GOOGLE" not in text


def test_deploy_dev_guard_job_lists_missing_google_secret_sentence() -> None:
    text = _read_deploy_dev_workflow()
    assert _MISSING_GOOGLE_SENTENCE in text


def _read_deploy_dev_sh() -> str:
    path = _SCRIPTS / "deploy-dev.sh"
    assert path.is_file(), "scripts/deploy-dev.sh must exist"
    return path.read_text(encoding="utf-8")


def test_deploy_dev_sh_refuses_non_dev_before_aws() -> None:
    text = _read_deploy_dev_sh()
    aws_idx = text.index("aws ")
    refuse_idx = text.index("refuse_unless_dev")
    assert refuse_idx < aws_idx


def test_deploy_dev_sh_uses_dev_stage_guards_before_cfn() -> None:
    text = _read_deploy_dev_sh()
    cfn_idx = text.index("cloudformation deploy")
    assert (
        "assert_not_prod_cluster" in text[:cfn_idx]
        or "auth_parameter_overrides" in text[:cfn_idx]
        or "api_parameter_overrides" in text[:cfn_idx]
    )


def test_deploy_dev_sh_dev_lambda_keys_and_no_prod_refs() -> None:
    text = _read_deploy_dev_sh()
    assert "catalog-dev-" in text
    assert "catalog-token-authorizer-dev-" in text
    for forbidden in (
        "BillingFulfillment",
        "catalog-prod-",
        "StreamMyCourse-Video-prod",
    ):
        assert forbidden not in text, f"forbidden in deploy-dev.sh: {forbidden!r}"


def test_deploy_backend_yml_tests_dev_before_prod() -> None:
    backend = (_WORKFLOWS / "deploy-backend.yml").read_text(encoding="utf-8")
    assert "uses: ./.github/workflows/deploy-dev.yml" in backend
    assert "StreamMyCourse-Api-dev" in backend
    assert "StreamMyCourse-Api-prod" not in backend
    assert "StreamMyCourse-Dsql-prod" in backend
    assert "deploy-backend.sh" in backend