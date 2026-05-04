"""Composition root for the catalog Lambda.

Responsibilities:
  * Load configuration once per warm Lambda container.
  * Pick between the DynamoDB and PostgreSQL repository adapters based on
    ``cfg.use_rds``.
  * Build the domain services and cache them in module state so subsequent
    invocations reuse the same objects (important for the PostgreSQL path: the
    connection is created lazily on the first query and cached for the lifetime
    of the warm container).

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
from services.auth.ports import UserProfileRepositoryPort
from services.auth.rds_repo import UserProfileRdsRepository
from services.auth.repo import UserProfileRepository
from services.auth.service import UserProfileService
from services.course_management.ports import CourseCatalogRepositoryPort
from services.course_management.rds_repo import CourseCatalogRdsRepository
from services.course_management.repo import CourseCatalogRepository
from services.course_management.service import CourseManagementService
from services.course_management.storage import CourseMediaStorage
from services.enrollment.ports import EnrollmentRepositoryPort
from services.enrollment.rds_repo import EnrollmentRdsRepository
from services.enrollment.repo import EnrollmentRepository


@dataclass(frozen=True)
class AwsDeps:
    cfg: AppConfig
    service: CourseManagementService
    auth_service: UserProfileService


_cached: Dict[str, Any] = {}


ConnectionFactory = Callable[[], Any]


# ---------------------------------------------------------------------------
# Indirection hooks for testability.
#
# These two attributes exist so tests can monkeypatch
# ``bootstrap._secretsmanager_client`` and ``bootstrap._psycopg2_connect``
# without reaching into boto3 / psycopg2 globals. In production they resolve
# to the real SDK calls on first use.
# ---------------------------------------------------------------------------


def _secretsmanager_client() -> Any:
    import boto3

    return boto3.client("secretsmanager")


def _psycopg2_connect(**kwargs: Any) -> Any:
    import psycopg2

    return psycopg2.connect(**kwargs)


def _build_rds_connection_factory(cfg: AppConfig) -> ConnectionFactory:
    """Return a ``() -> connection`` callable that lazily opens a PostgreSQL
    connection using credentials fetched from Secrets Manager.

    The factory is called at most once per warm Lambda container (caching in
    the repo adapters themselves), so the Secrets Manager fetch happens on the
    first query rather than at cold-start import time. This keeps import cheap
    when the Lambda is invoked but does not touch RDS.
    """
    if not cfg.db_secret_arn:
        raise RuntimeError("DB_SECRET_ARN is required when USE_RDS=true")
    if not cfg.db_host:
        raise RuntimeError("DB_HOST is required when USE_RDS=true")

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
            # TLS is enforced even inside the VPC (defense in depth). RDS
            # PostgreSQL supports TLS out of the box.
            sslmode="require",
            # Fail fast on a stuck connect instead of hanging up to the Lambda
            # timeout: 5 seconds is comfortable once the ENI is attached.
            connect_timeout=5,
        )

    return factory


def _build_course_repo(
    cfg: AppConfig, conn_factory: Optional[ConnectionFactory]
) -> CourseCatalogRepositoryPort:
    if cfg.use_rds:
        assert conn_factory is not None  # validated by caller
        return CourseCatalogRdsRepository(conn_factory)
    if not cfg.table_name:
        raise RuntimeError("TABLE_NAME is required when USE_RDS=false")
    return CourseCatalogRepository(cfg.table_name)


def _build_enrollment_repo(
    cfg: AppConfig, conn_factory: Optional[ConnectionFactory]
) -> EnrollmentRepositoryPort:
    if cfg.use_rds:
        assert conn_factory is not None
        return EnrollmentRdsRepository(conn_factory)
    return EnrollmentRepository(cfg.table_name)


def _build_auth_repo(
    cfg: AppConfig, conn_factory: Optional[ConnectionFactory]
) -> UserProfileRepositoryPort:
    if cfg.use_rds:
        assert conn_factory is not None
        return UserProfileRdsRepository(conn_factory)
    return UserProfileRepository(cfg.table_name)


def get_cached_aws_deps() -> Optional[AwsDeps]:
    dep = _cached.get("aws")
    return dep if isinstance(dep, AwsDeps) else None


def build_aws_deps(cfg: AppConfig) -> AwsDeps:
    if not cfg.use_rds and not cfg.table_name:
        raise RuntimeError("build_aws_deps called without TABLE_NAME")

    conn_factory: Optional[ConnectionFactory] = None
    if cfg.use_rds:
        conn_factory = _build_rds_connection_factory(cfg)

    course_repo = _build_course_repo(cfg, conn_factory)
    enrollment_repo = _build_enrollment_repo(cfg, conn_factory)
    auth_repo = _build_auth_repo(cfg, conn_factory)

    storage = CourseMediaStorage(cfg.video_bucket) if cfg.video_bucket else None
    service = CourseManagementService(course_repo, storage, enrollment_repo)
    auth_service = UserProfileService(auth_repo)
    return AwsDeps(cfg=cfg, service=service, auth_service=auth_service)


def warm_aws_deps_if_needed(cfg: AppConfig) -> None:
    if not cfg.use_rds and not cfg.table_name:
        return
    if "aws" not in _cached:
        _cached["aws"] = build_aws_deps(cfg)


def lambda_bootstrap() -> Tuple[AppConfig, Optional[CourseManagementService], Optional[UserProfileService]]:
    """
    Composition root: load config and construct dependencies once.
    When neither USE_RDS nor TABLE_NAME is set the catalog cannot be wired, so
    ``(cfg, None, None)`` is returned and the handler responds with a
    configuration error.
    """
    cfg = load_config()
    if not cfg.use_rds and not cfg.table_name:
        return cfg, None, None

    existing = get_cached_aws_deps()
    if existing is not None:
        return existing.cfg, existing.service, existing.auth_service

    deps = build_aws_deps(cfg)
    _cached["aws"] = deps
    return deps.cfg, deps.service, deps.auth_service
