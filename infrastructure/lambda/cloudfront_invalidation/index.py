"""Invoke-only Lambda: CloudFront CreateInvalidation for this stack's video distribution.

Env: ``DISTRIBUTION_ID`` (required). Event JSON: ``{"paths": ["/path1", ...]}`` (each path
should start with ``/``; normalized if missing). Returns ``invalidationId``, ``status``."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        distribution_id = os.environ.get("DISTRIBUTION_ID")
        if not distribution_id:
            logger.error("DISTRIBUTION_ID environment variable is required")
            return {
                "statusCode": 500,
                "error": "DISTRIBUTION_ID environment variable not set",
            }

        paths = event.get("paths", [])
        if not paths:
            logger.error("No paths provided in event")
            return {"statusCode": 400, "error": "paths is required in event"}

        if not isinstance(paths, list):
            paths = [paths]

        normalized_paths: List[str] = []
        for path in paths:
            if not path.startswith("/"):
                path = "/" + path
            normalized_paths.append(path)

        logger.info(
            "Creating CloudFront invalidation",
            extra={
                "distribution_id": distribution_id,
                "path_count": len(normalized_paths),
            },
        )

        cloudfront = boto3.client("cloudfront")
        response = cloudfront.create_invalidation(
            DistributionId=distribution_id,
            InvalidationBatch={
                "Paths": {
                    "Quantity": len(normalized_paths),
                    "Items": normalized_paths,
                },
                "CallerReference": str(context.aws_request_id)
                if context
                else f"invalidation-{hash(str(normalized_paths))}",
            },
        )

        invalidation = response.get("Invalidation", {})
        invalidation_id = invalidation.get("Id", "unknown")
        status = invalidation.get("Status", "Unknown")
        create_time = invalidation.get("CreateTime", "")

        logger.info(
            "CloudFront invalidation created",
            extra={
                "invalidation_id": invalidation_id,
                "status": status,
                "create_time": str(create_time),
            },
        )

        return {
            "invalidationId": invalidation_id,
            "status": status,
            "createTime": str(create_time) if create_time else None,
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        logger.error(
            "AWS API error creating invalidation",
            extra={"error_code": error_code, "error_message": error_message},
        )
        return {
            "statusCode": 500,
            "error": f"AWS API error: {error_code}",
            "errorMessage": error_message,
        }
    except Exception as e:
        logger.exception("Unexpected error creating invalidation")
        return {
            "statusCode": 500,
            "error": "Internal error",
            "errorMessage": str(e),
        }
