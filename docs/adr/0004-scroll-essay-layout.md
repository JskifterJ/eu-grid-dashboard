# ADR 0004: Scroll-essay layout over dashboard grid

**Status:** Accepted · 2026-04-20
**Deciders:** Johannes Skifter

---

## Context

The dashboard presents a thesis: *Europe's grid decarbonizes unevenly, and AI compute should chase clean electrons.* The artifact must work as both a live tool and a portfolio piece. Two layout archetypes were available:

1. **Dashboard grid** — a configurable panel layout where the user assembles the story themselves. Standard for operations centers, BI tools, and monitoring products. Treats the audience as an analyst.
2. **Scroll essay** — a linear, opinionated reading experience. The author determines the order. Sections build on each other. Treats the audience as a reader who needs to be convinced.

---

## Decision

Use the **scroll-essay layout**.

The page is structured as a deliberate narrative sequence:

1. Hero with thesis statement and live "right now" snapshot.
2. Live ranking strip — evidence that the thesis is real and current.
3. Interactive map — geographic intuition.
4. Country deep-dive — analytical credibility.
5. Compute-siting simulator — user agency; the thesis becomes actionable.
6. Forecast + eval — methodological honesty.
7. Historical context — temporal depth.
8. Strategic backdrop — link to the broader `gpu_industry` analysis.
9. Analyst note — AI layer, grounded in live data.
10. Methodology & sources — show your work.

The reader cannot reorder this sequence. The simulator only appears after the ranking and map have established *why* siting matters. The methodology section only appears after the reader has engaged with the thesis — not as a disclaimer buried at the top.

---

## Consequences

**Positive:**
- **Enforces reading order.** A hiring manager or technical evaluator will see the thesis before the data, and the data before the methodology. The argument is pre-structured; the reader doesn't have to assemble it.
- **Signals editorial intent.** A scroll essay says "I have a point of view." A grid dashboard says "here are tools." For a portfolio piece whose explicit goal is to demonstrate product thinking, the former is the stronger signal.
- **Reduces decision fatigue.** The user is not asked to choose which panel to open first. The simulator is the centerpiece; the layout makes this unambiguous.
- **Shareable permalinks** encode state (country, hour, weights) so a specific "moment" can be linked from `gpu_industry` or a blog post — the essay is navigable even if not configurable.

**Negative / tradeoffs:**
- **Less flexible for repeat analysts.** A user returning to check Norway's grid every morning has to scroll past the hero to reach the ranking. Mitigated by anchor links in the nav and the "jump to simulator" CTA in the hero.
- **Harder to extend with new panels.** Each new section must be placed in the narrative sequence deliberately. This is a feature (it enforces coherence) and a mild cost (adding a panel requires editorial judgment, not just column placement).
- Not appropriate if the product pivots to a multi-user operations center. Replace with a configurable grid layout at that point.

---

## Alternatives considered

| Option | Why rejected |
|---|---|
| **Dashboard grid (Grafana-style)** | Treats the artifact as a reporting tool, not an argument. The thesis gets buried. The hiring-manager audience reads reports all day; the scroll essay is differentiated. |
| **Tab-based layout (Overview / Deep-dive / Simulator)** | Hides evidence behind a click. The ranking strip and map need to be visible before the simulator so the reader understands what the score means. Tabs break the "show first, then let them play" flow. |
| **Single-page app with routing** | Adds build complexity (needs a bundler or SPA framework) for no narrative benefit. The scroll essay is navigable via anchor links without client-side routing. |
