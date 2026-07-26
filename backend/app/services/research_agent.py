from dataclasses import dataclass
from typing import TypedDict, cast

from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm import llm_service
from app.services.search import SearchHit, semantic_search


class ResearchState(TypedDict, total=False):
    question: str
    subquestions: list[str]
    evidence: list[SearchHit]
    report: str


@dataclass(frozen=True)
class ResearchResult:
    question: str
    subquestions: list[str]
    evidence: list[SearchHit]
    report: str


PLANNER_PROMPT = """
你是研究任务规划器。请把用户的复杂问题拆分为 2 到 4 个可独立检索的子问题。
返回 JSON 对象，格式必须为：
{"subquestions": ["子问题1", "子问题2"]}
不要返回其他字段或解释。
""".strip()

SYNTHESIZER_PROMPT = """
你是严谨的研究报告撰写助手。
只能使用给定证据，不得编造事实。
使用 [1]、[2] 形式标注引用，引用编号必须与证据编号一致。
报告需要包含简明结论、关键发现和仍无法确定的内容。
使用与用户问题相同的语言。
""".strip()


def _normalize_subquestions(
    payload: dict[str, object],
    original_question: str,
) -> list[str]:
    raw_subquestions = payload.get("subquestions")
    if not isinstance(raw_subquestions, list):
        return [original_question]

    normalized: list[str] = []
    for item in raw_subquestions:
        if not isinstance(item, str):
            continue

        question = item.strip()
        if len(question) >= 2 and question not in normalized:
            normalized.append(question)

    return normalized[:4] or [original_question]


async def run_deep_research(
    session: AsyncSession,
    question: str,
) -> ResearchResult:
    async def plan_node(state: ResearchState) -> ResearchState:
        payload = await llm_service.generate_json(
            system_prompt=PLANNER_PROMPT,
            user_prompt=state["question"],
        )
        return {
            "subquestions": _normalize_subquestions(
                payload,
                state["question"],
            )
        }

    async def retrieve_node(state: ResearchState) -> ResearchState:
        unique_evidence: dict[object, SearchHit] = {}

        for subquestion in state["subquestions"]:
            hits = await semantic_search(
                session=session,
                query=subquestion,
                limit=3,
            )
            for hit in hits:
                unique_evidence.setdefault(hit.chunk_id, hit)

        evidence = sorted(
            unique_evidence.values(),
            key=lambda hit: hit.score,
            reverse=True,
        )[:10]
        return {"evidence": evidence}

    async def synthesize_node(state: ResearchState) -> ResearchState:
        evidence = state["evidence"]
        if not evidence:
            return {
                "report": "无法从当前知识库中找到足够证据完成研究。"
            }

        evidence_context = "\n\n".join(
            f"[{index}] 文件：{hit.filename}\n{hit.content}"
            for index, hit in enumerate(evidence, start=1)
        )
        subquestion_context = "\n".join(
            f"- {subquestion}"
            for subquestion in state["subquestions"]
        )

        report = await llm_service.generate(
            system_prompt=SYNTHESIZER_PROMPT,
            user_prompt=(
                f"原始问题：\n{state['question']}\n\n"
                f"研究子问题：\n{subquestion_context}\n\n"
                f"证据：\n{evidence_context}\n\n"
                "请撰写最终研究报告。"
            ),
        )
        return {"report": report}

    workflow = StateGraph(ResearchState)
    workflow.add_node("plan", plan_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("synthesize", synthesize_node)
    workflow.add_edge(START, "plan")
    workflow.add_edge("plan", "retrieve")
    workflow.add_edge("retrieve", "synthesize")
    workflow.add_edge("synthesize", END)

    graph = workflow.compile()
    final_state = cast(
        ResearchState,
        await graph.ainvoke({"question": question}),
    )

    return ResearchResult(
        question=question,
        subquestions=final_state["subquestions"],
        evidence=final_state["evidence"],
        report=final_state["report"],
    )
