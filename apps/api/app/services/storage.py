from __future__ import annotations

from functools import lru_cache
from typing import BinaryIO, Mapping

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import Settings, get_settings


class StorageError(RuntimeError):
    """Raised when an object storage operation fails."""


class StorageService:
    def __init__(self, settings: Settings) -> None:
        self.bucket = settings.s3_bucket
        self.presigned_url_expire_seconds = settings.s3_presigned_url_expire_seconds
        self.client: BaseClient = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            use_ssl=settings.s3_use_ssl,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    def check_connection(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as exc:
            raise StorageError(
                f"Unable to access object storage bucket '{self.bucket}'."
            ) from exc

    def upload_file(
        self,
        *,
        file_obj: BinaryIO,
        object_key: str,
        content_type: str | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> None:
        extra_args: dict[str, object] = {}
        if content_type:
            extra_args["ContentType"] = content_type
        if metadata:
            extra_args["Metadata"] = dict(metadata)

        try:
            self.client.upload_fileobj(
                file_obj,
                self.bucket,
                object_key,
                ExtraArgs=extra_args or None,
            )
        except ClientError as exc:
            raise StorageError(f"Unable to upload object '{object_key}'.") from exc

    def download_file(self, *, object_key: str, destination: BinaryIO) -> None:
        try:
            self.client.download_fileobj(self.bucket, object_key, destination)
        except ClientError as exc:
            raise StorageError(f"Unable to download object '{object_key}'.") from exc

    def delete_file(self, *, object_key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=object_key)
        except ClientError as exc:
            raise StorageError(f"Unable to delete object '{object_key}'.") from exc

    def file_exists(self, *, object_key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=object_key)
            return True
        except ClientError as exc:
            status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status_code == 404:
                return False
            raise StorageError(f"Unable to inspect object '{object_key}'.") from exc

    def get_metadata(self, *, object_key: str) -> dict[str, object]:
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=object_key)
        except ClientError as exc:
            raise StorageError(f"Unable to read metadata for '{object_key}'.") from exc

        return {
            "content_type": response.get("ContentType"),
            "content_length": response.get("ContentLength"),
            "etag": response.get("ETag", "").strip('"'),
            "last_modified": response.get("LastModified"),
            "metadata": response.get("Metadata", {}),
        }

    def generate_presigned_url(
        self,
        *,
        object_key: str,
        expires_in: int | None = None,
        download_filename: str | None = None,
    ) -> str:
        params: dict[str, str] = {
            "Bucket": self.bucket,
            "Key": object_key,
        }
        if download_filename:
            params["ResponseContentDisposition"] = (
                f'attachment; filename="{download_filename}"'
            )

        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=expires_in or self.presigned_url_expire_seconds,
            )
        except ClientError as exc:
            raise StorageError(
                f"Unable to generate a URL for object '{object_key}'."
            ) from exc


@lru_cache
def get_storage_service() -> StorageService:
    return StorageService(get_settings())
