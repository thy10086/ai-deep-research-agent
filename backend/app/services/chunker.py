from dataclasses import dataclass

from app.services.parser import ParsedSection


@dataclass(frozen=True)
class TextChunk:
    content: str
    metadata: dict[str, object]


def chunk_sections(
    sections: list[ParsedSection],
    max_chars: int = 1000,
    overlap_chars: int = 150,
) -> list[TextChunk]:
    if max_chars <= 0:
        raise ValueError("max_chars must be greater than zero")

    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError(
            "overlap_chars must be between zero and max_chars"
        )

    chunks: list[TextChunk] = []

    for section_index, section in enumerate(sections):
        for content in _split_text(
            section.content,
            max_chars=max_chars,
            overlap_chars=overlap_chars,
        ):
            chunks.append(
                TextChunk(
                    content=content,
                    metadata={
                        **section.metadata,
                        "section_index": section_index,
                        "chunk_index": len(chunks),
                    },
                )
            )

    return chunks


def _split_text(
    text: str,
    max_chars: int,
    overlap_chars: int,
) -> list[str]:
    text = text.strip()

    if not text:
        return []

    chunks: list[str] = []
    start = 0

    while start < len(text):
        target_end = min(start + max_chars, len(text))
        end = _find_boundary(text, start, target_end, max_chars)
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        next_start = max(end - overlap_chars, start + 1)
        start = next_start

    return chunks


def _find_boundary(
    text: str,
    start: int,
    target_end: int,
    max_chars: int,
) -> int:
    if target_end >= len(text):
        return len(text)

    minimum_end = start + int(max_chars * 0.6)

    for separator in ("\n\n", "\n", ". ", " "):
        boundary = text.rfind(separator, minimum_end, target_end)

        if boundary != -1:
            return boundary + len(separator)

    return target_end