"""Contract tests: api-stack video provider edge conditional routes."""

from __future__ import annotations

from pathlib import Path


def _api_stack_text() -> str:
    path = (
        Path(__file__).resolve().parents[2]
        / "infrastructure"
        / "templates"
        / "api-stack.yaml"
    )
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def test_api_stack_video_edge_parameter_and_condition() -> None:
    text = _api_stack_text()
    assert "VideoProviderEdgeLambdaArn:" in text
    assert "IsKinescopeProvider:" in text
    assert "HasVideoProviderEdgeLambdaArn:" in text
    assert "UseKinescopeVideoEdge:" in text


def test_api_stack_catalog_strips_kinescope_http_env_when_edge_active() -> None:
    text = _api_stack_text()
    catalog_start = text.index("  CatalogLambda:")
    catalog_end = text.index("  TokenAuthorizerLambdaRole:", catalog_start)
    block = text[catalog_start:catalog_end]
    assert "KINESCOPE_DRM_JWT_SECRET: !Ref KinescopeDrmJwtSecret" in block
    assert "UseKinescopeVideoEdge" in block
    assert block.count("UseKinescopeVideoEdge") >= 3


def test_api_stack_upload_url_routes_use_edge_when_active() -> None:
    text = _api_stack_text()
    post_block = text[text.index("UploadUrlPostMethod:") : text.index("UploadUrlOptionsMethod:")]
    options_block = text[text.index("UploadUrlOptionsMethod:") : text.index("UsersMeGetMethod:")]
    for block in (post_block, options_block):
        assert "UseKinescopeVideoEdge" in block
        assert "${VideoProviderEdgeLambdaArn}/invocations" in block
        assert "${CatalogLambda.Arn}/invocations" in block


def test_api_stack_video_ready_routes_use_edge_when_active() -> None:
    text = _api_stack_text()
    put_block = text[
        text.index("LessonVideoReadyPutMethod:")
        : text.index("LessonVideoReadyOptionsMethod:")
    ]
    options_block = text[
        text.index("LessonVideoReadyOptionsMethod:")
        : text.index("PlaybackGetMethod:")
    ]
    for block in (put_block, options_block):
        assert "UseKinescopeVideoEdge" in block
        assert "${VideoProviderEdgeLambdaArn}/invocations" in block


def test_api_stack_kinescope_webhook_routes_use_edge_when_active() -> None:
    text = _api_stack_text()
    post_block = text[
        text.index("WebhooksKinescopePostMethod:")
        : text.index("WebhooksKinescopeOptionsMethod:")
    ]
    options_block = text[
        text.index("WebhooksKinescopeOptionsMethod:")
        : text.index("WebhooksKinescopeDrmAuthPostMethod:")
    ]
    for block in (post_block, options_block):
        assert "UseKinescopeVideoEdge" in block
        assert "${VideoProviderEdgeLambdaArn}/invocations" in block

    drm_block = text[text.index("WebhooksKinescopeDrmAuthPostMethod:") :]
    assert "${CatalogLambda.Arn}/invocations" in drm_block
    assert "UseKinescopeVideoEdge" not in drm_block.split("WebhooksKinescopeDrmAuthOptionsMethod:")[0]


def test_api_stack_video_edge_lambda_permission() -> None:
    text = _api_stack_text()
    assert "VideoProviderEdgeLambdaApiPermission:" in text
    perm_block = text[
        text.index("VideoProviderEdgeLambdaApiPermission:")
        : text.index("# API Gateway Method: GET /courses")
    ]
    assert "Condition: UseKinescopeVideoEdge" in perm_block
    assert "VideoProviderEdgeLambdaArn" in perm_block


def test_api_stack_video_edge_deployment_v34() -> None:
    text = _api_stack_text()
    assert "CatalogApiDeploymentV34:" in text
    assert "CatalogApiDeploymentV33:" not in text
    deployment_block = text.split("CatalogApiDeploymentV34:")[1].split("CatalogApiStage:")[0]
    assert "VideoProviderEdgeLambdaApiPermission" not in deployment_block
    assert "DeploymentId: !Ref CatalogApiDeploymentV34" in text
