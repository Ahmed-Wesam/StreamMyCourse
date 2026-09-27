"""Domain types for one-time purchases (RS-5)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class BundleOffer:
    amount_minor: int
    currency: str


@dataclass(frozen=True)
class PurchaseRecord:
    id: str
    product_type: str
    course_id: Optional[str]
    status: str
    amount_minor: int
    currency: str
    created_at: datetime


__all__ = ["BundleOffer", "PurchaseRecord"]
