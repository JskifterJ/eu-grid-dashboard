# Plan A.6 — Interactivity & Explainability

**Goal:** Make the dashboard legible to a non-technical reviewer. Add map pan+zoom, rich hover tooltips, a collapsible methodology panel explaining the math (CSS formula, carbon pricing, inference latency penalty), a workload explainer popover, a serving-region caption, and collapse the ranking to top/bottom chunks with an "expand" affordance. Fix the stale "all 20 countries" label.

**Architecture:** Pure frontend. D3 zoom behavior on the SVG; lightweight vanilla-JS tooltip system (one floating div reused across features); an expandable methodology section beneath the ranking strip. No backend changes.

**Tech Stack:** D3 v7 (zoom already in the D3 bundle), vanilla JS, CSS variables.

## Tasks

1. Map pan + zoom
2. Rich datacenter hover tooltip
3. Ranking card CSS-breakdown tooltip
4. Workload explainer popover
5. Region selector explainer caption
6. Top/bottom ranking view + fix "20" label
7. Methodology explainer panel
8. Smoke test + tag `plan-a6-complete`

Each task commits independently. Browser-refresh verifiable.
