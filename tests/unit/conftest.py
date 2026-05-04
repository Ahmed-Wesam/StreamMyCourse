"""Shared fixtures for the Lambda unit-test suite.

The suite runs with **no AWS credentials and no network**: every test patches the
boto3/S3 boundary inside `repo.py` / `storage.py` so nothing is dispatched to
AWS. Keep this conftest minimal — module-specific fixtures belong next to the
tests that use them.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Callable, Dict, Optional
from uuid import UUID

import pytest


# Belt-and-suspenders: pytest.ini already adds the lambda src to pythonpath,
# but if someone runs `pytest path/to/test_file.py` from elsewhere we still
# want imports like `from services.common.errors import ...` to resolve.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_LAMBDA_SRC = os.path.abspath(
    os.path.join(_THIS_DIR, "..", "..", "infrastructure", "lambda", "catalog")
)
if _LAMBDA_SRC not in sys.path:
    sys.path.insert(0, _LAMBDA_SRC)


@pytest.fixture
def make_lambda_event() -> Callable[..., Dict[str, Any]]:
    """Build a minimal API Gateway v2 event dict for handler/controller tests."""

    def _make(
        *,
        method: str = "GET",
        path: str = "/",
        body: Any = None,
        headers: Optional[Dict[str, str]] = None,
        is_base64: bool = False,
    ) -> Dict[str, Any]:
        evt: Dict[str, Any] = {
            "requestContext": {"http": {"method": method}},
            "rawPath": path,
            "headers": headers or {},
        }
        if body is not None:
            if isinstance(body, (dict, list)):
                evt["body"] = json.dumps(body)
            else:
                evt["body"] = body
        if is_base64:
            evt["isBase64Encoded"] = True
        return evt

    return _make


@pytest.fixture
def frozen_uuid() -> UUID:
    """Stable UUID returned by patched `uuid4` calls in storage tests."""
    return UUID("12345678-1234-5678-1234-567812345678")
