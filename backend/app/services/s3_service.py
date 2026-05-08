import os
import boto3
from botocore.config import Config

ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL", "http://localhost:9000")
ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "minioadmin")
SECRET_KEY = os.environ.get("S3_SECRET_KEY", "minioadmin")

BUCKET_UPLOADS = os.environ.get("S3_BUCKET_UPLOADS", "uploads")
BUCKET_OUTPUTS = os.environ.get("S3_BUCKET_OUTPUTS", "outputs")
BUCKET_CODEBASE = os.environ.get("S3_BUCKET_CODEBASE", "codebase")

print(f"DEBUG: S3_ENDPOINT_URL: {ENDPOINT_URL}")


def _client():
    return boto3.client(
        "s3",
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def upload_file(local_path: str, bucket: str, key: str) -> str:
    _client().upload_file(local_path, bucket, key)
    return key


def upload_bytes(data: bytes, bucket: str, key: str) -> str:
    _client().put_object(Bucket=bucket, Key=key, Body=data)
    return key


def download_file(bucket: str, key: str, dest_path: str) -> None:
    _client().download_file(bucket, key, dest_path)


def download_bytes(bucket: str, key: str) -> bytes:
    resp = _client().get_object(Bucket=bucket, Key=key)
    return resp["Body"].read()


def get_object(bucket: str, key: str):
    return _client().get_object(Bucket=bucket, Key=key)


def presigned_url(bucket: str, key: str, expires: int = 3600) -> str:
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires,
    )


def object_exists(bucket: str, key: str) -> bool:
    try:
        _client().head_object(Bucket=bucket, Key=key)
        return True
    except Exception:
        return False


def delete_object(bucket: str, key: str):
    _client().delete_object(Bucket=bucket, Key=key)
