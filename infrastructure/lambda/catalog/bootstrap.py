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

from _diag import trace  # DIAGNOSTIC: temporary stage tracer
from config import AppConfig, load_config
from services.auth.rds_repo import UserProfileRdsRepository
from services.auth.service import UserProfileService
from services.course_management.rds_repo import CourseCatalogRdsRepository
from services.course_management.service import CourseManagementService
from services.course_management.storage import CourseMediaStorage
from services.enrollment.rds_repo import EnrollmentRdsRepository
from services.progress.rds_repo import LessonProgressRdsRepository
from services.progress.service import LessonProgressService


@dataclass(frozen=True)
class AwsDeps:
    cfg: AppConfig
    service: CourseManagementService
    auth_service: UserProfileService
    progress_service: LessonProgressService


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
        trace("factory.enter")
        sm = _secretsmanager_client()
        trace("factory.before_get_secret")
        response = sm.get_secret_value(SecretId=cfg.db_secret_arn)
        trace("factory.after_get_secret")
        payload_raw = response.get("SecretString") or ""
        try:
            payload = json.loads(payload_raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("RDS secret is not valid JSON") from exc
        user = str(payload.get("username") or "")
        password = str(payload.get("password") or "")
        if not user or not password:
            raise RuntimeError("RDS secret missing username/password fields")
        trace("factory.before_psycopg2_connect", host=cfg.db_host)
        conn = _psycopg2_connect(
            host=cfg.db_host,
            port=int(cfg.db_port or 5432),
            dbname=cfg.db_name,
            user=user,
            password=password,
            sslmode="require",
            connect_timeout=5,
            # TCP keepalives: detect dropped RDS peers before Lambda hits its timeout.
            keepalives=1,
            keepalives_idle=10,
            keepalives_interval=5,
            keepalives_count=2,
            # Bound single-statement duration so a wedged query fails closed and the
            # repo-layer OperationalError retry can open a fresh connection.
            options="-c statement_timeout=10000",
        )
        trace("factory.after_psycopg2_connect")
        return conn

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
    enrollment_repo = EnrollmentRdsRepository(conn_factory)
    auth_repo = UserProfileRdsRepository(conn_factory)
    progress_repo = LessonProgressRdsRepository(conn_factory)

    storage = CourseMediaStorage(cfg.video_bucket) if cfg.video_bucket else None
    service = CourseManagementService(
        course_repo,
        storage,
        enrollment_repo,
        media_cleanup_queue_url=cfg.media_cleanup_queue_url,
    )
    auth_service = UserProfileService(auth_repo)
    progress_service = LessonProgressService(
        progress_repo,
        enrollment_repo,
        course_repo,
        progress_complete_ratio=cfg.progress_complete_ratio,
        position_slack_sec=cfg.progress_position_slack_sec,
    )

    return AwsDeps(
        cfg=cfg,
        service=service,
        auth_service=auth_service,
        progress_service=progress_service,
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
]:
    """
    Composition root: load config and construct dependencies once.
    When RDS settings are incomplete the catalog cannot be wired, so
    ``(cfg, None, None, None)`` is returned and the handler responds with a
    configuration error.
    """
    cfg = load_config()
    if not _rds_config_complete(cfg):
        return cfg, None, None, None

    existing = get_cached_aws_deps()
    if existing is not None:
        trace("bootstrap.cache_hit")
        return (
            existing.cfg,
            existing.service,
            existing.auth_service,
            existing.progress_service,
        )

    trace("bootstrap.cache_miss")
    deps = build_aws_deps(cfg)
    _cached["aws"] = deps
    trace("bootstrap.cache_populated")
    return deps.cfg, deps.service, deps.auth_service, deps.progress_service
