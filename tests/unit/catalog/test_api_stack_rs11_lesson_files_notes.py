"""RS-11 Slice 5: lesson files and notes API Gateway methods."""

from __future__ import annotations

from pathlib import Path

_API_STACK = (
    Path(__file__).resolve().parents[3] / "infrastructure" / "templates" / "api-stack.yaml"
)

_COGNITO_METHODS = (
    "LessonFilesGetMethod",
    "LessonFilesPostMethod",
    "LessonFileIdDeleteMethod",
    "LessonFileCompletePutMethod",
    "LessonFileUrlGetMethod",
    "LessonNotesGetMethod",
    "LessonNotesPostMethod",
    "LessonNoteIdPatchMethod",
    "LessonNoteIdDeleteMethod",
)

_DEPLOYMENT_METHODS = _COGNITO_METHODS + (
    "LessonFilesOptionsMethod",
    "LessonFileIdOptionsMethod",
    "LessonFileCompleteOptionsMethod",
    "LessonFileUrlOptionsMethod",
    "LessonNotesOptionsMethod",
    "LessonNoteIdOptionsMethod",
)


def test_rs11_lesson_file_and_note_methods_use_cognito() -> None:
    text = _API_STACK.read_text(encoding="utf-8")
    for logical_id in _COGNITO_METHODS:
        block = text.split(f"{logical_id}:", 1)[1].split("\n\n", 1)[0]
        assert "AuthorizationType: COGNITO_USER_POOLS" in block, logical_id
        assert "CatalogApiTokenAuthorizer" in block, logical_id


def test_rs11_lesson_file_and_note_methods_in_deployment_v41() -> None:
    text = _API_STACK.read_text(encoding="utf-8")
    deployment_block = text.split("CatalogApiDeploymentV41:", 1)[1].split(
        "CatalogApiStage:", 1
    )[0]
    for logical_id in _DEPLOYMENT_METHODS:
        assert logical_id in deployment_block, logical_id
    assert "DeploymentId: !Ref CatalogApiDeploymentV41" in text
