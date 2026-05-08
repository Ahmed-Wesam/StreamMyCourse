"""Diagnostic stage tracer for the catalog Lambda (TEMPORARY).

Writes single-line markers directly to stderr with an explicit flush so they
land in CloudWatch even if the container is SIGKILL'd before Python's logging
handlers flush. Used to pinpoint exactly which step of a request is hanging
when CloudWatch shows START -> 15000ms timeout with no application logs.

This module MUST be reverted (or its calls dropped) once the root cause is
identified. ``CATALOG_TRACE=0`` in env disables emission without a redeploy.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

_ENABLED = os.environ.get("CATALOG_TRACE", "1") != "0"


def trace(stage: str, **fields: Any) -> None:
    if not _ENABLED:
        return
    parts = [f"[trace] t={time.monotonic():.3f}", f"stage={stage}"]
    for k, v in fields.items():
        s = str(v).replace("\n", " ").replace(" ", "_")
        if len(s) > 80:
            s = s[:77] + "..."
        parts.append(f"{k}={s}")
    line = " ".join(parts) + "\n"
    try:
        sys.stderr.write(line)
        sys.stderr.flush()
    except Exception:
        # Tracer must never break the request path.
        pass
