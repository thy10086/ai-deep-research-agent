from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.research_agent import run_deep_research
from app.services.search import SearchHit


@pytest.mark.asyncio
async def test_research_agent_runs_all_nodes(
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
    searched_queries: list[str] = []

    async def fake_generate_json(
        self: object,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, object]:
        return {
            "subquestions": [
                "如何进行关键词检索？",
                "如何进行向量检索？",
            ]
        }

    async def fake_search(
        session: AsyncSession,
        query: str,
        limit: int,
    ) -> list[SearchHit]:
        searched_queries.append(query)
        return [source]

    async def fake_generate(
        self: object,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
    ) -> str:
        assert "[1]" in user_prompt
        assert source.content in user_prompt
        return "混合检索结合两类检索方式。[1]"

    monkeypatch.setattr(
        "app.services.llm.OllamaLLMService.generate_json",
        fake_generate_json,
    )
    monkeypatch.setattr(
        "app.services.research_agent.semantic_search",
        fake_search,
    )
    monkeypatch.setattr(
        "app.services.llm.OllamaLLMService.generate",
        fake_generate,
    )

    result = await run_deep_research(
        session=None,  # type: ignore[arg-type]
        question="如何设计混合检索系统？",
    )

    assert result.subquestions == [
        "如何进行关键词检索？",
        "如何进行向量检索？",
    ]
    assert searched_queries == result.subquestions
    assert result.evidence == [source]
    assert result.report == "混合检索结合两类检索方式。[1]"


@pytest.mark.asyncio
async def test_research_agent_handles_no_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_generate_json(
        self: object,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, object]:
        return {"subquestions": ["不存在的资料是什么？"]}

    async def fake_search(
        session: AsyncSession,
        query: str,
        limit: int,
    ) -> list[SearchHit]:
        return []

    monkeypatch.setattr(
        "app.services.llm.OllamaLLMService.generate_json",
        fake_generate_json,
    )
    monkeypatch.setattr(
        "app.services.research_agent.semantic_search",
        fake_search,
    )

    result = await run_deep_research(
        session=None,  # type: ignore[arg-type]
        question="不存在的资料是什么？",
    )

    assert result.evidence == []
    assert result.report == "无法从当前知识库中找到足够证据完成研究。"