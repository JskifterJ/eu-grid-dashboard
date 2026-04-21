# Plan B — Centerpiece, Narrative Bridge, Rigour

**Goal:** Ship the interactive simulator (the artifact's centerpiece), a 48h forecast chart, the strategic backdrop cards that bridge to `gpu_industry`, a structured analyst briefing with pragmatic RAG, and the rigour layer (methodology.md + ADRs + README). After Plan B the dashboard is a completed portfolio piece.

**Architecture:** Most work is frontend — new sections below the map. Backend gains two small additions: `/api/eval` (forecast MAPE, mock where historical data unavailable) and `/api/briefing` (structured Gemini output with pull-quote RAG from `gpu_industry`). A one-time build script `scripts/index_strategy.py` parses gpu_industry HTML files into a flat JSON of tagged pull-quotes. No vector DB.

**Tech Stack:** Same. Adds Chart.js for forecast chart (already loaded), `beautifulsoup4` for the indexer script (new dep — stdlib fallback if deemed overkill).

## Tasks

1. **Simulator UI** — the centerpiece. Inputs (workload/country/MW/hours/region/carbon_price), output card (current + best-hour + hub comparison + CSS percentile badge), shareable permalink via URL state.
2. **Forecast chart** — 48h CO₂ + price line chart for selected country. Actual-vs-forecast shaded region.
3. **Strategic backdrop indexer** — `scripts/index_strategy.py` parses `~/code/gpu_industry` HTML files into `frontend/strategic_quotes.json` (title, pull-quote, href, image, tags).
4. **Strategic backdrop cards** — 4-6 cards below the map linking to gpu_industry with pull-quotes, including IEA 415→945 TWh framing and inference cost data from `learning_inference_compute_master_v10.html`.
5. **Structured AI briefing — backend** — Gemini structured JSON output. Pragmatic RAG: rule-based pull-quote selection from step 3's JSON. Pydantic-validated `StructuredBriefing`.
6. **Analyst note UI** — render the structured briefing cleanly with headline + 3 bullets + risk flag + sources.
7. **Historical context strip** — simple "this decade on the grid" visual. Uses mock or Our World in Data / EMBER public CSV fallback.
8. **Eval panel** — `/api/eval` endpoint + small MAPE visualization. Mock values where live data incomplete.
9. **README + methodology.md + ADRs** — rigour layer.
10. **Smoke + tag `plan-b-complete`**.

Each task commits independently. Portfolio hub edits at `jskifterj.github.io` are noted as follow-ups (repo not local).
