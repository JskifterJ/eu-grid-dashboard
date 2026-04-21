# Plan C — Decision Support: Time-of-Day, Deferred Workloads, Full LCA

**Goal:** Turn the dashboard from "where should I run compute right now?" into **"when and how should I run compute to minimize impact?"**  Three meaningful additions:

1. **Time-of-day guidance** — the simulator learns to recommend *when* to start a workload. Shows a 24h CO₂/cost ribbon for the selected country, highlights the optimal window, quantifies the savings from deferring (e.g. "start at 02:00 instead of 14:00 — save 32% CO₂, €X cost").
2. **Deferred batch concept** — a live illustration of the product idea that inference providers should offer **discounted off-peak tiers** for agent-batchable workloads. Interactive mini-widget: "batch 1M tokens of agent work overnight in DE → save X kg CO₂ vs on-demand daytime serving."
3. **Full LCA calculator** — expand the simulator from operational-only emissions to a proper lifecycle view: **operational grid CO₂ × PUE + embodied hardware (amortized) + embodied datacenter (amortized)**. Toggle in the simulator switches between Operational (today's default) and Full LCA.

**Architecture:** Two new pure-function modules (`app/lca.py`, `app/time_of_day.py`). Two new endpoints. Three new UI sections. LCA constants are defensible — IPCC + manufacturer ESG + academic estimates, all cited. This is the portfolio's "I can reason about real-world AI infrastructure economics, not just electricity prices" moment.

**Tech Stack:** Unchanged. Chart.js for the time-of-day ribbon.

## Tasks

1. **LCA backend** — `app/lca.py` with constants (GPU embodied CO₂, datacenter embodied, default PUE), `LCABreakdown` pydantic model, `lca_breakdown()` pure function, full test suite.
2. **Time-of-day backend** — `app/time_of_day.py` that operates on `ForecastSeries` + a workload duration; returns the best contiguous window, worst window, and savings delta.
3. **New endpoints** — `GET /api/time-of-day?country=X&hours=6&workload=training` and `GET /api/lca?country=X&mw=10&hours=6&hardware=H100&pue=1.2`. Extend `/api/simulate` to optionally include the LCA breakdown.
4. **Time-of-day visualization** — 24h CO₂ ribbon below the simulator. Colored by intensity. Green outline marks the optimal start window for your duration. Callout: best vs worst deltas.
5. **Deferred batch card** — section explaining the off-peak tier concept with a live mini-calculator: input M tokens, show savings if batched overnight.
6. **LCA toggle in simulator** — toggle between Operational and Full LCA. Display a stacked breakdown (operational + embodied hardware + embodied datacenter + cooling overhead).
7. **Methodology panel updates** — add *Time-of-day optimization* and *Life-cycle assessment* subsections with formulas, citations, and caveats.
8. **gpu_industry cross-links** — add "live dashboard →" CTAs into key gpu_industry HTML files (pres3, inference-compute-deck, value chain, inference economics).
9. **README + methodology.md update** — reflect Plan C additions.
10. **Smoke + tag `plan-c-complete`**.

Portfolio landing edits (`jskifterj.github.io`) still deferred — repo not locally cloned.
