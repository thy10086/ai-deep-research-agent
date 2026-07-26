from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import aioboto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings


class S3StorageError(Exception):
    pass


class InvalidS3URIError(S3StorageError):
    pass


@dataclass(frozen=True)
class S3ObjectStorage:
    bucket_name: str
    endpoint_url: str = ""
    region: str = "auto"
    access_key_id: str = ""
    secret_access_key: str = ""

    def _client_options(self) -> dict[str, str]:
        options = {"region_name": self.region}

        if self.endpoint_url:
            options["endpoint_url"] = self.endpoint_url
        if self.access_key_id:
            options["aws_access_key_id"] = self.access_key_id
        if self.secret_access_key:
            options["aws_secret_access_key"] = self.secret_access_key

        return options

    def _parse_uri(self, uri: str) -> str:
        parsed = urlparse(uri)
        key = parsed.path.lstrip("/")

        if (
            parsed.scheme != "s3"
            or parsed.netloc != self.bucket_name
            or not key
        ):
            raise InvalidS3URIError(f"Invalid S3 URI: {uri}")

        return key

    async def upload_file(
        self,
        local_path: Path,
        object_key: str,
    ) -> str:
        try:
            session = aioboto3.Session()
            async with session.client(
                "s3",
                **self._client_options(),
            ) as client:
                await client.upload_file(
                    str(local_path),
                    self.bucket_name,
                    object_key,
                )
        except (BotoCoreError, ClientError, OSError) as error:
            raise S3StorageError("Failed to upload file to S3.") from error

        return f"s3://{self.bucket_name}/{object_key}"

    async def download_file(
        self,
        uri: str,
        destination: Path,
    ) -> None:
        object_key = self._parse_uri(uri)

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            session = aioboto3.Session()
            async with session.client(
                "s3",
                **self._client_options(),
            ) as client:
                await client.download_file(
                    self.bucket_name,
                    object_key,
                    str(destination),
                )
        except (BotoCoreError, ClientError, OSError) as error:
            raise S3StorageError("Failed to download file from S3.") from error

    async def delete_file(self, uri: str) -> None:
        object_key = self._parse_uri(uri)

        try:
            session = aioboto3.Session()
            async with session.client(
                "s3",
                **self._client_options(),
            ) as client:
                await client.delete_object(
                    Bucket=self.bucket_name,
                    Key=object_key,
                )
        except (BotoCoreError, ClientError) as error:
            raise S3StorageError("Failed to delete file from S3.") from error


s3_storage = S3ObjectStorage(
    bucket_name=settings.s3_bucket_name,
    endpoint_url=settings.s3_endpoint_url,
    region=settings.s3_region,
    access_key_id=settings.s3_access_key_id,
    secret_access_key=settings.s3_secret_access_key,
)
