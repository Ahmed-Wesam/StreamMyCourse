"""Isolate video_provider_edge imports from catalog ``handler`` modules."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_VIDEO_EDGE_DIR = (
    Path(__file__).resolve().parents[3]
    / "infrastructure"
    / "lambda"
    / "video_provider_edge"
)
_EDGE_PATH = str(_VIDEO_EDGE_DIR)
if _EDGE_PATH not in sys.path:
    sys.path.append(_EDGE_PATH)


def _load_module(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    path = _VIDEO_EDGE_DIR / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_load_module("apigw_path", "apigw_path.py")
_load_module("video_catalog_invoke", "video_catalog_invoke.py")
_load_module("video_edge_config", "video_edge_config.py")
_load_module("kinescope_http", "kinescope_http.py")
video_edge_handler = _load_module("video_provider_edge_handler", "handler.py")
