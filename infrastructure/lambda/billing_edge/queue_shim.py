"""Load ``queue/enqueue.py`` without shadowing the stdlib ``queue`` module."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ENQUEUE_PATH = Path(__file__).resolve().parent / "queue" / "enqueue.py"
_MODULE_NAME = "billing_sqs_enqueue"


def _load_enqueue_module():
    if _MODULE_NAME in sys.modules:
        return sys.modules[_MODULE_NAME]
    spec = importlib.util.spec_from_file_location(_MODULE_NAME, _ENQUEUE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load enqueue from {_ENQUEUE_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[_MODULE_NAME] = mod
    spec.loader.exec_module(mod)
    return mod


_enqueue_mod = _load_enqueue_module()
enqueue_domain_events = _enqueue_mod.enqueue_domain_events
EnqueueError = _enqueue_mod.EnqueueError
