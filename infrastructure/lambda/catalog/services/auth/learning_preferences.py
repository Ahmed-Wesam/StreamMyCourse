"""RS-16 built learning preferences stored on the user row."""

from __future__ import annotations

from typing import Final

# Stable keys for the five Settings research interests. Display labels live in the UI.
RESEARCH_INTEREST_TAG_KEYS: Final[tuple[str, ...]] = (
    "surgical_research",
    "systematic_reviews",
    "meta_analysis",
    "clinical_research",
    "database_research",
)
RESEARCH_INTEREST_TAG_SET: Final[frozenset[str]] = frozenset(RESEARCH_INTEREST_TAG_KEYS)

# Prototype Settings.html defaults for the built preferences.
DEFAULT_AUTOPLAY_NEXT: Final[bool] = True
DEFAULT_AUTO_MARK_COMPLETE: Final[bool] = True
DEFAULT_PROGRESS_CELEBRATIONS: Final[bool] = True
DEFAULT_RESEARCH_INTEREST_TAGS: Final[tuple[str, ...]] = (
    "systematic_reviews",
    "meta_analysis",
)
