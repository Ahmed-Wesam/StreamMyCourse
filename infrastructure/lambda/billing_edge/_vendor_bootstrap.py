"""Prepend ``_vendor`` to ``sys.path`` for Lambda wheels installed by deploy-payments.sh."""

from __future__ import annotations

import os
import sys

_VENDOR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor")

if os.path.isdir(_VENDOR_DIR) and _VENDOR_DIR not in sys.path:
    sys.path.insert(0, _VENDOR_DIR)
