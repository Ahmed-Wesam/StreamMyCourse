"""W7-P12: WS8/WS9 handoff — PayTabs cancel_agreement is deferred until period end.

Student cancel-at-period-end (WS7) updates RDS only; the PayTabs agreement stays
active until a WS8 scheduler calls cancel at ``current_period_end`` (live HTTP in WS9).
W7-P3c blocks renewal/activation IPNs from clobbering RDS while ``status=canceled`` and
``cancel_at_period_end=true``.
"""

from __future__ import annotations


def test_ws8_deferred_paytabs_cancel_documented() -> None:
    """Keeps WS8/WS9 cancel_agreement scheduler requirement in pytest discovery."""
    assert __doc__ is not None
