from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.rag import RAGRequest
from app.services.rag import answer_question
from app.services.search import SearchHit


def test_rag_request_normalizes_question() -> None:
    request = RAGRequest(
        question="  什么是混合检索？  ",
    )

    assert request.question == "什么是混合检索？"
    assert request.limit == 5


@pytest.mark.parametrize(
    "question",
    [
        "  ",
        "a",
    ],
)
def test_rag_request_rejects_short_question(
    question: str,
) -> None:
    with pytest.raises(ValidationError):
        RAGRequest(question=question)


@pytest.mark.asyncio
async def test_answer_question_uses_retrieved_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = SearchHit(
        chunk_id=uuid4(),
        document_id=uuid4(),
        filename="retrieval.txt",
        content="Hybrid retrieval combines dense and keyword search.",
        token_count=8,
        score=0.91,
        metadata={},
    )

    async def fake_search(
        session: AsyncSession,
        query: str,
        limit: int,
    ) -> list[SearchHit]:
        return [source]

    async def fake_generate(
        self: object,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        assert "Hybrid retrieval" in user_prompt
        assert "[1]" in user_prompt
        return "混合检索结合两类搜索方法。[1]"

    monkeypatch.setattr(
        "app.services.rag.semantic_search",
        fake_search,
    )
    monkeypatch.setattr(
        "app.services.llm.OllamaLLMService.generate",
        fake_generate,
    )

    result = await answer_question(
        session=None,  # type: ignore[arg-type]
        question="什么是混合检索？",
    )

    assert result.answer == "混合检索结合两类搜索方法。[1]"
    assert result.sources == [source]


@pytest.mark.asyncio
async def test_answer_question_handles_no_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_search(
        session: AsyncSession,
        query: str,
        limit: int,
    ) -> list[SearchHit]:
        return []

    monkeypatch.setattr(
        "app.services.rag.semantic_search",
        fake_search,
    )

    result = await answer_question(
        session=None,  # type: ignore[arg-type]
        question="不存在的信息",
    )

    assert result.answer == "无法从现有资料中找到相关信息。"
    assert result.sources == []