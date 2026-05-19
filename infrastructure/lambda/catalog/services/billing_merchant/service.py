from __future__ import annotations

from typing import Any, Dict

from services.billing_merchant.repo import MerchantAccountRdsRepository

_SETUP_CHECKLIST_KEYS = (
    "paytabsAccountCreated",
    "profileIdConfigured",
    "repeatBillingEnabled",
    "termsUrlSet",
    "ipnRegistered",
    "testChargeSucceeded",
    "payoutMarkedReady",
)


def _empty_checklist() -> Dict[str, bool]:
    return {key: False for key in _SETUP_CHECKLIST_KEYS}


def _is_placeholder_profile_id(profile_id: str | None) -> bool:
    """Deploy-time mock/placeholder profile IDs are not a configured PayTabs merchant."""
    if profile_id is None:
        return True
    normalized = str(profile_id).strip().lower()
    if not normalized:
        return True
    if normalized.startswith("mock-"):
        return True
    if normalized.startswith("placeholder-"):
        return True
    return "placeholder" in normalized


def _has_synced_profile_id(profile_id: str | None) -> bool:
    """Deploy sync wrote a Profile ID to RDS (placeholder or live)."""
    return bool(profile_id and str(profile_id).strip())


def _has_live_profile_id(profile_id: str | None) -> bool:
    return bool(profile_id and str(profile_id).strip() and not _is_placeholder_profile_id(profile_id))


def _build_setup_checklist(row: Dict[str, Any] | None) -> Dict[str, bool]:
    if row is None:
        return _empty_checklist()
    raw_profile_id = row.get("providerProfileId")
    profile_id = str(raw_profile_id) if raw_profile_id is not None else None
    has_synced_profile = _has_synced_profile_id(profile_id)
    has_live_profile = _has_live_profile_id(profile_id)
    payout_ready = bool(row.get("payoutReady"))
    return {
        # Live PayTabs merchant (non-placeholder Profile ID from operator go-live sync).
        "paytabsAccountCreated": has_live_profile,
        # Platform has a Profile ID in RDS (mock placeholder counts until go-live).
        "profileIdConfigured": has_synced_profile,
        # PayTabs Dashboard steps — no automated signal in WS4; remain pending until WS8+.
        "repeatBillingEnabled": False,
        "termsUrlSet": False,
        "ipnRegistered": False,
        # Operator test charge (WS8); not tied to payout_ready / mark-ready script.
        "testChargeSucceeded": False,
        "payoutMarkedReady": payout_ready,
    }


class MerchantStatusService:
    def __init__(
        self,
        repo: MerchantAccountRdsRepository,
        *,
        deployment_environment: str,
    ) -> None:
        self._repo = repo
        self._deployment_environment = (deployment_environment or "dev").strip().lower()

    def get_merchant_status(self) -> Dict[str, Any]:
        row = self._repo.get_merchant_account(environment=self._deployment_environment)
        if row is None:
            return {
                "provider": "paytabs",
                "providerProfileId": None,
                "payoutReady": False,
                "payoutReadyAt": None,
                "setupChecklist": _empty_checklist(),
            }
        return {
            "provider": row["provider"],
            "providerProfileId": row.get("providerProfileId"),
            "payoutReady": row["payoutReady"],
            "payoutReadyAt": row.get("payoutReadyAt"),
            "setupChecklist": _build_setup_checklist(row),
        }
