"""Prepend the vendored-deps directory to ``sys.path`` as a side effect of import.

Deploy scripts install ``cryptography`` into ``_vendor/`` via
``pip install -r requirements.txt -t _vendor``. At runtime Python needs
``_vendor`` on ``sys.path`` so ``from cryptography...`` resolves.

This module is imported *first* from ``index.py`` to guarantee the path is
patched before any code triggers ``import cryptography``.
"""

from __future__ import annotations

import os
import sys

_VENDOR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor")

if os.path.isdir(_VENDOR_DIR) and _VENDOR_DIR not in sys.path:
    sys.path.insert(0, _VENDOR_DIR)
