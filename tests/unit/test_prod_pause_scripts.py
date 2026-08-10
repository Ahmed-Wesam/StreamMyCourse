"""Contract tests: prod pause/teardown/restore scripts (TDD Red → Green).

Tests assert stack order via scripts/lib/prod_pause_constants.sh and script contracts
once teardown-prod.sh, export-pause-manifest.sh, restore-prod.sh, and
sync-rds-secret-after-restore.sh exist.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _constants_sh_text() -> str:
    path = _repo_root() / "scripts" / "lib" / "prod_pause_constants.sh"
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def _parse_bash_string(text: str, var_name: str) -> str:
    match = re.search(rf'{var_name}="([^"]+)"', text)
    assert match, f"{var_name} assignment not found in prod_pause_constants.sh"
    return match.group(1)


def _parse_bash_string_array(text: str, var_name: str) -> list[str]:
    match = re.search(rf"{var_name}=\(\s*(.*?)\s*\)", text, re.DOTALL)
    assert match, f"{var_name} array not found in prod_pause_constants.sh"
    return re.findall(r'"([^"]+)"', match.group(1))


def _script_must_exist(rel: str) -> Path:
    path = _repo_root() / rel
    assert path.is_file(), f"required script missing (implement in Green slice): {rel}"
    return path


def _bash_syntax_check(rel: str) -> None:
    script = _script_must_exist(rel)
    subprocess.run(
        ["bash", "-n", str(script)],
        check=True,
        cwd=str(_repo_root()),
    )


# Canonical teardown sequence from prod shutdown/restore plan (runbook Phase 2).
EXPECTED_WAF_SCRIPT = "scripts/delete-waf-stacks.sh"
EXPECTED_TEARDOWN_STACKS = (
    "StreamMyCourse-Api-prod:eu-west-1",
    "StreamMyCourse-Auth-prod:eu-west-1",
    "StreamMyCourse-VideoProviderEdge-prod:eu-west-1",
    "StreamMyCourse-Payments-prod:eu-west-1",
    "StreamMyCourse-MediaCleanup-prod:eu-west-1",
    "StreamMyCourse-RdsQuery-prod:eu-west-1",
    "StreamMyCourse-Rds-prod:eu-west-1",
    "StreamMyCourse-Video-prod:eu-west-1",
    "StreamMyCourse-EdgeHosting-prod:us-east-1",
    "StreamMyCourse-ArtifactJanitor-prod:eu-west-1",
)
EXPECTED_LEGACY_STACKS = (
    "StreamMyCourse-Web-prod:us-east-1",
    "StreamMyCourse-TeacherWeb-prod:us-east-1",
    "StreamMyCourse-Cert-prod:us-east-1",
)
EXPECTED_MANIFEST_JSON_KEYS = (
    "aws_account_id",
    "regions",
    "video_bucket_name",
    "student_bucket_name",
    "teacher_bucket_name",
    "api_endpoint",
    "user_pool_id",
    "student_user_pool_client_id",
    "teacher_user_pool_client_id",
    "cognito_hosted_ui_domain",
    "rds_db_host",
    "rds_snapshot_identifier",
    "github_env_checklist",
)
TEARDOWN_REQUIRED_FLAGS = (
    "--dry-run",
    "--confirm",
    "--skip-missing",
    "--manifest-out",
)
RESTORE_REQUIRED_FLAGS = (
    "--manifest",
    "--confirm",
    "--dry-run",
)
RESTORE_ORCHESTRATION_MARKERS = (
    "prod_pause_constants.sh",
    "deploy-edge.sh",
    "sync-rds-secret-after-restore.sh",
    "deploy-backend.sh",
    "auth-stack.yaml",
)


def test_prod_pause_constants_teardown_waf_script_first() -> None:
    text = _constants_sh_text()
    waf = _parse_bash_string(text, "TEARDOWN_WAF_SCRIPT")
    assert waf == EXPECTED_WAF_SCRIPT
    assert (_repo_root() / waf).is_file(), f"WAF helper must exist: {waf}"


def test_prod_pause_constants_teardown_stack_order() -> None:
    text = _constants_sh_text()
    stacks = _parse_bash_string_array(text, "TEARDOWN_STACKS")
    assert stacks == list(EXPECTED_TEARDOWN_STACKS)


def test_prod_pause_constants_legacy_stack_order() -> None:
    text = _constants_sh_text()
    legacy = _parse_bash_string_array(text, "TEARDOWN_LEGACY_STACKS")
    assert legacy == list(EXPECTED_LEGACY_STACKS)


def test_prod_pause_constants_manifest_json_keys() -> None:
    text = _constants_sh_text()
    keys = _parse_bash_string_array(text, "PAUSE_MANIFEST_JSON_KEYS")
    assert keys == list(EXPECTED_MANIFEST_JSON_KEYS)


def test_teardown_prod_sh_sources_pause_constants() -> None:
    text = _script_must_exist("scripts/teardown-prod.sh").read_text(encoding="utf-8")
    assert "prod_pause_constants.sh" in text
    assert "TEARDOWN_STACKS" in text or "TEARDOWN_WAF_SCRIPT" in text


def test_teardown_prod_sh_exposes_required_flags() -> None:
    text = _script_must_exist("scripts/teardown-prod.sh").read_text(encoding="utf-8")
    for flag in TEARDOWN_REQUIRED_FLAGS:
        assert flag in text, f"teardown-prod.sh must support {flag}"


def test_export_pause_manifest_sh_passes_bash_syntax_check() -> None:
    _bash_syntax_check("scripts/export-pause-manifest.sh")


def test_export_pause_manifest_sh_writes_required_manifest_keys() -> None:
    text = _script_must_exist("scripts/export-pause-manifest.sh").read_text(
        encoding="utf-8"
    )
    for key in EXPECTED_MANIFEST_JSON_KEYS:
        assert key in text, f"export-pause-manifest.sh must emit JSON key {key!r}"


def test_teardown_prod_sh_passes_bash_syntax_check() -> None:
    _bash_syntax_check("scripts/teardown-prod.sh")


def test_restore_prod_sh_passes_bash_syntax_check() -> None:
    _bash_syntax_check("scripts/restore-prod.sh")


def test_restore_prod_sh_sources_pause_constants() -> None:
    text = _script_must_exist("scripts/restore-prod.sh").read_text(encoding="utf-8")
    assert "prod_pause_constants.sh" in text


def test_restore_prod_sh_exposes_required_flags() -> None:
    text = _script_must_exist("scripts/restore-prod.sh").read_text(encoding="utf-8")
    for flag in RESTORE_REQUIRED_FLAGS:
        assert flag in text, f"restore-prod.sh must support {flag}"


def test_restore_prod_sh_references_restore_orchestration() -> None:
    text = _script_must_exist("scripts/restore-prod.sh").read_text(encoding="utf-8")
    for marker in RESTORE_ORCHESTRATION_MARKERS:
        assert marker in text, f"restore-prod.sh must reference {marker!r}"


def test_sync_rds_secret_after_restore_sh_passes_bash_syntax_check() -> None:
    _bash_syntax_check("scripts/sync-rds-secret-after-restore.sh")


def test_sync_rds_secret_after_restore_sh_avoids_password_on_cli() -> None:
    text = _script_must_exist("scripts/sync-rds-secret-after-restore.sh").read_text(
        encoding="utf-8"
    )
    assert "--master-user-password" not in text
    assert "--cli-input-json" in text
    assert "file://${TMP_JSON}" in text
    assert "RDS_PASSWORD" not in text
    assert "PASSWORD=" not in text


def test_restore_prod_sh_video_cors_uses_web_domains() -> None:
    text = _script_must_exist("scripts/restore-prod.sh").read_text(encoding="utf-8")
    assert "video_cors_allowed_origins" in text
    assert "STUDENT_WEB_DOMAIN" in text
    assert "TEACHER_WEB_DOMAIN" in text
    assert "https://researchspectrum.org,https://teach.researchspectrum.org" not in text


def test_restore_prod_sh_auth_deploy_avoids_google_secret_on_cli() -> None:
    text = _script_must_exist("scripts/restore-prod.sh").read_text(encoding="utf-8")
    assert "GoogleClientSecret=${GOOGLE_OAUTH_CLIENT_SECRET}" not in text
    assert "cfn_deploy_stack_from_parameters_file" in text
    assert '--parameters "$params_uri"' in text


def test_restore_prod_sh_derives_cognito_urls_from_web_domains() -> None:
    text = _script_must_exist("scripts/restore-prod.sh").read_text(encoding="utf-8")
    assert "auth_student_callback_urls" in text
    assert "auth_teacher_callback_urls" in text
    assert 'urls="https://${STUDENT_WEB_DOMAIN}/"' in text
    assert 'urls="https://${TEACHER_WEB_DOMAIN}/"' in text
    assert "RESTORE_AUTH_STUDENT_CALLBACK_URLS=\"$(auth_student_callback_urls)\"" in text


def test_restore_prod_sh_cfn_deploy_tolerates_no_op_update() -> None:
    text = _script_must_exist("scripts/restore-prod.sh").read_text(encoding="utf-8")
    assert "No updates are to be performed" in text
    assert "already up to date" in text


def test_export_pause_manifest_sh_uses_python_fallback() -> None:
    text = _script_must_exist("scripts/export-pause-manifest.sh").read_text(encoding="utf-8")
    assert 'PY=python3' in text or "python3" in text
    assert "PY=python" in text
    assert '"$PY"' in text
    assert "python3 <<" not in text
