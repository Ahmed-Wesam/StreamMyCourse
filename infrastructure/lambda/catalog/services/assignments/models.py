"""RS-13 assignment domain constants."""

from __future__ import annotations

MAX_ASSIGNMENTS_PER_COURSE = 20
MAX_CRITERIA_PER_ASSIGNMENT = 12
MAX_FILES_PER_SUBMISSION = 10

MIN_TITLE_LEN = 1
MAX_TITLE_LEN = 200
MIN_CRITERION_LABEL_LEN = 1
MAX_CRITERION_LABEL_LEN = 120
MIN_CRITERION_MAX_POINTS = 1
MAX_CRITERION_MAX_POINTS = 100

MIN_PASS_PERCENT = 1
MAX_PASS_PERCENT = 100
DEFAULT_PASS_PERCENT = 70

MAX_PLAIN_OR_RICH_LEN = 8000
MIN_NOTE_LEN = 1
MAX_NOTE_LEN = 4000
MIN_FEEDBACK_LEN = 1
MAX_FEEDBACK_LEN = 4000

MAX_IMAGE_BYTES = 52_428_800  # 50 MiB
MAX_SUBMISSION_FILE_BYTES = 104_857_600  # 100 MiB
PRESIGN_GET_TTL_SECONDS = 300

ALLOWED_IMAGE_CONTENT_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/webp", "image/gif"}
)
ALLOWED_SUBMISSION_FILE_TYPES = frozenset({"pdf", "csv", "xlsx", "docx", "sav"})

IMAGE_SLOTS = frozenset({"instructions", "rubric"})

CONTENT_TYPE_FOR_FILE_TYPE = {
    "pdf": "application/pdf",
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "sav": "application/x-spss-sav",
}

EXT_FOR_IMAGE_CONTENT_TYPE = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}

RICH_TEXT_ALLOWED_TAGS = frozenset({"p", "br", "strong", "em", "ul", "ol", "li", "a"})
