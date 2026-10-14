"""Domain types and constants for certificates (RS-12)."""

from __future__ import annotations

import re

INSTRUCTOR_NAME = "Dr. Bahaa Aburayya"
INSTRUCTOR_TITLE = "Founder & Instructor, Research Spectrum"

CREDENTIAL_ID_RE = re.compile(r"^RS-[0-9A-F]{6}-[0-9]{4}-[0-9A-F]{10}$")

PROFILE_INCOMPLETE_MESSAGE = "Add your profile name to issue this certificate."
PROFILE_HREF = "/account/profile"

BUNDLE_COURSE_TITLE = "Research Mastery Bundle"
BUNDLE_CERTIFICATE_CODE = "B00001"

PATHWAY_COURSE_TITLES: tuple[str, ...] = (
    "Research Methodology",
    "Statistics & SPSS",
    "Scientific Writing",
    "Systematic Reviews & Meta-Analysis",
)
