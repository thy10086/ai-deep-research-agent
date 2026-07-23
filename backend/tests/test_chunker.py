import pytest

from app.services.chunker import chunk_sections
from app.services.parser import ParsedSection


def test_chunk_sections_preserves_metadata_and_boundaries() -> None:
    sections = [
        ParsedSection(
            content="First paragraph.\n\nSecond paragraph.",
            metadata={"source": "paper.pdf", "page": 3},
        )
    ]

    chunks = chunk_sections(
        sections,
        max_chars=20,
        overlap_chars=0,
    )

    assert [chunk.content for chunk in chunks] == [
        "First paragraph.",
        "Second paragraph.",
    ]
    assert chunks[0].metadata == {
        "source": "paper.pdf",
        "page": 3,
        "section_index": 0,
        "chunk_index": 0,
    }
    assert chunks[1].metadata["chunk_index"] == 1


def test_chunk_sections_adds_overlap() -> None:
    sections = [
        ParsedSection(
            content="abcdefghijklmnopqrstuvwxyz",
            metadata={"source": "letters.txt"},
        )
    ]

    chunks = chunk_sections(
        sections,
        max_chars=10,
        overlap_chars=3,
    )

    assert chunks[0].content == "abcdefghij"
    assert chunks[1].content == "hijklmnopq"
    assert chunks[0].content[-3:] == chunks[1].content[:3]
    assert all(len(chunk.content) <= 10 for chunk in chunks)


@pytest.mark.parametrize(
    ("max_chars", "overlap_chars"),
    [
        (0, 0),
        (10, -1),
        (10, 10),
        (10, 11),
    ],
)
def test_chunk_sections_rejects_invalid_parameters(
    max_chars: int,
    overlap_chars: int,
) -> None:
    with pytest.raises(ValueError):
        chunk_sections(
            [],
            max_chars=max_chars,
            overlap_chars=overlap_chars,
        )