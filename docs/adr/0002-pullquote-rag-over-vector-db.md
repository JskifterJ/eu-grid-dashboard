# ADR 0002: Pull-quote RAG over vector database

**Status:** Accepted · 2026-04-20
**Deciders:** Johannes Skifter

---

## Context

The Analyst Note feature enriches the Gemini briefing with a relevant excerpt from the `gpu_industry` repository — a collection of ~6 HTML presentations covering GPU value chain, competitive landscape, inference economics, and market positioning.

We need a retrieval step that selects the most contextually relevant pull-quote to include in the Gemini prompt. The alternatives are:

1. **Embed all documents and query a vector database at runtime.**
2. **Pre-index pull-quotes at build time; select by rule at runtime.**

The corpus is deliberately small: ~6 HTML files, ~30 candidate pull-quotes, tagged by topic at indexing time (`scripts/index_strategy.py`). Topics map directly to CSS attributes: a country ranked high on renewable share triggers the `clean-premium` topic; a country with high cost sigma triggers `grid-volatility`; the inference workload mode triggers `inference-economics`.

---

## Decision

Use **rule-based pull-quote selection** over a pre-built flat JSON index (`data/strategy_quotes.json`).

The build-time script `scripts/index_strategy.py` parses the `gpu_industry` HTML files and emits one JSON record per pull-quote: `{text, source_file, topic_tags[], source_url}`. This file is committed to the repo and refreshed when `gpu_industry` changes.

At runtime, `app/briefing.py` scores each quote by counting tag overlaps with the current CSS context (high-renewable, low-cost, inference-mode, etc.) and selects the top match. No embeddings, no network call, no vector DB.

---

## Consequences

**Positive:**
- **Deterministic and inspectable.** The selection logic is a handful of lines of Python. A technical reviewer can read `briefing.py` and understand exactly why a given quote was chosen. This matters for a portfolio piece: "here's the RAG, and here's why it selected this quote" is a stronger signal than a black-box cosine similarity.
- **Zero additional infrastructure.** No Pinecone, no Chroma, no embedding API call on every briefing request.
- **Latency.** Tag matching is O(n) over ~30 quotes; effectively free compared to the Gemini call.
- **No embedding drift.** Vector similarity can select plausible-sounding but contextually wrong quotes when the embedding model's semantic space doesn't align with the domain. With 30 manually tagged quotes, curation beats recall.

**Negative / tradeoffs:**
- **Recall ceiling.** The index only surfaces what was tagged at build time. A quote not tagged with `inference-economics` will not be retrieved for an inference-mode query, even if it is relevant. This is acceptable — the corpus is small enough that a human review covers it.
- **Maintenance burden.** Adding new `gpu_industry` content requires re-running the indexing script. Acceptable given the expected cadence (quarterly updates to the strategy docs).
- Does not scale to a large, dynamic corpus. Replace with a vector DB if the corpus grows beyond ~200 documents or if retrieval quality becomes inadequate.

---

## Alternatives considered

| Option | Why rejected |
|---|---|
| **Pinecone / Chroma vector DB** | Adds infra dependency, embedding API cost, and latency for a 6-document corpus. Recall improvement over curated tagging is marginal — and the tagging is the more credible approach to demonstrate in a portfolio context. |
| **OpenAI / Gemini embeddings at query time** | Extra API call on every briefing request; non-deterministic (embedding model versions change). Not justified for this corpus size. |
| **Full document in every Gemini prompt** | Context window cost scales with corpus size; prompts become noisy. Selective retrieval keeps the prompt tight. |
| **No RAG at all** | The Analyst Note becomes generic. Including a domain-specific pull-quote from `gpu_industry` grounds the briefing in the strategic narrative and demonstrates the dashboard-analysis connection. |
