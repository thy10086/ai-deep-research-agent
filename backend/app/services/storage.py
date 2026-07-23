import asyncio
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import UploadFile


class EmptyFileError(Exception):
    pass


class FileTooLargeError(Exception):
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