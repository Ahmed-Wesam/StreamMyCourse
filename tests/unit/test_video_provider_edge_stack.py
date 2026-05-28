"""Contract tests: video-provider-edge-stack IAM, env, and outputs."""

from __future__ import annotations

from pathlib import Path


def _video_edge_stack_text() -> str:
    path = (
        Path(__file__).resolve().parents[2]
        / "infrastructure"
        / "templates"
        / "video-provider-edge-stack.yaml"
    )
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def test_video_provider_edge_stack_parameters() -> None:
    text = _video_edge_stack_text()
    for name in (
        "Environment:",
        "LambdaCodeS3Bucket:",
        "LambdaCodeS3Key:",
        "CatalogLambdaArn:",
        "KinescopeApiToken:",
        "KinescopeParentId:",
        "KinescopeWebhookSecret:",
        "CorsAllowOrigin:",
    ):
        assert name in text


def test_video_provider_edge_stack_lambda_env_and_invoke_iam() -> None:
    text = _video_edge_stack_text()
    assert "StreamMyCourse-VideoProviderEdge-${Environment}" in text
    assert "Handler: handler.lambda_handler" in text
    assert "VideoProviderEdgeCatalogInvokePolicy:" in text
    assert "HasCatalogLambdaArn" in text
    assert "lambda:InvokeFunction" in text

    start = text.index("  VideoProviderEdge:")
    end = text.index("Outputs:", start)
    block = text[start:end]
    assert "CATALOG_LAMBDA_ARN:" in block
    assert "KINESCOPE_API_TOKEN:" in block
    assert "KINESCOPE_PARENT_ID:" in block
    assert "KINESCOPE_WEBHOOK_SECRET:" in block
    assert "DEPLOYMENT_ENVIRONMENT:" in block
    assert "CORS_ALLOW_ORIGIN:" in block


def test_video_provider_edge_stack_output_arn() -> None:
    text = _video_edge_stack_text()
    assert "VideoProviderEdgeLambdaArn:" in text
    assert "!GetAtt VideoProviderEdge.Arn" in text
