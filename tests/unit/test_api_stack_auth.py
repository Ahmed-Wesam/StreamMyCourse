from __future__ import annotations

import re
from pathlib import Path


_API_STACK = (
    Path(__file__).resolve().parents[2]
    / "infrastructure"
    / "templates"
    / "api-stack.yaml"
)


def _is_public_unauth_method(comment_line: str) -> bool:
    """
    We intentionally allow anonymous access only for:
    - OPTIONS preflight (every route)
    - GET catalog browsing endpoints
    """
    s = comment_line.strip()
    if not s.startswith("# API Gateway Method:"):
        return False
    if "OPTIONS " in s:
        return True
    return s.endswith("GET /courses") or s.endswith("GET /courses/{courseId}") or s.endswith(
        "GET /courses/{courseId}/lessons"
    ) or s.endswith("GET /courses/{courseId}/modules")


def test_only_expected_methods_are_unauthenticated() -> None:
    text = _API_STACK.read_text(encoding="utf-8")

    # Heuristic parser: for each "API Gateway Method" block, inspect the declared HttpMethod and AuthorizationType.
    blocks = re.split(r"(?m)^\s*#\s*API Gateway Method:", text)
    assert len(blocks) > 5  # sanity check template parsed

    offenders: list[str] = []
    for b in blocks[1:]:
        header_line = "# API Gateway Method:" + b.splitlines()[0]
        http_method = None
        auth_type = None
        for line in b.splitlines():
            if http_method is None:
                m = re.match(r"^\\s*HttpMethod:\\s*(\\w+)\\s*$", line)
                if m:
                    http_method = m.group(1)
                    continue
            if auth_type is None:
                m = re.match(r"^\\s*AuthorizationType:\\s*(\\S+)\\s*$", line)
                if m:
                    auth_type = m.group(1)
                    continue
            if http_method and auth_type:
                break

        if http_method is None or auth_type is None:
            continue

        if auth_type == "NONE" and not _is_public_unauth_method(header_line):
            offenders.append(header_line.strip())

    assert offenders == [], "Unexpected unauthenticated methods:\\n" + "\\n".join(offenders)

