"""
Artifact Janitor Lambda

Cleans up old Lambda deployment artifacts from S3, keeping only
the most recent N artifacts per environment and artifact type.

Trigger: EventBridge (CloudWatch Events) - daily schedule
Environment variables:
  - ARTIFACT_BUCKET: S3 bucket name (default: auto-detected from account/region)
  - KEEP_COUNT: Number of recent artifacts to keep per group (default: 2)
  - DRY_RUN: If "true", only log what would be deleted (default: false)
"""

import os
import re
import boto3
from datetime import datetime, timezone
from typing import List, Dict, Tuple


def get_artifact_bucket() -> str:
    """Determine artifact bucket name from env or construct from caller identity."""
    bucket = os.environ.get('ARTIFACT_BUCKET')
    if bucket:
        return bucket

    sts = boto3.client('sts')
    account = sts.get_caller_identity()['Account']
    region = boto3.session.Session().region_name or 'eu-west-1'
    return f"streammycourse-artifacts-{account}-{region}"


def parse_artifact_key(key: str) -> Tuple[str, str, str]:
    """
    Parse artifact key into (type, environment, identifier).

    Expected patterns:
    - catalog-{env}-{sha}.zip -> ('catalog', 'dev', 'sha')
    - rds-schema-apply-{env}-{sha}.zip -> ('rds-schema-apply', 'dev', 'sha')

    Returns ('unknown', 'unknown', key) if pattern doesn't match.
    """
    # Pattern: {type}-{env}-{suffix}.zip
    match = re.match(r'^(.*?)-([a-z]+)-([a-f0-9]{12,})\.zip$', key)
    if match:
        artifact_type = match.group(1)  # 'catalog' or 'rds-schema-apply'
        env = match.group(2)  # 'dev', 'integ', 'prod'
        identifier = match.group(3)  # git sha or timestamp
        return (artifact_type, env, identifier)

    # Fallback for non-matching keys (timestamps, etc.)
    if '-' in key:
        parts = key.rsplit('-', 1)
        if len(parts) == 2:
            base, suffix = parts
            # Try to extract env from base
            for env in ['prod', 'integ', 'dev']:
                if f'-{env}-' in base or base.endswith(f'-{env}'):
                    artifact_type = base.replace(f'-{env}', '').replace(f'_{env}', '')
                    return (artifact_type or 'unknown', env, suffix.replace('.zip', ''))

    return ('unknown', 'unknown', key)


def group_artifacts(objects: List[Dict]) -> Dict[Tuple[str, str], List[Dict]]:
    """
    Group S3 objects by (artifact_type, environment).

    Each group will be sorted by LastModified descending.
    """
    groups: Dict[Tuple[str, str], List[Dict]] = {}

    for obj in objects:
        key = obj['Key']
        artifact_type, env, _ = parse_artifact_key(key)

        group_key = (artifact_type, env)
        if group_key not in groups:
            groups[group_key] = []
        groups[group_key].append(obj)

    # Sort each group by LastModified (newest first)
    for group_key in groups:
        groups[group_key].sort(key=lambda x: x['LastModified'], reverse=True)

    return groups


def delete_old_artifacts(bucket: str, groups: Dict[Tuple[str, str], List[Dict]],
                         keep_count: int, dry_run: bool) -> Dict:
    """
    Delete old artifacts, keeping only the most recent N per group.

    Returns statistics about the operation.
    """
    s3 = boto3.client('s3')
    stats = {
        'groups_processed': 0,
        'artifacts_kept': 0,
        'artifacts_deleted': 0,
        'bytes_deleted': 0,
        'errors': []
    }

    for (artifact_type, env), artifacts in groups.items():
        stats['groups_processed'] += 1

        # Keep the most recent N
        to_keep = artifacts[:keep_count]
        to_delete = artifacts[keep_count:]

        stats['artifacts_kept'] += len(to_keep)

        if not to_delete:
            print(f"[{artifact_type}/{env}] No old artifacts to delete (have {len(to_keep)})")
            continue

        print(f"[{artifact_type}/{env}] Keeping {len(to_keep)}, deleting {len(to_delete)} artifacts")

        for artifact in to_delete:
            key = artifact['Key']
            size = artifact['Size']
            last_modified = artifact['LastModified']
            age_days = (datetime.now(timezone.utc) - last_modified).days

            if dry_run:
                print(f"  [DRY-RUN] Would delete: {key} ({size} bytes, {age_days} days old)")
                stats['artifacts_deleted'] += 1
                stats['bytes_deleted'] += size
            else:
                try:
                    print(f"  Deleting: {key} ({size} bytes, {age_days} days old)")
                    s3.delete_object(Bucket=bucket, Key=key)
                    stats['artifacts_deleted'] += 1
                    stats['bytes_deleted'] += size
                except Exception as e:
                    error_msg = f"Failed to delete {key}: {str(e)}"
                    print(f"  ERROR: {error_msg}")
                    stats['errors'].append(error_msg)

    return stats


def lambda_handler(event, context):
    """
    Main entry point for Lambda execution.
    """
    # Configuration from environment
    bucket = get_artifact_bucket()
    keep_count = int(os.environ.get('KEEP_COUNT', '2'))
    dry_run = os.environ.get('DRY_RUN', '').lower() == 'true'

    print(f"Artifact Janitor starting...")
    print(f"  Bucket: {bucket}")
    print(f"  Keep count: {keep_count}")
    print(f"  Dry run: {dry_run}")

    # List all objects in the bucket
    s3 = boto3.client('s3')
    all_objects = []

    try:
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket):
            if 'Contents' in page:
                all_objects.extend(page['Contents'])
    except Exception as e:
        print(f"ERROR: Failed to list objects in {bucket}: {str(e)}")
        raise

    if not all_objects:
        print("No objects found in bucket. Nothing to do.")
        return {
            'statusCode': 200,
            'body': 'No artifacts to clean'
        }

    print(f"Found {len(all_objects)} total objects in bucket")

    # Group by (type, environment)
    groups = group_artifacts(all_objects)
    print(f"Grouped into {len(groups)} artifact groups")

    # Print summary of each group
    for (artifact_type, env), artifacts in groups.items():
        if artifact_type == 'unknown':
            print(f"  [UNKNOWN/{env}] {len(artifacts)} objects (unrecognized pattern)")
        else:
            newest_age = (datetime.now(timezone.utc) - artifacts[0]['LastModified']).days
            print(f"  [{artifact_type}/{env}] {len(artifacts)} objects (newest: {newest_age} days old)")

    # Delete old artifacts
    stats = delete_old_artifacts(bucket, groups, keep_count, dry_run)

    # Print summary
    print("\n--- Janitor Summary ---")
    print(f"Groups processed: {stats['groups_processed']}")
    print(f"Artifacts kept: {stats['artifacts_kept']}")
    print(f"Artifacts deleted: {stats['artifacts_deleted']}")
    print(f"Bytes deleted: {stats['bytes_deleted']:,} ({stats['bytes_deleted'] / (1024*1024):.2f} MB)")

    if stats['errors']:
        print(f"Errors: {len(stats['errors'])}")
        for err in stats['errors'][:5]:  # Show first 5 errors
            print(f"  - {err}")

    # Return structured result for CloudWatch/Step Functions
    result = {
        'statusCode': 200,
        'bucket': bucket,
        'dryRun': dry_run,
        'stats': {
            'groupsProcessed': stats['groups_processed'],
            'artifactsKept': stats['artifacts_kept'],
            'artifactsDeleted': stats['artifacts_deleted'],
            'bytesDeleted': stats['bytes_deleted'],
            'errorCount': len(stats['errors'])
        }
    }

    if stats['errors']:
        result['errors'] = stats['errors']

    print(f"\nResult: {result}")
    return result


if __name__ == '__main__':
    # For local testing
    lambda_handler({}, {})
