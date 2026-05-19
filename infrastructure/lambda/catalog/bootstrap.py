"""Composition root for the catalog Lambda.

Responsibilities:
  * Load configuration once per warm Lambda container.
  * Wire PostgreSQL repository adapters (RDS only).
  * Build the domain services and cache them in module state so subsequent
    invocations reuse the same objects (the connection is created lazily on the
    first query and cached for the lifetime of the warm container).

Nothing here talks to AWS SDKs directly except inside the private
``_build_rds_connection_factory`` helper, which is the only place Secrets
Manager and ``psycopg2.connect`` are called. Tests patch that helper (or the
module-level ``_secretsmanager_client`` / ``_psycopg2_connect`` hooks it uses)
to exercise the wiring without network access.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

from config import AppConfig, load_config
from services.auth.rds_repo import UserProfileRdsRepository
from services.auth.service import UserProfileService
from services.billing_merchant.repo import MerchantAccountRdsRepository
from services.billing_merchant.service import MerchantStatusService
from services.course_management.models import Course
from services.course_management.rds_repo import CourseCatalogRdsRepository
from services.course_management.service import CourseManagementService
from services.course_management.storage import CourseMediaStorage
from services.progress.rds_repo import LessonProgressRdsRepository
from services.progress.service import LessonProgressService
from services.subscription.repo import SubscriptionRdsRepository
from services.subscription.service import CourseAccessService
from services.question_banks.rds_repo import QuestionBankRdsRepository
from services.question_banks.service import QuestionBankService
from services.question_banks.visibility import (
    apply_module_quiz_visibility,
    module_quiz_score_percent,
)


@dataclass(frozen=True)
class _ModuleQuizVisibilityAdapter:
    """Composition-root adapter: ``ModuleQuizVisibilityPort`` → question bank RDS + visibility."""

    _qb_repo: QuestionBankRdsRepository

    def module_quiz_visibility_by_course(
        self,
        course_id: str,
        *,
        course_status: str,
        has_lesson_access: bool,
        cognito_sub: str,
    ) -> Dict[str, Dict[str, Any]]:
        if course_status != "PUBLISHED" or not has_lesson_access:
            return {}
        repo_map = self._qb_repo.list_module_quiz_visibility_for_course(
            course_id=course_id
        )
        visibility = apply_module_quiz_visibility(
            repo_map,
            course_status=course_status,
            has_lesson_access=has_lesson_access,
        )
        if not visibility or not cognito_sub.strip():
            return visibility
        scores = self._qb_repo.list_latest_submission_scores_for_course(
            course_id=course_id,
            user_sub=cognito_sub.strip(),
        )
        for module_id, entry in visibility.items():
            score = scores.get(module_id)
            if score is None:
                continue
            entry["latestScorePercent"] = module_quiz_score_percent(
                correct_count=score["correctCount"],
                total_count=score["totalCount"],
            )
        return visibility


@dataclass(frozen=True)
class _CourseMutateAuthorizerAdapter:
    """Composition-root adapter: ``CourseMutateAuthorizerPort`` → ``CourseManagementService``."""

    _course: CourseManagementService

    def ensure_course_mutable_by_actor(
        self, course_id: str, *, cognito_sub: str, role: str
    ) -> None:
        self._course.ensure_can_modify_course(
            course_id, cognito_sub=cognito_sub, role=role
        )

    def ensure_course_publisher_read_scope(
        self, course_id: str, *, cognito_sub: str, role: str
    ) -> None:
        self._course.ensure_publisher_question_bank_read(
            course_id, cognito_sub=cognito_sub, role=role
        )


@dataclass(frozen=True)
class _CourseReadAdapter:
    """Composition-root adapter: ``CourseReadPort`` → course catalog RDS."""

    _course_repo: CourseCatalogRdsRepository

    def get_course_status(self, course_id: str) -> str | None:
        course = self._course_repo.get_course(course_id)
        return course.status if course else None


@dataclass(frozen=True)
class _StudentLessonAccessAdapter:
    """Composition-root adapter: ``StudentLessonAccessPort`` → ``CourseManagementService``."""

    _course: CourseManagementService
    _course_repo: CourseCatalogRdsRepository

    def viewer_has_lesson_access(
        self, course_id: str, cognito_sub: str, role: str
    ) -> bool:
        course: Course | None = self._course_repo.get_course(course_id)
        if course is None:
            return False
        return self._course.viewer_has_lesson_access(
            course,
            course_id=course_id,
            cognito_sub=cognito_sub,
            role=role,
        )


@dataclass(frozen=True)
class AwsDeps:
    cfg: AppConfig
    service: CourseManagementService
    auth_service: UserProfileService
    progress_service: LessonProgressService
    question_bank_service: QuestionBankService
    merchant_service: MerchantStatusService


_cached: Dict[str, Any] = {}


ConnectionFactory = Callable[[], Any]


def _secretsmanager_client() -> Any:
    import boto3

    return boto3.client("secretsmanager")


def _psycopg2_connect(**kwargs: Any) -> Any:
    import psycopg2

    conn = psycopg2.connect(**kwargs)
    # Default to autocommit so a read-only `_execute(commit=False)` does not
    # leave the connection idle in a transaction holding share locks across
    # warm Lambda invocations. Repository methods that need multi-statement
    # atomicity (e.g. CourseCatalogRdsRepository.create_course,
    # set_lesson_orders) explicitly toggle autocommit off via
    # `_atomic_transaction` for the duration of their block.
    conn.autocommit = True
    return conn


def _rds_config_complete(cfg: AppConfig) -> bool:
    return bool(cfg.db_host and cfg.db_name and cfg.db_secret_arn)


def _build_rds_connection_factory(cfg: AppConfig) -> ConnectionFactory:
    """Return a ``() -> connection`` callable that lazily opens a PostgreSQL
    connection using credentials fetched from Secrets Manager.

    The factory is called at most once per warm Lambda container (caching in
    the repo adapters themselves), so the Secrets Manager fetch happens on the
    first query rather than at cold-start import time. This keeps import cheap
    when the Lambda is invoked but does not touch RDS.
    """
    if not cfg.db_secret_arn:
        raise RuntimeError("DB_SECRET_ARN is required for the RDS catalog")
    if not cfg.db_host:
        raise RuntimeError("DB_HOST is required for the RDS catalog")
    if not cfg.db_name:
        raise RuntimeError("DB_NAME is required for the RDS catalog")

    def factory() -> Any:
        sm = _secretsmanager_client()
        response = sm.get_secret_value(SecretId=cfg.db_secret_arn)
        payload_raw = response.get("SecretString") or ""
        try:
            payload = json.loads(payload_raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("RDS secret is not valid JSON") from exc
        user = str(payload.get("username") or "")
        password = str(payload.get("password") or "")
        if not user or not password:
            raise RuntimeError("RDS secret missing username/password fields")
        return _psycopg2_connect(
            host=cfg.db_host,
            port=int(cfg.db_port or 5432),
            dbname=cfg.db_name,
            user=user,
            password=password,
            sslmode="require",
            connect_timeout=5,
            # Server-side single-statement cap. A wedged query raises
            # psycopg2.errors.QueryCanceled at 10s instead of stalling the warm
            # container until the Lambda hard timeout, letting the repo-layer
            # OperationalError retry path open a fresh connection if needed.
            options="-c statement_timeout=10000",
        )

    return factory


def get_cached_aws_deps() -> Optional[AwsDeps]:
    dep = _cached.get("aws")
    return dep if isinstance(dep, AwsDeps) else None


def build_aws_deps(cfg: AppConfig) -> AwsDeps:
    if not _rds_config_complete(cfg):
        raise RuntimeError(
            "RDS catalog requires DB_HOST, DB_NAME, and DB_SECRET_ARN to be set"
        )

    conn_factory = _build_rds_connection_factory(cfg)
    course_repo = CourseCatalogRdsRepository(conn_factory)
    subscription_repo = SubscriptionRdsRepository(
        conn_factory,
        deployment_environment=cfg.deployment_environment,
    )
    course_access = CourseAccessService(subscription_repo, course_repo)
    auth_repo = UserProfileRdsRepository(conn_factory)
    progress_repo = LessonProgressRdsRepository(conn_factory)

    storage = CourseMediaStorage(cfg.video_bucket) if cfg.video_bucket else None
    qb_repo = QuestionBankRdsRepository(conn_factory)
    module_quiz_visibility = _ModuleQuizVisibilityAdapter(qb_repo)
    service = CourseManagementService(
        course_repo,
        storage,
        course_access=course_access,
        media_cleanup_queue_url=cfg.media_cleanup_queue_url,
        module_quiz_visibility=module_quiz_visibility,
    )
    auth_service = UserProfileService(auth_repo)
    progress_service = LessonProgressService(
        progress_repo,
        course_access,
        course_repo,
        progress_complete_ratio=cfg.progress_complete_ratio,
        position_slack_sec=cfg.progress_position_slack_sec,
    )

    authorizer = _CourseMutateAuthorizerAdapter(service)
    course_read = _CourseReadAdapter(course_repo)
    lesson_access = _StudentLessonAccessAdapter(service, course_repo)
    question_bank_service = QuestionBankService(
        course_mutate_authorizer=authorizer,
        question_bank_repo=qb_repo,
        student_lesson_access=lesson_access,
        course_read=course_read,
    )
    merchant_repo = MerchantAccountRdsRepository(conn_factory)
    merchant_service = MerchantStatusService(
        merchant_repo,
        deployment_environment=cfg.deployment_environment,
    )

    return AwsDeps(
        cfg=cfg,
        service=service,
        auth_service=auth_service,
        progress_service=progress_service,
        question_bank_service=question_bank_service,
        merchant_service=merchant_service,
    )


def warm_aws_deps_if_needed(cfg: AppConfig) -> None:
    if not _rds_config_complete(cfg):
        return
    if "aws" not in _cached:
        _cached["aws"] = build_aws_deps(cfg)


def lambda_bootstrap() -> Tuple[
    AppConfig,
    Optional[CourseManagementService],
    Optional[UserProfileService],
    Optional[LessonProgressService],
    Optional[QuestionBankService],
    Optional[MerchantStatusService],
]:
    """
    Composition root: load config and construct dependencies once.
    When RDS settings are incomplete the catalog cannot be wired, so
    ``(cfg, None, None, None, None, None)`` is returned and the handler responds
    with a configuration error.
    """
    cfg = load_config()
    if not _rds_config_complete(cfg):
        return cfg, None, None, None, None, None

    existing = get_cached_aws_deps()
    if existing is not None:
        return (
            existing.cfg,
            existing.service,
            existing.auth_service,
            existing.progress_service,
            existing.question_bank_service,
            existing.merchant_service,
        )

    deps = build_aws_deps(cfg)
    _cached["aws"] = deps
    return (
        deps.cfg,
        deps.service,
        deps.auth_service,
        deps.progress_service,
        deps.question_bank_service,
        deps.merchant_service,
    )
