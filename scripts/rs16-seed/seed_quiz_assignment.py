"""Create one Research Methodology module quiz and assignment from the prototype.

Uses the teacher HTTP API. Prints outcome lines only (no JWT, no passwords).
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

_PROTOTYPE = Path(r"D:\Desktop\Website\Frontend Course")
_COURSE_TITLE = "Research Methodology"
_QUIZ_MODULE = "Research Questions & Hypotheses"
_QUIZ_TITLE = "Introduction to Hypothesis Testing"
_DRAW_N = 15
_PASS_PERCENT = 70
_ASSIGNMENT_TITLE = "Research Proposal & Design Plan"
_ASSIGNMENT_MODULE = "Protocol Development"
_KEYS = "ABCDEFGH"

_INSTRUCTIONS = (
    "Research Proposal & Design Plan\n\n"
    "Design a complete research study based on a provided real-world scenario. "
    "You will define your research question, select an appropriate study design, "
    "describe your sampling strategy, and address the ethical considerations of "
    "your proposed study.\n\n"
    "Deliverables\n"
    "- Completed research proposal document (.docx or .pdf)\n"
    "- Research question and hypothesis statement (PICO/PECO)\n"
    "- Sampling plan with justification\n"
    "- Ethics & informed consent considerations\n\n"
    "Learning objectives\n"
    "- Formulate a clear, testable research question\n"
    "- Select an appropriate research design for the scenario\n"
    "- Justify a sampling strategy for the target population\n"
    "- Address ethical considerations in study design\n\n"
    "Passing criteria\n"
    "- Rubric score of 70% or higher\n"
    "- Research question clearly defined\n"
    "- Appropriate study design selected and justified\n"
    "- Sampling strategy included and justified\n"
    "- Ethical considerations addressed\n"
    "- All required deliverables submitted\n\n"
    "Minimum 70% required to pass."
)

_RUBRIC = (
    "Your submission is evaluated across five competency areas. "
    "Each area must demonstrate required proficiency to achieve a passing score.\n\n"
    "Research Question Development: 20 points\n"
    "Study Design Selection: 25 points\n"
    "Sampling Strategy & Recruitment: 20 points\n"
    "Ethics & Feasibility: 20 points\n"
    "Scientific Rationale & Proposal Quality: 15 points"
)

_CRITERIA = (
    {"label": "Research Question Development", "maxPoints": 20},
    {"label": "Study Design Selection", "maxPoints": 25},
    {"label": "Sampling Strategy & Recruitment", "maxPoints": 20},
    {"label": "Ethics & Feasibility", "maxPoints": 20},
    {"label": "Scientific Rationale & Proposal Quality", "maxPoints": 15},
)


def _js_string(raw: str) -> str:
    return (
        raw.replace("\\n", "\n")
        .replace("\\'", "'")
        .replace('\\"', '"')
        .replace("\\\\", "\\")
    )


def load_single_answer_questions(path: Path) -> tuple[list[dict], int]:
    """Return single-correct questions and the count of select-all items skipped."""
    text = path.read_text(encoding="utf-8")
    start = text.find("var QUESTION_BANK_STATS=")
    if start < 0:
        raise ValueError("QUESTION_BANK_STATS not found")
    end = text.find("];", start)
    if end < 0:
        raise ValueError("QUESTION_BANK_STATS end not found")
    block = text[start:end]
    chunks = re.split(r"\n\s*\{id:'q", block)
    questions: list[dict] = []
    skipped = 0
    for chunk in chunks[1:]:
        stem_m = re.search(r"stem:'((?:\\'|[^'])*)'", chunk)
        options_m = re.search(r"options:\[(.*?)\],", chunk, flags=re.S)
        correct_m = re.search(r"correct:\[([0-9,\s]+)\]", chunk)
        if not stem_m or not options_m or not correct_m:
            continue
        correct = [int(part) for part in correct_m.group(1).split(",") if part.strip()]
        if len(correct) != 1:
            skipped += 1
            continue
        options = [
            _js_string(item)
            for item in re.findall(r"'((?:\\'|[^'])*)'", options_m.group(1))
        ]
        media_m = re.search(r"media:'((?:\\'|[^'])*)'", chunk)
        stem = _js_string(stem_m.group(1))
        if media_m:
            stem = stem + "\n\n" + _js_string(media_m.group(1))
        if not options or correct[0] >= len(options):
            skipped += 1
            continue
        questions.append(
            {
                "promptText": stem,
                "optionsJson": [
                    {"key": _KEYS[index], "text": option}
                    for index, option in enumerate(options)
                ],
                "correctOptionKey": _KEYS[correct[0]],
            }
        )
    return questions, skipped


class Api:
    def __init__(self, base: str, token: str) -> None:
        self._base = base.rstrip("/")
        self._token = token

    def request(self, method: str, path: str, body: dict | None = None) -> tuple[int, object]:
        data = None
        headers = {"Authorization": "Bearer " + self._token, "Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            self._base + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
                return resp.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                parsed = {"message": raw[:180]}
            return exc.code, parsed


def _fail(label: str, status: int, body: object) -> None:
    code = ""
    if isinstance(body, dict):
        code = str(body.get("code") or body.get("message") or "")[:120]
    print(label + "=failed status=" + str(status) + " code=" + code)


def _course_id(api: Api) -> str | None:
    status, body = api.request("GET", "/courses/mine")
    if status != 200 or not isinstance(body, list):
        _fail("quiz", status, body)
        return None
    for course in body:
        if isinstance(course, dict) and course.get("title") == _COURSE_TITLE:
            course_id = course.get("id")
            if isinstance(course_id, str) and course_id:
                return course_id
    print("quiz=failed status=404 code=course_not_found")
    return None


def _modules(api: Api, course_id: str) -> list[dict] | None:
    status, body = api.request("GET", "/courses/" + course_id + "/modules")
    if status != 200 or not isinstance(body, list):
        _fail("quiz", status, body)
        return None
    return [item for item in body if isinstance(item, dict)]


def _module_id(modules: list[dict], title: str) -> str | None:
    for module in modules:
        if module.get("title") == title and isinstance(module.get("id"), str):
            return module["id"]
    return None


def seed_quiz(api: Api, course_id: str, modules: list[dict]) -> None:
    module_id = _module_id(modules, _QUIZ_MODULE)
    if not module_id:
        print("quiz=failed status=404 code=module_not_found")
        return
    status, quizzes = api.request("GET", "/courses/" + course_id + "/module-quizzes")
    if status != 200 or not isinstance(quizzes, list):
        _fail("quiz", status, quizzes)
        return
    for quiz in quizzes:
        if isinstance(quiz, dict) and quiz.get("moduleId") == module_id:
            print("quiz=exists")
            return
    questions, skipped = load_single_answer_questions(_PROTOTYPE / "Quiz.html")
    if len(questions) < _DRAW_N:
        print("quiz=failed status=0 code=not_enough_questions")
        return
    status, bank = api.request(
        "POST",
        "/courses/" + course_id + "/question-banks",
        {"name": _QUIZ_TITLE},
    )
    if status != 201 or not isinstance(bank, dict):
        _fail("quiz", status, bank)
        return
    bank_id = bank.get("questionBankId")
    if not isinstance(bank_id, str):
        print("quiz=failed status=201 code=missing_bank_id")
        return
    for question in questions:
        q_status, q_body = api.request(
            "POST",
            "/courses/" + course_id + "/question-banks/" + bank_id + "/questions",
            question,
        )
        if q_status != 201:
            _fail("quiz", q_status, q_body)
            return
    status, quiz_body = api.request(
        "POST",
        "/courses/" + course_id + "/modules/" + module_id + "/quiz",
        {"questionBankId": bank_id, "passPercent": _PASS_PERCENT},
    )
    if status != 201:
        _fail("quiz", status, quiz_body)
        return
    status, pub_body = api.request(
        "POST",
        "/courses/" + course_id + "/question-banks/" + bank_id + "/publish",
        {"n": _DRAW_N, "moduleId": module_id},
    )
    if status != 200:
        _fail("quiz", status, pub_body)
        return
    print(
        "quiz=created questions="
        + str(len(questions))
        + " skipped_multi="
        + str(skipped)
        + " draw="
        + str(_DRAW_N)
    )


def seed_assignment(api: Api, course_id: str, modules: list[dict]) -> None:
    module_id = _module_id(modules, _ASSIGNMENT_MODULE)
    if not module_id:
        print("assignment=failed status=404 code=module_not_found")
        return
    status, listed = api.request("GET", "/courses/" + course_id + "/assignments")
    if status != 200 or not isinstance(listed, dict):
        _fail("assignment", status, listed)
        return
    existing = listed.get("assignments")
    if isinstance(existing, list):
        for item in existing:
            if isinstance(item, dict) and item.get("title") == _ASSIGNMENT_TITLE:
                print("assignment=exists")
                return
    status, created = api.request(
        "POST",
        "/courses/" + course_id + "/assignments",
        {
            "title": _ASSIGNMENT_TITLE,
            "moduleId": module_id,
            "passPercent": _PASS_PERCENT,
            "countsTowardCertificate": True,
        },
    )
    if status != 201 or not isinstance(created, dict):
        _fail("assignment", status, created)
        return
    assignment = created.get("assignment")
    assignment_id = assignment.get("id") if isinstance(assignment, dict) else None
    if not isinstance(assignment_id, str):
        print("assignment=failed status=201 code=missing_assignment_id")
        return
    status, updated = api.request(
        "PATCH",
        "/courses/" + course_id + "/assignments/" + assignment_id,
        {
            "instructions": {"mode": "plain", "text": _INSTRUCTIONS},
            "rubric": {"mode": "plain", "text": _RUBRIC},
            "criteria": list(_CRITERIA),
            "status": "published",
        },
    )
    if status != 200:
        _fail("assignment", status, updated)
        return
    print("assignment=created")


def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] == "--extract-only":
        questions, skipped = load_single_answer_questions(_PROTOTYPE / "Quiz.html")
        print("questions=" + str(len(questions)) + " skipped_multi=" + str(skipped))
        return
    base = (os.environ.get("RS16_API_BASE") or "").strip()
    token = (os.environ.get("RS16_TEACHER_JWT") or "").strip()
    if not base or not token:
        print("quiz_assignment=not_done jwt_or_api_missing")
        raise SystemExit(2)
    api = Api(base, token)
    course_id = _course_id(api)
    if not course_id:
        raise SystemExit(2)
    modules = _modules(api, course_id)
    if modules is None:
        raise SystemExit(2)
    seed_quiz(api, course_id, modules)
    seed_assignment(api, course_id, modules)


if __name__ == "__main__":
    main()
