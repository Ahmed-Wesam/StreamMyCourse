"""Domain constants and types for research team applications (RS-14)."""

from __future__ import annotations

from typing import Final

STATUSES: Final[tuple[str, ...]] = (
    "submitted",
    "under_review",
    "accepted",
    "rejected",
)

OPEN_STATUSES: Final[frozenset[str]] = frozenset({"submitted", "under_review"})

EXPERIENCE_LEVELS: Final[frozenset[str]] = frozenset(
    {"None", "Beginner", "Intermediate", "Advanced"}
)

WEEKLY_HOURS: Final[frozenset[str]] = frozenset(
    {
        "Less than 5 hours/week",
        "5–10 hours/week",
        "10–15 hours/week",
        "15–20 hours/week",
        "20+ hours/week",
    }
)

RESEARCH_AREAS: Final[tuple[str, ...]] = (
    "General Surgery",
    "Plastic Surgery",
    "Vascular Surgery",
    "Internal Medicine",
    "Cardiology",
    "Oncology",
    "Public Health",
    "Medical Education",
    "Epidemiology",
    "Systematic Reviews & Meta-Analysis",
    "Clinical Research",
    "Basic Science Research",
    "Artificial Intelligence In Healthcare",
    "Other",
)

RESEARCH_AREAS_SET: Final[frozenset[str]] = frozenset(RESEARCH_AREAS)
MAX_RESEARCH_AREAS: Final[int] = 20

CAP_FULL_NAME: Final[int] = 200
CAP_INSTITUTION: Final[int] = 200
CAP_POSITION: Final[int] = 200
CAP_INTERESTS: Final[int] = 4000
CAP_MOTIVATION: Final[int] = 8000
CAP_COUNT: Final[int] = 9999

# Fixed notify subjects — no applicant text.
SUBJECT_SUBMITTED: Final[str] = "Research Team application received"
SUBJECT_STATUS_CHANGE: Final[str] = "Research Team application update"
SUBJECT_REAPPLY: Final[str] = "Research Team reapply allowed"

BODY_SUBMITTED: Final[str] = (
    "We received your Research Team application. Our team will review it shortly."
)
BODY_STATUS_CHANGE: Final[str] = (
    "Your Research Team application status has been updated. Sign in to view details."
)
BODY_REAPPLY: Final[str] = (
    "You may submit a new Research Team application. Sign in to apply again."
)
