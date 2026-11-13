"""Lesson notes domain errors (not HTTP errors)."""

from __future__ import annotations


class NoteLimitExceeded(Exception):
    """User already has the maximum number of notes for this lesson."""
