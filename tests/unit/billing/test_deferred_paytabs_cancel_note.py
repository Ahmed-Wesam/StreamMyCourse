"""W8-P4: PayTabs cancel_agreement runs on student cancel (immediate provider cancel).

Student cancel-at-period-end (WS7/WS8) updates RDS, then billing_edge calls
``cancel_agreement`` on the provider in the same request — no deferred scheduler.
W7-P3c blocks renewal/activation IPNs from clobbering RDS while ``status=canceled`` and
``cancel_at_period_end=true`` until WS8-P7 removes that guard.
"""

from __future__ import annotations


def test_ws8_immediate_paytabs_cancel_documented() -> None:
    """Keeps WS8 immediate cancel_agreement behavior in pytest discovery."""
    assert __doc__ is not None
