import asyncio
import json
import math
from pathlib import Path

from app.services.embeddings import embedding_service


DATASET_PATH = Path(__file__).with_name("retrieval_dataset.json")


def cosine_similarity(
    left: list[float],
    right: list[float],
) -> float:
    dot_product = sum(
        left_value * right_value
        for left_value, right_value in zip(left, right, strict=True)
    )
    left_norm = math.sqrt(
        sum(value * value for value in left)
    )
    right_norm = math.sqrt(
        sum(value * value for value in right)
    )

    if left_norm == 0 or right_norm == 0:
        return 0.0

    return dot_product / (left_norm * right_norm)


async def evaluate() -> None:
    dataset = json.loads(
        DATASET_PATH.read_text(encoding="utf-8")
    )
    documents = dataset["documents"]
    queries = dataset["queries"]

    document_embeddings = await embedding_service.embed_texts(
        [document["content"] for document in documents]
    )
    query_embeddings = await embedding_service.embed_texts(
        [query["query"] for query in queries]
    )

    recall_at_1 = 0.0
    recall_at_3 = 0.0
    reciprocal_rank_sum = 0.0

    for query, query_embedding in zip(
        queries,
        query_embeddings,
        strict=True,
    ):
        scored_documents = sorted(
            [
                (
                    document["id"],
                    cosine_similarity(
                        query_embedding,
                        document_embedding,
                    ),
                )
                for document, document_embedding in zip(
                    documents,
                    document_embeddings,
                    strict=True,
                )
            ],
            key=lambda item: item[1],
            reverse=True,
        )

        ranked_ids = [
            document_id
            for document_id, _ in scored_documents
        ]
        relevant_ids = set(query["relevant_ids"])

        recall_at_1 += (
            len(relevant_ids.intersection(ranked_ids[:1]))
            / len(relevant_ids)
        )
        recall_at_3 += (
            len(relevant_ids.intersection(ranked_ids[:3]))
            / len(relevant_ids)
        )

        first_relevant_rank = next(
            (
                rank
                for rank, document_id in enumerate(
                    ranked_ids,
                    start=1,
                )
                if document_id in relevant_ids
            ),
            None,
        )
        if first_relevant_rank is not None:
            reciprocal_rank_sum += 1 / first_relevant_rank

        print(f"\nQuery: {query['query']}")
        print(f"Expected: {sorted(relevant_ids)}")
        for rank, (document_id, score) in enumerate(
            scored_documents[:3],
            start=1,
        ):
            print(
                f"  {rank}. {document_id}: {score:.4f}"
            )

    query_count = len(queries)

    print("\nDense Retrieval Metrics")
    print(f"Recall@1: {recall_at_1 / query_count:.4f}")
    print(f"Recall@3: {recall_at_3 / query_count:.4f}")
    print(f"MRR:      {reciprocal_rank_sum / query_count:.4f}")


if __name__ == "__main__":
    asyncio.run(evaluate())