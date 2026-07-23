from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile

from app.services.storage import (
    EmptyFileError,
    FileTooLargeError,
    save_upload,
)


@pytest.mark.asyncio
async def test_save_upload_writes_content_and_checksum(tmp_path: Path) -> None:
    content = b"retrieval augmented generation"
    upload = UploadFile(
        filename="sample.txt",
        file=BytesIO(content),
    )

    result = await save_upload(
        file=upload,
        upload_dir=tmp_path,
        suffix=".txt",
        max_file_size=1024,
        chunk_size=8,
    )

    assert result.path.read_bytes() == content
    assert result.checksum == sha256(content).hexdigest()
    assert result.size == len(content)
    assert result.path.name == f"{result.checksum}.txt"


@pytest.mark.asyncio
async def test_save_upload_rejects_empty_file(tmp_path: Path) -> None:
    upload = UploadFile(
        filename="empty.txt",
        file=BytesIO(b""),
    )

    with pytest.raises(EmptyFileError):
        await save_upload(
            file=upload,
            upload_dir=tmp_path,
            suffix=".txt",
            max_file_size=1024,
            chunk_size=8,
        )

    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_save_upload_rejects_large_file(tmp_path: Path) -> None:
    upload = UploadFile(
        filename="large.txt",
        file=BytesIO(b"too large"),
    )

    with pytest.raises(FileTooLargeError):
        await save_upload(
            file=upload,
            upload_dir=tmp_path,
            suffix=".txt",
            max_file_size=4,
            chunk_size=2,
        )

    assert list(tmp_path.iterdir()) == []