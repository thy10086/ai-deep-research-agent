from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm import llm_service
from app.services.search import SearchHit, semantic_search


@dataclass(frozen=True)
class RAGResult:
    answer: str
    sources: list[SearchHit]


SYSTEM_PROMPT = """
你是一个严谨的研究助手。
你只能根据提供的参考资料回答问题，不得编造资料中不存在的信息。
回答时使用 [1]、[2] 这样的编号标注信息来源。
如果参考资料不足以回答，请明确说明无法从现有资料中确定。
请使用与用户问题相同的语言回答。
""".strip()


async def answer_question(
    session: AsyncSession,
    question: str,
    limit: int = 5,
) -> RAGResult:
    sources = await semantic_search(
        session=session,
        query=question,
        limit=limit,
    )

    if not sources:
        return RAGResult(
            answer="无法从现有资料中找到相关信息。",
            sources=[],
        )

    context_parts = [
        (
            f"[{index}] 文件：{source.filename}\n"
            f"{source.content}"
        )
        for index, source in enumerate(sources, start=1)
    ]
    context = "\n\n".join(context_parts)

    user_prompt = (
        f"用户问题：\n{question}\n\n"
        f"参考资料：\n{context}\n\n"
        "请根据参考资料回答，并标注引用编号。"
    )

    answer = await llm_service.generate(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    return RAGResult(
        answer=answer,
        sources=sources,
    )