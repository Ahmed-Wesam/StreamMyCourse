"""RS-16 course seed document: four prototype courses and page_content keys."""

from __future__ import annotations

import json
from pathlib import Path

from services.course_management.course_page_validation import (
    validate_and_normalize_course_page,
)

_ALLOWED_PAGE_KEYS = frozenset(
    {
        "subtitle",
        "level",
        "estimatedHours",
        "catalogSkills",
        "curriculumLead",
        "problem",
        "outcomes",
        "inside",
        "handsOn",
        "highlights",
        "audience",
        "assessment",
        "enrollCta",
    }
)

_OMITTED_HEADINGS = (
    "Part of a Bigger Research Journey",
    "One Concept. Many Study Designs",
    "Common Reasons Manuscripts Get Rejected",
    "Tools You'll Use",
)

_EXPECTED = (
    {
        "title": "Research Methodology",
        "description_prefix": "Learn to design rigorous, ethical research studies",
        "level": "Beginner",
        "estimatedHours": 15,
        "lesson_count": 75,
        "first_lesson": "What Is Research?",
        "modules": (
            "Introduction to Medical Research",
            "Finding Research Ideas",
            "Literature Review",
            "Research Questions & Hypotheses",
            "Study Designs",
            "Variables & Measurements",
            "Sampling",
            "Bias & Validity",
            "Ethics & Approvals",
            "Data Collection",
            "Writing The Methodology Section",
            "Protocol Development",
        ),
    },
    {
        "title": "Statistics & SPSS",
        "description_prefix": "Master practical biostatistics",
        "level": "Beginner\u2013Intermediate",
        "estimatedHours": 20,
        "lesson_count": 71,
        "first_lesson": "Welcome & Course Roadmap",
        "modules": (
            "Introduction to Research Statistics & SPSS",
            "Data Management & Data Cleaning",
            "Descriptive Statistics",
            "Choosing the Correct Statistical Test",
            "Comparing Groups",
            "Association Analysis",
            "Regression Analysis",
            "Writing Methods & Results",
            "Real-World Applications",
            "Final Project",
        ),
    },
    {
        "title": "Scientific Writing",
        "description_prefix": "Turn your results into a clear, publishable manuscript",
        "level": "Beginner\u2013Intermediate",
        "estimatedHours": 12,
        "lesson_count": 51,
        "first_lesson": "Why Scientific Writing Matters",
        "modules": (
            "Introduction to Scientific Writing",
            "Understanding Manuscript Structure",
            "Writing Effective Titles & Abstracts",
            "Writing The Introduction",
            "Writing The Methods Section",
            "Writing The Results Section",
            "Writing The Discussion Section",
            "References & Citation Management",
            "Journal Selection",
            "Submission Preparation",
            "Peer Review & Revisions",
            "Final Manuscript Project",
        ),
    },
    {
        "title": "Systematic Reviews & Meta-Analysis",
        "description_prefix": "Plan and complete a systematic review and meta-analysis",
        "level": "Intermediate",
        "estimatedHours": 18,
        "lesson_count": 43,
        "first_lesson": "What Is a Systematic Review?",
        "modules": (
            "Introduction to Evidence Synthesis",
            "Research Questions",
            "Protocol Development",
            "Database Searching",
            "Study Screening",
            "Data Extraction",
            "Risk of Bias Assessment",
            "Introduction to Meta-Analysis",
            "Interpretation",
            "PRISMA Reporting",
            "Writing The Review",
            "Final Project",
        ),
    },
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _courses_path() -> Path:
    return _repo_root() / "scripts" / "rs16-seed" / "courses.json"


def _load() -> dict:
    path = _courses_path()
    assert path.is_file(), f"missing seed document {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def test_seed_document_has_four_courses_at_5000_cents() -> None:
    doc = _load()
    courses = doc["courses"]
    assert len(courses) == 4
    titles = [course["title"] for course in courses]
    assert titles == [item["title"] for item in _EXPECTED]
    for course in courses:
        assert course["priceAmountMinor"] == 5000
        assert course["status"] == "PUBLISHED"


def test_page_content_round_trips_validation_without_extra_keys() -> None:
    doc = _load()
    for course, expected in zip(doc["courses"], _EXPECTED, strict=True):
        page = course["pageContent"]
        assert set(page.keys()) <= _ALLOWED_PAGE_KEYS
        unknown = set(page.keys()) - _ALLOWED_PAGE_KEYS
        assert not unknown
        normalized = validate_and_normalize_course_page(page)
        assert normalized == page
        assert page["level"] == expected["level"]
        assert page["estimatedHours"] == expected["estimatedHours"]
        assert course["description"].startswith(expected["description_prefix"])
        blob = json.dumps(page, ensure_ascii=False)
        for heading in _OMITTED_HEADINGS:
            assert heading not in blob


def test_module_and_lesson_order_matches_prototype_curriculum() -> None:
    doc = _load()
    for course, expected in zip(doc["courses"], _EXPECTED, strict=True):
        modules = course["modules"]
        assert [module["title"] for module in modules] == list(expected["modules"])
        lesson_count = 0
        for module in modules:
            titles = module["lessons"]
            assert titles, module["title"]
            assert titles == [title.strip() for title in titles]
            lesson_count += len(titles)
        assert lesson_count == expected["lesson_count"]
        assert modules[0]["lessons"][0] == expected["first_lesson"]

    stats = doc["courses"][1]
    association = next(
        module for module in stats["modules"] if module["title"] == "Association Analysis"
    )
    assert "Fisher's Exact Test" in association["lessons"]

    methodology = doc["courses"][0]
    study_designs = next(
        module for module in methodology["modules"] if module["title"] == "Study Designs"
    )
    assert "when and why" in study_designs["description"]
