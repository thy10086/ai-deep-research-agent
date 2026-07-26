import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse
from uuid import uuid4

import aiofiles
from fastapi import UploadFile

from app.core.config import settings
from app.services.s3_storage import s3_storage


class EmptyFileError(Exception):
    pass


class FileTooLargeError(Exception):
    pass


class StorageConfigurationError(Exception):
    pass


@dataclass(frozen=True)
class StoredUpload:
    path: Path
    checksum: str
    size: int


async def save_upload(
    file: UploadFile,
    upload_dir: Path,
    suffix: str,
    max_file_size: int,
    chunk_size: int,
) -> StoredUpload:
    await asyncio.to_thread(upload_dir.mkdir, parents=True, exist_ok=True)

    temporary_path = upload_dir / f".{uuid4().hex}.tmp"
    digest = sha256()
    file_size = 0

    try:
        async with aiofiles.open(temporary_path, "wb") as output:
            while chunk := await file.read(chunk_size):
                file_size += len(chunk)

                if file_size > max_file_size:
                    raise FileTooLargeError

                digest.update(chunk)
                await output.write(chunk)

        if file_size == 0:
            raise EmptyFileError

        checksum = digest.hexdigest()
        destination = upload_dir / f"{checksum}{suffix}"

        await asyncio.to_thread(temporary_path.replace, destination)

        return StoredUpload(
            path=destination,
            checksum=checksum,
            size=file_size,
        )
    except Exception:
        if await asyncio.to_thread(temporary_path.exists):
            await asyncio.to_thread(temporary_path.unlink)
        raise


async def persist_upload(
    stored_upload: StoredUpload,
    suffix: str,
) -> str:
    if settings.storage_backend == "local":
        return stored_upload.path.as_posix()

    if settings.storage_backend != "s3":
        raise StorageConfigurationError(
            f"Unsupported storage backend: {settings.storage_backend}"
        )

    if not settings.s3_bucket_name:
        raise StorageConfigurationError(
            "S3_BUCKET_NAME is required for the S3 storage backend."
        )

    object_key = f"documents/{stored_upload.checksum}{suffix}"
    uri = await s3_storage.upload_file(
        local_path=stored_upload.path,
        object_key=object_key,
    )
    await asyncio.to_thread(stored_upload.path.unlink, missing_ok=True)
    return uri


@asynccontextmanager
async def materialize_source(uri: str) -> AsyncIterator[Path]:
    if not uri.startswith("s3://"):
        yield Path(uri)
        return

    suffix = Path(urlparse(uri).path).suffix
    with TemporaryDirectory(prefix="research-agent-") as temporary_dir:
        destination = Path(temporary_dir) / f"source{suffix}"
        await s3_storage.download_file(uri, destination)
        yield destination


async def delete_source(uri: str) -> None:
    if uri.startswith("s3://"):
        await s3_storage.delete_file(uri)
        return

    await asyncio.to_thread(Path(uri).unlink, missing_ok=True)
