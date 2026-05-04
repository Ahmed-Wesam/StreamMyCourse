"""Prepend the vendored-deps directory to ``sys.path`` as a side effect of import.

``scripts/deploy-backend.sh`` runs
``pip install -r requirements.txt -t infrastructure/lambda/catalog/_vendor`` before
zipping the Lambda bundle. At runtime Python needs ``_vendor`` on ``sys.path`` so
``import psycopg2`` resolves to the vendored wheel.

This module is imported *first* from ``index.py`` -- before any other project
imports -- to guarantee ``sys.path`` is patched before any repo module triggers
``import psycopg2``. When the directory is absent (local unit tests running
without vendored deps, or DynamoDB-only deploys), this is a no-op.
"""

from __future__ import annotations

import os
import sys

_VENDOR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor")

if os.path.isdir(_VENDOR_DIR) and _VENDOR_DIR not in sys.path:
    sys.path.insert(0, _VENDOR_DIR)
