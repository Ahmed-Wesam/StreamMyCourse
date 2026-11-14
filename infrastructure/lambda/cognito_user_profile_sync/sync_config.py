"""Environment-driven configuration for the Cognito PostAuthentication hook."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SyncConfig:
    """Runtime configuration loaded once per cold start."""

    dsql_endpoint: str
    student_client_id: str = ""
    teacher_client_id: str = ""


def load_sync_config() -> SyncConfig:
    return SyncConfig(
        dsql_endpoint=os.environ.get("DSQL_ENDPOINT", "").strip(),
        student_client_id=os.environ.get("STUDENT_COGNITO_CLIENT_ID", "").strip(),
        teacher_client_id=os.environ.get("TEACHER_COGNITO_CLIENT_ID", "").strip(),
    )
