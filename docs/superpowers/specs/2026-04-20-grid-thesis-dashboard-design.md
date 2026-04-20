# EU Grid Dashboard → Thesis-Led Portfolio Artifact

**Date:** 2026-04-20
**Author:** Johannes Skifter (jskifter@icn.global) with Claude
**Status:** Design approved — ready for implementation plan

---

## 1. Purpose

Transform the existing EU Grid Dashboard from a passive status-reporting dashboard into an **opinionated, thesis-driven scroll experience** that works as a flagship portfolio piece for **technical sales / solutions-engineer, product management, and applied-AI-engineer roles**. Concurrently link it to the existing `gpu_industry` repository so the two form a single connected narrative about **grid decarbonization and AI compute siting in Europe**.

The finished artifact must demonstrate:
- Product thinking (a thesis, a user flow, a shareable simulator).
- Technical fluency (live data, structured APIs, honest forecasting with evaluation, pragmatic RAG).
- Domain credibility (correct bidding-zone handling, primary energy factors, IPCC/IEA citations, caveat transparency).
- Narrative and strategic depth (ties to a broader GPU/compute value-chain analysis already written in `gpu_industry`).

## 2. Thesis

> **Europe's grid is changing hour by hour. So is the right answer to *where AI should run.***

The artifact argues:
1. Europe's electricity mix decarbonizes unevenly — France nuclear-clean 24/7, Norway hydro, Poland coal-heavy, Germany wind-variable.
2. AI compute is a massive, relocatable, price-sensitive new load — precisely the kind that can chase clean electrons.
3. The optimal *where and when* for training shifts hourly. The dashboard proves it by scoring European countries live and letting the reader simulate a workload.

## 3. Out of scope (deliberately)

- Per-zone drill-downs inside a country (we aggregate multi-zone countries and footnote; we do not build a zone-level UI).
- Real-time carbon matching / 24/7 CFE accounting (interesting but too deep for scope).
- Inference workloads (scope is training-shaped long-running loads; inference economics are linked-to via `gpu_industry` but not modeled here).
- Offline mobile (responsive fine; no PWA).

## 4. Narrative page structure (scroll, not dashboard)

1. **Hero.** Thesis H1, live "right now" banner (cleanest country + dirtiest + representative 10 MW × 6 h run comparison). "Permalink to this moment" chip. Sources down-arrow.
2. **Live ranking strip.** All 20 covered countries as score cards, sortable by CSS / carbon / cost / renewable / stability. Weights-preset switcher: Green / Balanced / Cost / Custom.
3. **Interactive map.** CSS-colored choropleth. Hour-scrub slider covering last 24h + next 24h (forecast region visually distinct — dashed boundary, lighter fill). Lens toggle: *Consumer view* (CO₂ g/kWh) vs *AI-compute view* (CSS).
4. **Country deep-dive panel.** Enhanced side panel. Generation mix with **PEF toggle** (Electricity output vs Primary energy input). 48h CO₂ + price chart with forecast shaded. Cross-border flows. CSS breakdown showing why this country scores as it does.
5. **Compute-siting simulator.** Input: country, MW, hours. Output: current-hour emissions + cost, best-hour-next-24h emissions + cost, delta vs running in default AI hub, CSS percentile. Shareable permalink.
6. **Forecast accuracy panel.** MAPE of ENTSO market forecast vs naive seasonal baseline, last 7 days, per country.
7. **Historical context strip.** Time-slider morphing the current map backward using ENTSO historicals (or annual summaries where hourly doesn't go back that far). 2-3 sentences of commentary.
8. **Strategic backdrop.** Four cards linking out to `gpu_industry`: Value chain · Competitive landscape · Inference economics · Positioning trends. Each pulls a pull-quote + image from its source HTML.
9. **Analyst note.** Repositioned AI briefing — structured output + pragmatic RAG. Gemini fetches current CSS + forecast + a relevance-selected quote from `gpu_industry`; emits `{headline, three_bullets, risk_flag, as_of, sources}`; rendered deterministically with a "How this briefing is generated" link.
10. **Methodology & sources.** Weights, PEFs, emission factors (IPCC 2014 citation), forecast approach, eval metrics, bidding-zone caveats explicitly acknowledged.
11. **Footer.** Clean credits, link back to `jskifterj.github.io`, other projects.

## 5. Compute Siting Score (CSS)

Per country, per hour, 0–100:

| Dimension | Source | Better when |
|---|---|---|
| Carbon intensity (g CO₂/kWh) | ENTSO-E generation × IPCC emission factors | lower |
| Cost (€/MWh) | ENTSO-E day-ahead auction | lower |
| Renewable share (%) | ENTSO-E generation | higher |
| Price stability (24h-rolling σ, €/MWh, over published + forecasted prices) | ENTSO-E day-ahead | lower |

**Normalization:** min-max across the 20 covered countries per hour, mapped 0–100, flipped where lower is better, summed with weights.

**Default weights:** 40% carbon, 30% cost, 20% renewable, 10% stability. Rationale: a carbon-conscious trainer who still cares about cost. Presets `Green` (60/15/20/5), `Balanced` (current defaults), `Cost` (10/60/15/15), `Custom` (user sliders with the constraint `sum = 100`).

**Emission factors:** IPCC AR5 2014 median lifecycle values, already in `app/entso.py`. Will be moved to a dedicated module and cited in UI tooltips.

**Primary Energy Factors (PEF):** IEA physical-content convention.
- Hard coal 2.7, lignite 3.0, gas CCGT 2.0, gas OC 2.5, oil 2.6, peat 2.9
- Nuclear 3.0
- Biomass 1.2, waste 1.1
- Wind, solar, hydro, geothermal: 1.0

PEF is applied **only** to the generation-mix visualization via an explicit UI toggle ("Electricity output" default vs "Primary energy input"). CSS itself continues to score on electricity-delivered basis — that is what compute buys. Renewable-share dimension inside CSS uses electricity-MWh (not primary-MWh) to stay consistent with the other per-kWh-delivered dimensions; the PEF-adjusted renewable share is a visualization-only artifact.

## 6. Forecasting

**Deliberately un-fancy and honest.** No ML black-box. Two legitimate published 24h-ahead sources:

1. **Price forecast:** ENTSO-E day-ahead auction publishes every hour of tomorrow — this *is* the market's forecast. Used directly.
2. **CO₂ forecast:** ENTSO-E day-ahead *generation-forecast-by-source* per bidding zone × the same IPCC factors → forecasted g CO₂/kWh per hour.
3. **Naive seasonal baseline:** same-hour-same-weekday mean over last 4 weeks. Used as the eval benchmark, not as production forecast.

**Eval metric:** MAPE over the last 7 full days, per country, for both (a) market forecast vs realized and (b) naive seasonal vs realized. Surfaced on the Forecast accuracy panel. Explicitly the "applied-AI-engineer rigor" signal — show-your-work before claiming predictive power.

## 7. Compute-siting simulator

**Inputs:** country, MW, hours, start-hour (defaults to now).
**Outputs:**
- Current-hour emissions (tCO₂) = MW × h × g/kWh / 1000.
- Current-hour cost (€) = MW × h × €/MWh.
- Best-hour-next-24h equivalents, using the forecast.
- Delta vs "same workload in default AI hub" (Germany and Ireland are selectable comparison baselines; Germany default).
- CSS percentile ranking at chosen hour.
- Shareable permalink encoding all inputs + the exact as-of timestamp for reproducibility.

## 8. Backend architecture

### New endpoints (all additive; existing `/api/generation|prices|flows|overview|summary` retained)

| Endpoint | Purpose |
|---|---|
| `GET /api/forecast?country=XX` | 24h CO₂ g/kWh + €/MWh per hour |
| `GET /api/css?country=XX&weights=…&at=…` | CSS for one country, one hour |
| `GET /api/ranking?weights=…&at=…` | All 20 countries scored + sorted |
| `GET /api/simulate?country=XX&mw=10&hours=6&start=…` | Simulator output |
| `GET /api/historical?country=XX&start=…&end=…&agg=daily` | Historicals |
| `GET /api/eval?country=XX` | Forecast MAPE last 7 days |
| `POST /api/briefing` | Structured analyst note (RAG) |

### New internal modules

- `app/scoring.py` — pure CSS computation (no I/O, fully unit-tested): normalization, weight application, percentile.
- `app/forecast.py` — `market_forecast(country)`, `seasonal_baseline(country)`, `mape(actual, predicted)`.
- `app/simulator.py` — pure arithmetic over forecast × scoring.
- `app/historical.py` — ENTSO-E historical wrapper with persistent on-disk SQLite cache (historicals are immutable).
- `app/primary_energy.py` — `PRIMARY_ENERGY_FACTORS` table + `apply_pef(sources)` helper.
- `app/briefing.py` — replaces `app/ai.py`. Builds structured prompt with CSS + forecast + top-3 ranking + pre-indexed `gpu_industry` pull-quote. Calls Gemini with `response_mime_type=application/json`. Parses into pydantic `StructuredBriefing`.
- `scripts/index_strategy.py` — build-time script parsing `gpu_industry` HTML files; emits flat JSON of pull-quote snippets keyed by topic tags. Committed to repo; refreshed when `gpu_industry` changes.

### Bidding-zone aggregation

`AREA_CODES` becomes `dict[str, list[str]]`. For Norway: `["NO_1","NO_2","NO_3","NO_4","NO_5"]`, etc. ENTSO queries loop the zones, aggregate generation (GW summed) and weight-average prices by generation volume. Countries where aggregation is unclean (DE_LU spans DE and LU) are footnoted explicitly in the methodology and in tooltips.

### Data model additions (pydantic)

`ForecastPoint`, `ForecastSeries`, `CSSBreakdown`, `RankingEntry`, `SimulationResult`, `EvalResult`, `StructuredBriefing`.

### Caching

Extends existing `Cache`:
- Current-hour data: 15 min (unchanged).
- Forecast, CSS, ranking: 15 min.
- Historicals: 24 h, persistent SQLite.
- Briefing: 1 h.
- Eval: 6 h.

A lightweight `/api/refresh` endpoint pre-warms forecast + ranking + briefing on a 15-minute external cron (Render cron or GitHub Actions workflow hitting the URL).

## 9. Frontend

### Aesthetic: Editorial with premium interaction polish

- **Type:** Charter / Iowan Old Style serif for headlines (system-available on macOS/iOS, web-fallback Georgia). Inter for body and UI.
- **Palette:** warm off-white `#faf8f3`, deep graphite `#1a1a1a`, muted amber accent `#9a6a2f`, semantic colors retained for data (green/red for deltas).
- **Dark mode:** retained; adapted to the editorial palette — paper-dark (`#1a1815`) not GitHub-dark.
- **Motion:** Framer-Motion-quality transitions (CSS + lightweight JS only — no framework switch). Hour-scrub animates through map states smoothly. Hover micro-interactions on ranking cards. No decorative gimmicks.

### JS architecture

Kept vanilla + D3/Chart.js (already deployed on Render). Refactored into small modules per section:

- `frontend/state.js` — single source of truth (country, hour, weights, lens, view).
- `frontend/api.js` — thin fetch layer, already exists; extended for new endpoints.
- `frontend/hero.js`, `ranking.js`, `map.js` (existing, upgraded), `simulator.js`, `forecast-chart.js`, `historical.js`, `briefing.js`, `strategic-cards.js` — one module per scroll section.

No build step. Keeps deployment simple; Render continues to serve static frontend + FastAPI.

### Shareable permalinks

URL query encodes `?country=FR&at=2026-04-20T14:00Z&weights=40-30-20-10&mw=10&hours=6`. State-hydration on load. Enables deep-linking from `gpu_industry` and from blog posts.

## 10. Portfolio hub + gpu_industry integration

### `jskifterj.github.io`

- New "Current thesis" section above Projects — two sentences framing the AI+energy story; two links: live dashboard + gpu_industry overview.
- Projects reordered with EU Grid first; copy rewritten to foreground the thesis, not the stack.
- `gpu_industry` added as a linked project card.

### `gpu_industry`

- `index.html` hero rewrite: mirrors dashboard thesis; CTA "see it live →".
- Standardize nav across pres1/pres2/pres3/strategy_* so the collection feels unified.
- Each of the four files pulled by the dashboard's Strategic Backdrop gets a checked-in "card metadata" block (title, pull-quote, image) so the dashboard's build-time index is clean.

### Dashboard → gpu_industry cross-links

Strategic Backdrop section pulls one pull-quote + image each from:
- `strategy_value_chain_master.html`
- `strategy_competitor_intelligence.html`
- `strategy_inference_economics.html`
- `pres3_gpu-trends-positioning-deck.html`

## 11. Rigour / show-your-work layer

- **`README.md` rewrite:** two-sentence thesis, architecture diagram (mermaid), data sources, run instructions, deploy notes.
- **`docs/methodology.md`:** CSS formula, weights rationale, emission factors (IPCC AR5 citation), PEFs (IEA physical-content citation), forecast approach, eval, limitations — bidding-zone caveats, emission-factor vintage, carbon accounting boundaries.
- **`docs/adr/0001-sqlite-for-historicals.md`** — why not Postgres.
- **`docs/adr/0002-pullquote-rag-over-vector-db.md`** — scope-matched retrieval.
- **`docs/adr/0003-seasonal-baseline-as-forecast-eval.md`** — honest bar for claims of predictive power.
- **`docs/adr/0004-scroll-essay-over-dashboard-grid.md`** — form follows thesis.
- **Tests:** `test_scoring.py` (normalization edge cases, weights-sum-to-100 invariant), `test_forecast.py` (MAPE correctness, seasonal baseline determinism), `test_simulator.py` (emissions arithmetic, percentile), `test_briefing.py` (schema + happy-path RAG selection).

## 12. Build sequence

Each step is independently demonstrable and leaves the site working:

1. **Foundations** — backend refactor. `scoring.py`, `forecast.py`, `simulator.py`, `historical.py`, `primary_energy.py`, new endpoints with tests. No UI change.
2. **Visual reset** — Editorial aesthetic migration. Same features, new typography/layout/color.
3. **Thesis hero + live ranking strip** with weights presets.
4. **Interactive map upgrade** — hour-scrub, forecast region styling, AI-compute lens, multi-zone aggregation.
5. **Compute-siting simulator** — the centerpiece.
6. **Forecast + eval panel.**
7. **Historical context strip + Strategic backdrop** (pull-quote cards).
8. **Structured analyst-note briefing** with pragmatic RAG over `gpu_industry`.
9. **Portfolio hub + gpu_industry light edits** — cross-links, thesis section.
10. **Rigour layer** — README, methodology.md, 4 ADRs, test expansion, domain-credibility fixes.

## 13. Risks & mitigations

| Risk | Mitigation |
|---|---|
| ENTSO day-ahead generation-forecast is not published for all 20 covered countries | Detect per-country; fall back to seasonal baseline and mark the forecast panel accordingly. |
| Historicals beyond ENTSO's window (~5 years) break the "decade ago" slider | Hybrid: ENTSO for recent, public annual summary CSVs (EEA / Our World in Data) for older. Footnote the data source change. |
| RAG pulls a pull-quote irrelevant to the live situation | Pull-quotes are tagged by topic at indexing time; relevance selection is rule-based on CSS attributes (high-renewable → "clean premium" topic). Deterministic and inspectable. |
| Design drift toward "pretty dashboard" and away from thesis | Build-sequence step 3 (hero + ranking) must ship before any chart polish. Thesis above the fold is non-negotiable. |
| Credibility damaged by bidding-zone sloppiness in current code | Step 4 fixes multi-zone aggregation and adds footnotes; do not ship any new visuals referencing single-zone country data. |

## 14. Success criteria

- A non-technical PM/SE reader reaches the simulator and produces a shareable permalink within 90 seconds.
- A technical reviewer finds the methodology page convincing on emission factors, PEFs, forecast eval, and bidding zones.
- The `gpu_industry` ↔ dashboard cross-links are bidirectional, feel deliberate, and are one click apart.
- The `jskifterj.github.io` front page makes the thesis clear within the first viewport without a click.
