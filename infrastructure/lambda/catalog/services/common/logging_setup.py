"""Logging configuration and JSON formatter for Lambda.

Provides structured JSON logging with contextvar integration for correlation IDs.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict

from services.common import runtime_context


class JsonLogFormatter(logging.Formatter):
    """JSON formatter for structured logging.

    Outputs one JSON object per line with standard fields:
    - timestamp: ISO format UTC timestamp
    - level: Log level name
    - logger: Logger name
    - message: Log message
    - lambda_request_id, api_request_id, http_method: From contextvars (if set)
    - action: Routed handler name from contextvars (``route_or_action``)
    - api_stage, api_domain, route_key, client_ip, user_agent_snippet: API Gateway
      fields when present (see ``runtime_context.extract_apigw_public_fields``)
    - request_path: Normalized path used for in-Lambda routing (after stage strip)
    - upload_kind: For ``POST /upload-url`` (lessonVideo | courseThumbnail | lessonThumbnail)
    - exc_info: Exception info (if present)
    """

    def __init__(self) -> None:
        super().__init__()

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_obj: Dict[str, Any] = {
            "timestamp": self._format_timestamp(record.created),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add contextvar fields if available (API Gateway + routing + upload kind)
        ctx = runtime_context.get_request_context()
        for key, value in ctx.items():
            if value is None or value == "":
                continue
            if key == "route_or_action":
                log_obj["action"] = value
            else:
                log_obj[key] = value

        # Add exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_obj["exc_info"] = self._format_exception(record.exc_info)

        # Add any extra fields from the record
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "asctime",
                # Skip standard logging fields
                "timestamp",
                "level",
                "logger",
                "lambda_request_id",
                "api_request_id",
                "action",
                "http_method",
                "api_stage",
                "api_domain",
                "route_key",
                "client_ip",
                "user_agent_snippet",
                "request_path",
                "upload_kind",
            ):
                log_obj[key] = value

        # JSON encode with proper escaping
        return json.dumps(log_obj, ensure_ascii=False, default=str)

    def _format_timestamp(self, created: float) -> str:
        """Format timestamp as ISO 8601 UTC."""
        dt = datetime.fromtimestamp(created, tz=timezone.utc)
        return dt.isoformat()

    def _format_exception(self, exc_info: tuple) -> str:
        """Format exception info as string."""
        return "".join(traceback.format_exception(*exc_info))


class ContextVarFilter(logging.Filter):
    """Filter that merges contextvar fields into log records.

    This allows context data to be available on the record for formatters.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add contextvar fields to the record."""
        ctx = runtime_context.get_request_context()

        # Set attributes on the record for access by formatters
        if ctx.get("lambda_request_id"):
            record.lambda_request_id = ctx["lambda_request_id"]
        if ctx.get("api_request_id"):
            record.api_request_id = ctx["api_request_id"]
        if ctx.get("route_or_action"):
            record.action = ctx["route_or_action"]
        if ctx.get("http_method"):
            record.http_method = ctx["http_method"]
        for attr in (
            "api_stage",
            "api_domain",
            "route_key",
            "client_ip",
            "user_agent_snippet",
            "request_path",
            "upload_kind",
        ):
            val = ctx.get(attr)
            if val:
                setattr(record, attr, val)

        return True


# Track if we've configured logging (for idempotency)
_configured = False


def configure_logging() -> None:
    """Configure root logger for JSON output.

    This function is idempotent - calling it multiple times is safe.
    Sets up:
    - JSON formatter on stdout
    - ContextVarFilter for correlation IDs
    - Log level from LOG_LEVEL env var (default INFO)
    """
    global _configured

    if _configured:
        return

    # Get log level from environment
    log_level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create stdout handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    handler.addFilter(ContextVarFilter())
    root_logger.addHandler(handler)

    # Log startup message
    if log_level == logging.DEBUG:
        root_logger.warning(
            "DEBUG logging enabled - verify no sensitive data in production",
            extra={"log_level": "DEBUG"},
        )

    _configured = True


def reset_logging_configuration() -> None:
    """Reset logging configuration (useful for testing).

    Clears the configured flag so configure_logging() can be called again.
    """
    global _configured
    _configured = False
