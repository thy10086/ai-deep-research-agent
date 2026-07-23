from pathlib import Path

import pytest

from app.services.parser import (
    EmptyDocumentError,
    ParsedSection,
    UnsupportedDocumentError,
    parse_document,
)


@pytest.mark.asyncio
async def test_parse_text_document(tmp_path: Path) -> None:
    document_path = tmp_path / "research.txt"
    document_path.write_text(
        "Hybrid retrieval improves evidence recall.",
        encoding="utf-8",
    )

    sections = await parse_document(
        document_path,
        content_type="text/plain",
    )

    assert sections == [
        ParsedSection(
            content="Hybrid retrieval improves evidence recall.",
            metadata={"source": "research.txt"},
        )
    ]


@pytest.mark.asyncio
async def test_parse_empty_document(tmp_path: Path) -> None:
    document_path = tmp_path / "empty.txt"
    document_path.write_text("   \n", encoding="utf-8")

    with pytest.raises(EmptyDocumentError):
        await parse_document(
            document_path,
            content_type="text/plain",
        )


@pytest.mark.asyncio
async def test_parse_unsupported_document(tmp_path: Path) -> None:
    document_path = tmp_path / "image.png"

    with pytest.raises(UnsupportedDocumentError):
        await parse_document(
            document_path,
            content_type="image/png",
        )