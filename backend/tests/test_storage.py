from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile

from app.services.storage import (
    EmptyFileError,
    FileTooLargeError,
    StoredUpload,
    persist_upload,
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


@pytest.mark.asyncio
async def test_persist_upload_keeps_local_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "checksum.txt"
    source.write_text("research", encoding="utf-8")
    stored_upload = StoredUpload(
        path=source,
        checksum="checksum",
        size=8,
    )
    monkeypatch.setattr(
        "app.services.storage.settings.storage_backend",
        "local",
    )

    uri = await persist_upload(stored_upload, suffix=".txt")

    assert uri == source.as_posix()
    assert source.is_file()


@pytest.mark.asyncio
async def test_persist_upload_moves_file_to_s3(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "checksum.txt"
    source.write_text("research", encoding="utf-8")
    stored_upload = StoredUpload(
        path=source,
        checksum="checksum",
        size=8,
    )
    uploaded_keys: list[str] = []

    async def fake_upload_file(
        self: object,
        local_path: Path,
        object_key: str,
    ) -> str:
        assert local_path == source
        uploaded_keys.append(object_key)
        return f"s3://research-documents/{object_key}"

    monkeypatch.setattr(
        "app.services.storage.settings.storage_backend",
        "s3",
    )
    monkeypatch.setattr(
        "app.services.storage.settings.s3_bucket_name",
        "research-documents",
    )
    monkeypatch.setattr(
        "app.services.s3_storage.S3ObjectStorage.upload_file",
        fake_upload_file,
    )

    uri = await persist_upload(stored_upload, suffix=".txt")

    assert uri == "s3://research-documents/documents/checksum.txt"
    assert uploaded_keys == ["documents/checksum.txt"]
    assert not source.exists()
