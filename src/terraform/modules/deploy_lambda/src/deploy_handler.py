"""Lambda that updates the application Lambda code from an S3 object-created event."""

from __future__ import annotations

import json
import os
from urllib.parse import unquote_plus

import boto3

lambda_client = boto3.client("lambda")
TARGET_FUNCTION_NAME = os.environ["TARGET_LAMBDA_FUNCTION_NAME"]


def lambda_handler(event, context):
    records = event.get("Records", [])
    if not records:
        raise ValueError("No S3 records found in event")

    record = records[0]
    bucket = record["s3"]["bucket"]["name"]
    key = unquote_plus(record["s3"]["object"]["key"])
    version_id = record["s3"]["object"].get("versionId")

    params = {
        "FunctionName": TARGET_FUNCTION_NAME,
        "S3Bucket": bucket,
        "S3Key": key,
        "Publish": True,
    }
    if version_id:
        params["S3ObjectVersion"] = version_id

    response = lambda_client.update_function_code(**params)
    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "targetFunction": TARGET_FUNCTION_NAME,
                "sourceBucket": bucket,
                "sourceKey": key,
                "sourceVersion": version_id,
                "updatedVersion": response.get("Version"),
            }
        ),
    }
