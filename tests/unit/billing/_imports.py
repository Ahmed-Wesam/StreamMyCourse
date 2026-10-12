"""Load billing_edge Lambda modules (flat imports under infrastructure/lambda/billing_edge)."""

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

if not _BILLING_EDGE_DIR.is_dir():
    raise ImportError(
        f"billing_edge package not found at {_BILLING_EDGE_DIR} "
        "(restore from git da82b89 for Green slice)"
    )

_EDGE_PATH = str(_BILLING_EDGE_DIR)
if _EDGE_PATH not in sys.path:
    sys.path.insert(0, _EDGE_PATH)


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


billing_edge_handler = _load_isolated("handler.py", "billing_edge_lambda_handler")
catalog_invoke = _load("catalog_invoke")
edge_config = _load("edge_config")
hyperpay_adapter_mod = _load("providers.hyperpay_adapter")
hyperpay_adapter = hyperpay_adapter_mod

BillingEdgeConfig = edge_config.BillingEdgeConfig
HyperPayAdapter = hyperpay_adapter_mod.HyperPayAdapter
CheckoutProduct = _load("providers.port").CheckoutProduct
CheckoutBillingContact = _load("domain.checkout_billing").CheckoutBillingContact
