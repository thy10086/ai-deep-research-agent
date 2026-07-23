import asyncio
from dataclasses import dataclass
from pathlib import Path

import aiofiles
from pypdf import PdfReader


class DocumentParseError(Exception):
    pass


class EmptyDocumentError(DocumentParseError):
    pass


class UnsupportedDocumentError(DocumentParseError):
    pass


@dataclass(frozen=True)
class ParsedSection:
    content: str
    metadata: dict[str, object]


async def parse_document(
    path: Path,
    content_type: str,
) -> list[ParsedSection]:
    try:
        if content_type in {"text/plain", "text/markdown"}:
            sections = await _parse_text(path)
        elif content_type == "application/pdf":
            sections = await asyncio.to_thread(_parse_pdf, path)
        else:
            raise UnsupportedDocumentError(
                f"Unsupported content type: {content_type}"
            )
    except DocumentParseError:
        raise
    except Exception as error:
        raise DocumentParseError(f"Failed to parse {path.name}") from error

    sections = [
        section
        for section in sections
        if section.content.strip()
    ]

    if not sections:
        raise EmptyDocumentError(
            f"No extractable text found in {path.name}"
        )

    return sections


async def _parse_text(path: Path) -> list[ParsedSection]:
    async with aiofiles.open(path, encoding="utf-8") as document:
        content = await document.read()

    return [
        ParsedSection(
            content=content,
            metadata={"source": path.name},
        )
    ]


def _parse_pdf(path: Path) -> list[ParsedSection]:
    reader = PdfReader(path)

    return [
        ParsedSection(
            content=page.extract_text() or "",
            metadata={
                "source": path.name,
                "page": page_number,
            },
        )
        for page_number, page in enumerate(reader.pages, start=1)
    ]