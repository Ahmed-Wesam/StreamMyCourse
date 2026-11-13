#!/usr/bin/env python3
"""Operator entrypoint: disable Cognito user, delete DSQL profile row (DSQL-2)."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable, Optional, Protocol

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CATALOG = _REPO_ROOT / "infrastructure" / "lambda" / "catalog"
if str(_CATALOG) not in sys.path:
    sys.path.insert(0, str(_CATALOG))

from dsql_connect import connect  # noqa: E402
from services.assignments.rds_repo import AssignmentsRdsRepository  # noqa: E402
from services.certificates.rds_repo import CertificatesRdsRepository  # noqa: E402
from services.research_team.rds_repo import ResearchTeamRdsRepository  # noqa: E402
from services.auth.rds_repo import UserProfileRdsRepository  # noqa: E402
from services.common.sqs_client import send_media_cleanup_job  # noqa: E402
from services.lesson_notes.rds_repo import LessonNotesRdsRepository  # noqa: E402
from services.progress.rds_repo import LessonProgressRdsRepository  # noqa: E402
from services.purchases.repo import PurchaseRdsRepository  # noqa: E402
from services.question_banks.rds_repo import QuestionBankRdsRepository  # noqa: E402
from services.user_deletion import (  # noqa: E402
    UserDeletionBlocked,
    UserDeletionRegistry,
    UserDeletionService,
    register_operator_user_steps,
)

_USER_SUB_RE = re.compile(r"^[A-Za-z0-9-]{1,255}$")
_DEFAULT_AUTH_STACK = "StreamMyCourse-Auth-prod"
_DEFAULT_MEDIA_CLEANUP_STACK = "StreamMyCourse-MediaCleanup-prod"
_DEFAULT_REGION = "eu-west-1"
DSQL_USER_ADMIN = "admin"


class _CognitoPort(Protocol):
    def disable_user(self, *, user_pool_id: str, username: str) -> None: ...
    def delete_user(self, *, user_pool_id: str, username: str) -> None: ...
    def resolve_username(self, *, user_pool_id: str, user_sub: str) -> Optional[str]: ...


def _resolve_dsql_endpoint() -> str:
    host = os.environ.get("DSQL_ENDPOINT", "").strip()
    if host:
        return host
    region = os.environ.get("AWS_REGION", _DEFAULT_REGION).strip() or _DEFAULT_REGION
    try:
        import boto3

        cf = boto3.client("cloudformation", region_name=region)
        resp = cf.describe_stacks(StackName="StreamMyCourse-Dsql-prod")
        for out in resp["Stacks"][0].get("Outputs", []):
            if out.get("OutputKey") == "Endpoint":
                value = (out.get("OutputValue") or "").strip()
                if value:
                    return value
    except Exception:
        pass
    return ""


def _resolve_media_cleanup_queue_url() -> str:
    env = os.environ.get("MEDIA_CLEANUP_QUEUE_URL", "").strip()
    if env:
        return env
    region = os.environ.get("AWS_REGION", _DEFAULT_REGION).strip() or _DEFAULT_REGION
    stack = os.environ.get(
        "INTEGRATION_MEDIA_CLEANUP_STACK", _DEFAULT_MEDIA_CLEANUP_STACK
    ).strip() or _DEFAULT_MEDIA_CLEANUP_STACK
    try:
        import boto3

        cf = boto3.client("cloudformation", region_name=region)
        resp = cf.describe_stacks(StackName=stack)
        for out in resp["Stacks"][0].get("Outputs", []):
            if out.get("OutputKey") == "MediaCleanupQueueUrl":
                return (out.get("OutputValue") or "").strip()
    except Exception:
        pass
    return ""


def _resolve_user_pool_id() -> str:
    region = os.environ.get("AWS_REGION", _DEFAULT_REGION).strip() or _DEFAULT_REGION
    stack = os.environ.get("INTEGRATION_AUTH_STACK", _DEFAULT_AUTH_STACK).strip() or _DEFAULT_AUTH_STACK
    try:
        import boto3

        cf = boto3.client("cloudformation", region_name=region)
        resp = cf.describe_stacks(StackName=stack)
        for out in resp["Stacks"][0].get("Outputs", []):
            if out.get("OutputKey") == "UserPoolId":
                return (out.get("OutputValue") or "").strip()
    except Exception:
        pass
    return ""


def _build_service(endpoint: str) -> UserDeletionService:
    factory: Callable[[], Any] = lambda: connect(DSQL_USER_ADMIN, endpoint)
    profile_repo = UserProfileRdsRepository(factory, tags_as_jsonb=True)
    progress_repo = LessonProgressRdsRepository(factory)
    notes_repo = LessonNotesRdsRepository(factory)
    deploy_env = (os.environ.get("DEPLOYMENT_ENVIRONMENT") or "prod").strip().lower()
    purchase_repo = PurchaseRdsRepository(factory, deployment_environment=deploy_env)
    quiz_repo = QuestionBankRdsRepository(factory)
    assignments_repo = AssignmentsRdsRepository(factory)
    certificates_repo = CertificatesRdsRepository(factory)
    research_team_repo = ResearchTeamRdsRepository(factory, areas_as_jsonb=True)
    registry = UserDeletionRegistry()
    register_operator_user_steps(
        registry,
        profile_repo,
        progress_repo,
        notes_repo,
        purchase_repo,
        quiz_repo,
        assignments_repo,
        certificates_repo,
        research_team_repo,
    )
    return UserDeletionService(registry), assignments_repo


class _BotoCognito:
    def resolve_username(self, *, user_pool_id: str, user_sub: str) -> Optional[str]:
        import boto3
        from botocore.exceptions import ClientError

        client = boto3.client("cognito-idp")
        resp = client.list_users(
            UserPoolId=user_pool_id,
            Filter=f'sub = "{user_sub}"',
            Limit=10,
        )
        users = resp.get("Users") or []
        if len(users) == 0:
            return None
        if len(users) > 1:
            raise RuntimeError("multiple Cognito users matched user_sub")
        return str(users[0].get("Username") or "")

    def disable_user(self, *, user_pool_id: str, username: str) -> None:
        import boto3
        from botocore.exceptions import ClientError

        client = boto3.client("cognito-idp")
        try:
            client.admin_disable_user(UserPoolId=user_pool_id, Username=username)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "UserNotFoundException":
                return
            raise

    def delete_user(self, *, user_pool_id: str, username: str) -> None:
        import boto3
        from botocore.exceptions import ClientError

        client = boto3.client("cognito-idp")
        try:
            client.admin_delete_user(UserPoolId=user_pool_id, Username=username)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "UserNotFoundException":
                return
            raise


def run(
    argv: list[str],
    *,
    cognito: _CognitoPort,
    service_factory: Callable[[str], UserDeletionService],
    endpoint_resolver: Callable[[], str],
    pool_resolver: Callable[[], str],
) -> int:
    parser = argparse.ArgumentParser(description="Delete a Cognito user and DSQL users row")
    parser.add_argument("--user-sub", required=True, dest="user_sub")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Perform disable, DSQL delete, and Cognito delete (default is dry-run)",
    )
    args = parser.parse_args(argv)
    user_sub = (args.user_sub or "").strip()
    if not _USER_SUB_RE.match(user_sub):
        print("user_sub must match ^[A-Za-z0-9-]{1,255}$", file=sys.stderr)
        return 1

    endpoint = endpoint_resolver().strip()
    pool_id = pool_resolver().strip()
    if not endpoint:
        print("DSQL endpoint not resolved", file=sys.stderr)
        return 1
    if not pool_id:
        print("Cognito UserPoolId not resolved", file=sys.stderr)
        return 1

    steps = [
        "resolve DSQL endpoint",
        "resolve Cognito pool",
        "admin_disable_user (if username found)",
        "UserDeletionService.delete_user (DSQL)",
        "admin_delete_user (if username found)",
        "UserDeletionService.delete_user (DSQL again)",
    ]
    print(f"Planned user_sub prefix: {user_sub[:8]}")
    for step in steps:
        print(f"  - {step}")
    if not args.execute:
        return 0

    username: Optional[str] = None
    try:
        username = cognito.resolve_username(user_pool_id=pool_id, user_sub=user_sub)
    except RuntimeError:
        print("multiple Cognito users matched user_sub", file=sys.stderr)
        return 1

    built = service_factory(endpoint)
    if isinstance(built, tuple):
        svc, assignments_repo = built
    else:
        svc = built
        assignments_repo = None
    file_keys_by_course: dict[str, list[str]] = {}
    if assignments_repo is not None:
        for course_id, key in assignments_repo.list_submission_file_keys_for_user(
            user_sub
        ):
            file_keys_by_course.setdefault(course_id, []).append(key)
    all_keys = [k for keys in file_keys_by_course.values() for k in keys if k]
    queue_url = _resolve_media_cleanup_queue_url() if all_keys else ""
    if all_keys and not queue_url:
        print(
            "Media cleanup queue URL could not be resolved but submission files exist",
            file=sys.stderr,
        )
        return 1
    if username:
        cognito.disable_user(user_pool_id=pool_id, username=username)
    try:
        svc.delete_user(user_sub)
    except UserDeletionBlocked as exc:
        print(f"blocked at step {exc.step_name} ({exc.pgcode})", file=sys.stderr)
        if username:
            print(username)
        return 2
    if username:
        cognito.delete_user(user_pool_id=pool_id, username=username)
    svc.delete_user(user_sub)
    if all_keys and queue_url:
        for course_id, keys in file_keys_by_course.items():
            send_media_cleanup_job(queue_url, course_id, keys, s3_keys=keys)
    return 0


def main() -> None:
    code = run(
        sys.argv[1:],
        cognito=_BotoCognito(),
        service_factory=_build_service,
        endpoint_resolver=_resolve_dsql_endpoint,
        pool_resolver=_resolve_user_pool_id,
    )
    raise SystemExit(code)


if __name__ == "__main__":
    main()
