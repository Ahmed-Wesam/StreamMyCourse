"""Load billing_edge / billing_fulfillment Lambda modules for unit tests."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_BILLING_EDGE_DIR = (
    Path(__file__).resolve().parents[3]
    / "infrastructure"
    / "lambda"
    / "billing_edge"
)

# Re-export for tests that inspect handler source on disk.
BILLING_EDGE_DIR = _BILLING_EDGE_DIR

_BILLING_FULFILL_DIR = (
    Path(__file__).resolve().parents[3]
    / "infrastructure"
    / "lambda"
    / "billing_fulfillment"
)

if not _BILLING_EDGE_DIR.is_dir():
    raise ImportError(
        f"billing_edge package not found at {_BILLING_EDGE_DIR} "
        "(restore from git for Green slice)"
    )

_EDGE_PATH = str(_BILLING_EDGE_DIR)
if _EDGE_PATH not in sys.path:
    sys.path.insert(0, _EDGE_PATH)

_FULFILL_PATH = str(_BILLING_FULFILL_DIR)
if _BILLING_FULFILL_DIR.is_dir() and _FULFILL_PATH not in sys.path:
    sys.path.append(_FULFILL_PATH)


def _load(name: str) -> ModuleType:
    return importlib.import_module(name)


def _load_isolated(rel_file: str, module_name: str) -> ModuleType:
    """Load a billing_edge file without registering as top-level ``handler`` (conflicts with Cognito tests)."""
    path = _BILLING_EDGE_DIR / rel_file
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load billing_edge module from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_fulfillment_module(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    path = _BILLING_FULFILL_DIR / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


billing_edge_handler = _load_isolated("handler.py", "billing_edge_lambda_handler")
# Historical WS3 tests use this alias.
billing_handler = billing_edge_handler

catalog_invoke = _load("catalog_invoke")
edge_config = _load("edge_config")
hyperpay_adapter_mod = _load("providers.hyperpay_adapter")
hyperpay_adapter = hyperpay_adapter_mod

BillingEdgeConfig = edge_config.BillingEdgeConfig
HyperPayAdapter = hyperpay_adapter_mod.HyperPayAdapter
CheckoutProduct = _load("providers.port").CheckoutProduct
CheckoutBillingContact = _load("domain.checkout_billing").CheckoutBillingContact

if _BILLING_FULFILL_DIR.is_dir():
    billing_fulfillment_worker = _load_fulfillment_module(
        "billing_fulfillment_worker", "worker.py"
    )
else:
    billing_fulfillment_worker = None  # type: ignore[assignment]
