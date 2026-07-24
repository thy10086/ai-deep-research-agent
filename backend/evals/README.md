# Retrieval Evaluation

This directory contains versioned datasets and reproducible offline
evaluation scripts for retrieval experiments.

## Dense Baseline

- Date: 2026-07-24
- Model: `bge-m3`
- Runtime: Ollama `0.32.3`
- Embedding dimension: 1024
- Distance metric: cosine similarity
- Corpus size: 8 documents
- Query count: 6
- Query language: Chinese
- Document language: English

Run the baseline:

```powershell
uv run --directory backend python -m evals.evaluate_dense

```

Results:

| Metric | Score |
| --- | ---: |
| Recall@1 | 0.6667 |
| Recall@3 | 1.0000 |
| MRR | 0.8056 |

## Observations

The relevant document appeared in the top three for every query. Two
queries did not rank the relevant document first:

- Candidate reranking
- Cross-lingual embedding retrieval

These cases will be retained as regression examples for evaluating
hybrid retrieval and reranking.

## Limitations

This is a pipeline validation dataset, not a representative benchmark.
The next versions should include:

- At least 100 queries
- Multiple relevant documents per query
- Hard negative passages
- Longer documents and chunk-level labels
- Chinese, English, and cross-lingual queries
- Latency and cost measurements