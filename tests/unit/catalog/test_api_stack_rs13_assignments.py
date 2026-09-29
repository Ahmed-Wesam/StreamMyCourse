"""RS-13: assignments API Gateway methods, Cognito, IAM prefix, deployment V42."""

from __future__ import annotations

from pathlib import Path

_API_STACK = (
    Path(__file__).resolve().parents[3] / "infrastructure" / "templates" / "api-stack.yaml"
)

_COGNITO_METHODS = (
    "CourseAssignmentsGetMethod",
    "CourseAssignmentsPostMethod",
    "CourseAssignmentIdGetMethod",
    "CourseAssignmentIdPatchMethod",
    "CourseAssignmentIdDeleteMethod",
    "CourseAssignmentImagesPostMethod",
    "CourseAssignmentImageCompletePostMethod",
    "CourseAssignmentImageUrlGetMethod",
    "CourseAssignmentSubmissionsGetMethod",
    "CourseAssignmentSubmissionsPostMethod",
    "CourseAssignmentSubmissionIdGetMethod",
    "CourseAssignmentSubmissionFilesPostMethod",
    "CourseAssignmentSubmissionFileCompletePostMethod",
    "CourseAssignmentSubmissionFileUrlGetMethod",
    "CourseAssignmentSubmitPostMethod",
    "CourseAssignmentGradePostMethod",
)

_OPTIONS_METHODS = (
    "CourseAssignmentsOptionsMethod",
    "CourseAssignmentIdOptionsMethod",
    "CourseAssignmentImagesOptionsMethod",
    "CourseAssignmentImageCompleteOptionsMethod",
    "CourseAssignmentImageUrlOptionsMethod",
    "CourseAssignmentSubmissionsOptionsMethod",
    "CourseAssignmentSubmissionIdOptionsMethod",
    "CourseAssignmentSubmissionFilesOptionsMethod",
    "CourseAssignmentSubmissionFileCompleteOptionsMethod",
    "CourseAssignmentSubmissionFileUrlOptionsMethod",
    "CourseAssignmentSubmitOptionsMethod",
    "CourseAssignmentGradeOptionsMethod",
)

_DEPLOYMENT_METHODS = _COGNITO_METHODS + _OPTIONS_METHODS


def test_rs13_assignment_methods_use_cognito_except_options() -> None:
    text = _API_STACK.read_text(encoding="utf-8")
    for logical_id in _COGNITO_METHODS:
        block = text.split(f"{logical_id}:", 1)[1].split("\n\n", 1)[0]
        assert "AuthorizationType: COGNITO_USER_POOLS" in block, logical_id
        assert "CatalogApiTokenAuthorizer" in block, logical_id
    for logical_id in _OPTIONS_METHODS:
        block = text.split(f"{logical_id}:", 1)[1].split("\n\n", 1)[0]
        assert "AuthorizationType: NONE" in block, logical_id
        assert "HttpMethod: OPTIONS" in block, logical_id


def test_rs13_assignment_methods_in_deployment_v42() -> None:
    text = _API_STACK.read_text(encoding="utf-8")
    assert "CatalogApiDeploymentV43:" in text
    deployment_block = text.split("CatalogApiDeploymentV43:", 1)[1].split(
        "CatalogApiStage:", 1
    )[0]
    for logical_id in _DEPLOYMENT_METHODS:
        assert logical_id in deployment_block, logical_id
    assert "DeploymentId: !Ref CatalogApiDeploymentV43" in text
    # Stage must not remain pinned to the previous deployment.
    stage_block = text.split("CatalogApiStage:", 1)[1].split("\n\n", 1)[0]
    assert "CatalogApiDeploymentV42" not in stage_block


def test_rs13_s3_get_object_includes_assignments_prefix_not_whole_bucket() -> None:
    text = _API_STACK.read_text(encoding="utf-8")
    assert "arn:aws:s3:::${VideoBucketName}/*/assignments/*" in text
    # Least privilege: GetObject must not grant the whole bucket.
    get_object_start = text.index("s3:GetObject")
    get_object_block = text[get_object_start : get_object_start + 1200]
    assert "arn:aws:s3:::${VideoBucketName}/*'" not in get_object_block
    assert 'arn:aws:s3:::${VideoBucketName}/*"' not in get_object_block
