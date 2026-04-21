# Plan A.5 — Interactive Map Enhancements

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Expand the map to ~35 ENTSO-E countries, fix flow-arrow direction, render a default cross-border-flow web, distinguish three workloads (training/fine-tuning/inference) with real behavioral differences, and overlay a curated dataset of hyperscaler regions + GPU neoclouds + EU AI Factories.

**Architecture:** Backend additions are config (more countries in `AREA_CODES`/`COUNTRY_NAMES`/centroids), one new scoring module function (`apply_inference_penalty`), and one extended endpoint contract (`workload`+`region` query params on `/api/ranking` and `/api/css`). Frontend: extend `map.js` for more countries + bidirectional flow arcs + always-on flow web + datacenter overlay layer. New static dataset `frontend/datacenters.json`.

**Tech Stack:** Same as Plan A — FastAPI/pydantic/pandas/entsoe-py/sqlite, vanilla JS + D3 + Chart.js.

**Spec:** `docs/superpowers/specs/2026-04-20-grid-thesis-dashboard-design.md`. This plan supersedes the original Plan B step 4 (map upgrade) and folds the workload-distinction work earlier than originally sequenced.

---

## Task 1: Expand AREA_CODES to ~35 ENTSO-E countries

**Files:** `app/entso.py`, `app/mock_data.py`, `app/geo.py`, `tests/test_entso.py`, `tests/test_geo.py`

**Goal:** Add 15 more countries — Estonia, Latvia, Lithuania, Slovakia, Slovenia, Croatia, Bulgaria, Serbia, Bosnia, Montenegro, North Macedonia, Albania, Iceland, Cyprus, Luxembourg.

- [ ] **Step 1: Failing test for new countries**

Append to `tests/test_entso.py`:

```python
def test_expanded_country_set_includes_balkans_and_baltics():
    expected_new = {"EE", "LV", "LT", "SK", "SI", "HR", "BG", "RS", "BA",
                    "ME", "MK", "AL", "IS", "CY", "LU"}
    for c in expected_new:
        assert c in AREA_CODES, f"missing country {c}"
        assert c in COUNTRY_NAMES, f"missing name for {c}"


def test_total_country_count_around_35():
    assert 33 <= len(AREA_CODES) <= 38
```

Append to `tests/test_geo.py`:

```python
def test_expanded_countries_have_centroids():
    expected_new = {"EE", "LV", "LT", "SK", "SI", "HR", "BG", "RS", "BA",
                    "ME", "MK", "AL", "IS", "CY", "LU"}
    for c in expected_new:
        assert c in COUNTRY_CENTROIDS, f"missing centroid for {c}"
```

Run: `pytest tests/test_entso.py tests/test_geo.py -v` — expect failures.

- [ ] **Step 2: Add countries to `app/entso.py`**

In `AREA_CODES`, append entries with the correct ENTSO-E zone codes. Use `entsoe-py`'s `Area` enum semantics (string IDs):

```python
    "EE": ["EE"],
    "LV": ["LV"],
    "LT": ["LT"],
    "SK": ["SK"],
    "SI": ["SI"],
    "HR": ["HR"],
    "BG": ["BG"],
    "RS": ["RS"],
    "BA": ["BA"],
    "ME": ["ME"],
    "MK": ["MK"],
    "AL": ["AL"],
    "IS": ["IS"],
    "CY": ["CY"],
    "LU": ["LU"],
```

Append to `COUNTRY_NAMES`:

```python
    "EE": "Estonia", "LV": "Latvia", "LT": "Lithuania",
    "SK": "Slovakia", "SI": "Slovenia", "HR": "Croatia",
    "BG": "Bulgaria", "RS": "Serbia", "BA": "Bosnia & Herzegovina",
    "ME": "Montenegro", "MK": "North Macedonia", "AL": "Albania",
    "IS": "Iceland", "CY": "Cyprus", "LU": "Luxembourg",
```

- [ ] **Step 3: Add centroids to `app/geo.py`**

Append to `COUNTRY_CENTROIDS`:

```python
    "EE": (58.60, 25.00),
    "LV": (56.88, 24.60),
    "LT": (55.17, 23.88),
    "SK": (48.67, 19.70),
    "SI": (46.15, 14.99),
    "HR": (45.10, 15.20),
    "BG": (42.73, 25.49),
    "RS": (44.02, 21.00),
    "BA": (43.92, 17.68),
    "ME": (42.71, 19.37),
    "MK": (41.61, 21.75),
    "AL": (41.15, 20.17),
    "IS": (64.96, -19.02),
    "CY": (35.13, 33.43),
    "LU": (49.82, 6.13),
```

- [ ] **Step 4: Mock data fallbacks for new countries**

Read `app/mock_data.py` first to understand the mock structure. The mock module exposes `mock_generation(country)`, `mock_prices(country)`, `mock_flows(country)`, `mock_overview()`. For each new country, add a minimal entry to whichever lookup table the mock module uses. If the structure is "if country not in TABLE: return generic-defaults", you may not need to add anything per-country — but `mock_overview()` likely iterates a fixed list and must include the new countries.

Realistic per-country generation profiles for the new entries (rough but defensible — a coal-leaning country shouldn't show as 90% renewable):

| Country | Profile (mock) | Renewable% | g CO₂/kWh | €/MWh |
|---|---|---|---|---|
| EE | shale-oil, some wind | 30 | 650 | 90 |
| LV | hydro + biomass | 65 | 180 | 78 |
| LT | wind + grid imports | 55 | 280 | 82 |
| SK | nuclear + hydro | 80 | 120 | 75 |
| SI | nuclear + hydro | 75 | 150 | 80 |
| HR | hydro + gas | 60 | 230 | 85 |
| BG | nuclear + lignite | 40 | 380 | 95 |
| RS | lignite-heavy | 25 | 720 | 88 |
| BA | coal-heavy | 30 | 680 | 90 |
| ME | hydro-leaning | 60 | 250 | 82 |
| MK | coal + imports | 30 | 590 | 95 |
| AL | hydro-dominant | 95 | 30 | 75 |
| IS | hydro + geothermal | 100 | 10 | 45 |
| CY | oil-heavy isolated | 15 | 720 | 130 |
| LU | imports-dominated | 50 | 280 | 92 |

Adapt these into the existing mock_data structure. If the file uses a fixture dict keyed by country, add entries.

- [ ] **Step 5: Run tests + commit**

```
pytest tests/ -v
```

Expect: all pass (was 79; will be 81 after the two new tests).

```
git add app/entso.py app/mock_data.py app/geo.py tests/test_entso.py tests/test_geo.py
git commit -m "feat: expand grid coverage to ~35 ENTSO-E countries"
```

---

## Task 2: Update map.js metadata for new countries

**Files:** `frontend/map.js`

**Goal:** The map.js file has `EUROPEAN_IDS`, `COUNTRY_MAP`, `CENTROIDS`, `MAP_FLAGS`, `MAP_NAMES` hardcoded. Extend them so the new 15 countries render with data instead of staying grey.

ISO numeric country codes (for TopoJSON `id` matching):
EE=233, LV=428, LT=440, SK=703, SI=705, HR=191, BG=100, RS=688, BA=70, ME=499, MK=807, AL=8, IS=352, CY=196, LU=442.

- [ ] **Step 1: Extend `EUROPEAN_IDS`**

Add the new IDs (most are already in the existing set since the map already draws greyed-out countries — verify by reading current `EUROPEAN_IDS`). Add any missing.

- [ ] **Step 2: Extend `COUNTRY_MAP`**

Add the 15 new ID→code mappings.

- [ ] **Step 3: Extend `CENTROIDS`** with `[lon, lat]` for each (note D3 uses lon-lat order):

```javascript
'EE':[25,58.6],'LV':[24.6,56.9],'LT':[23.9,55.2],'SK':[19.7,48.7],
'SI':[15,46.1],'HR':[15.2,45.1],'BG':[25.5,42.7],'RS':[21,44],
'BA':[17.7,43.9],'ME':[19.4,42.7],'MK':[21.8,41.6],'AL':[20.2,41.1],
'IS':[-19,65],'CY':[33.4,35.1],'LU':[6.1,49.8],
```

- [ ] **Step 4: Extend `MAP_FLAGS` + `MAP_NAMES`**

```javascript
// MAP_FLAGS
'EE':'🇪🇪','LV':'🇱🇻','LT':'🇱🇹','SK':'🇸🇰','SI':'🇸🇮','HR':'🇭🇷',
'BG':'🇧🇬','RS':'🇷🇸','BA':'🇧🇦','ME':'🇲🇪','MK':'🇲🇰','AL':'🇦🇱',
'IS':'🇮🇸','CY':'🇨🇾','LU':'🇱🇺',

// MAP_NAMES
'EE':'Estonia','LV':'Latvia','LT':'Lithuania','SK':'Slovakia',
'SI':'Slovenia','HR':'Croatia','BG':'Bulgaria','RS':'Serbia',
'BA':'Bosnia & Herzegovina','ME':'Montenegro','MK':'North Macedonia',
'AL':'Albania','IS':'Iceland','CY':'Cyprus','LU':'Luxembourg',
```

- [ ] **Step 5: Re-center the projection**

Iceland sits far northwest; current projection centered on `[14, 54]` may push Iceland off-canvas. Update line ~72:

```javascript
_projection = d3.geoMercator().center([14, 56]).scale(W * 0.95).translate([W / 2, H / 2]);
```

(Slightly higher center, slightly lower scale, to fit Iceland and Cyprus.)

- [ ] **Step 6: Smoke test in browser + commit**

Restart server (kill prior uvicorn, start new one), open `http://127.0.0.1:8001/`, verify the new countries are now color-coded by CO₂ instead of grey.

```
git add frontend/map.js
git commit -m "feat(map): extend metadata + projection to cover 35 countries"
```

---

## Task 3: Workload presets in scoring

**Files:** `app/scoring.py`, `tests/test_scoring.py`

**Goal:** Three workload modes — training/fine-tuning/inference — each with its own preset weights, distinct from the user-facing Green/Balanced/Cost weight presets. The user-facing presets shape what's important; the workload presets shape *how the user* should think about siting.

- [ ] **Step 1: Failing tests**

Append to `tests/test_scoring.py`:

```python
from app.scoring import WORKLOAD_PRESETS, weights_for_workload


def test_three_workload_presets_defined():
    assert set(WORKLOAD_PRESETS.keys()) == {"training", "fine-tuning", "inference"}


def test_each_workload_preset_sums_to_100():
    for w in WORKLOAD_PRESETS.values():
        assert sum(w.values()) == 100


def test_training_emphasizes_carbon_and_cost():
    w = WORKLOAD_PRESETS["training"]
    # Training is long-running, latency-insensitive — clean+cheap dominate
    assert w["carbon"] >= 35
    assert w["cost"] >= 25


def test_inference_emphasizes_cost():
    w = WORKLOAD_PRESETS["inference"]
    # Inference is continuous and cost-dominant; carbon stays meaningful but smaller
    assert w["cost"] >= 35


def test_weights_for_workload_unknown_raises():
    with pytest.raises(KeyError):
        weights_for_workload("inferring")
```

Run: `pytest tests/test_scoring.py -v` — expect failures.

- [ ] **Step 2: Implement**

Append to `app/scoring.py` (after the existing PRESET_* constants):

```python
# Workload presets — different from user weight presets. These shape the
# implicit weighting per workload type even when the user sticks with
# "Balanced". A solutions-engineer would never run training and inference
# scoring identically; siting concerns differ materially.
WORKLOAD_PRESETS: dict[str, Weights] = {
    "training":    {"carbon": 40, "cost": 30, "renewable": 20, "stability": 10},
    "fine-tuning": {"carbon": 30, "cost": 40, "renewable": 20, "stability": 10},
    "inference":   {"carbon": 20, "cost": 45, "renewable": 15, "stability": 20},
}


def weights_for_workload(workload: str) -> Weights:
    if workload not in WORKLOAD_PRESETS:
        raise KeyError(f"unknown workload {workload!r}; expected one of {set(WORKLOAD_PRESETS)}")
    return dict(WORKLOAD_PRESETS[workload])
```

- [ ] **Step 3: Run + commit**

```
pytest tests/test_scoring.py -v
git add app/scoring.py tests/test_scoring.py
git commit -m "feat(scoring): workload-aware weight presets (training/fine-tuning/inference)"
```

---

## Task 4: Per-country latency-adjusted CSS

**Files:** `app/scoring.py`, `tests/test_scoring.py`

**Goal:** When workload is `inference` and a serving region is given, each country's CSS gets multiplied by `(1 - latency_penalty(country, region))`. This makes the ranking actually shift by serving region — the current implementation applies penalty uniformly so it cancels out (the bug noted at end of Plan A).

- [ ] **Step 1: Failing tests**

Append to `tests/test_scoring.py`:

```python
from app.scoring import apply_per_country_latency_penalty


def test_apply_latency_penalty_no_region_passthrough():
    results = compute_css([
        _metrics("FR", 40, 70, 90, 5),
        _metrics("PT", 200, 80, 60, 8),
    ], DEFAULT_WEIGHTS)
    out = apply_per_country_latency_penalty(results, region=None)
    assert [r.css for r in out] == [r.css for r in results]


def test_apply_latency_penalty_western_favors_close_country():
    results = compute_css([
        _metrics("FR", 40, 70, 90, 5),
        _metrics("PT", 100, 75, 80, 6),
    ], DEFAULT_WEIGHTS)
    out = apply_per_country_latency_penalty(results, region="western")
    fr_out = next(r for r in out if r.country == "FR")
    pt_out = next(r for r in out if r.country == "PT")
    fr_in = next(r for r in results if r.country == "FR")
    pt_in = next(r for r in results if r.country == "PT")
    # FR is in western-zone (penalty=0); PT pays a small penalty
    assert fr_out.css == fr_in.css
    assert pt_out.css < pt_in.css


def test_apply_latency_penalty_northern_far_country_drops():
    results = compute_css([_metrics("PT", 100, 75, 80, 6)], DEFAULT_WEIGHTS)
    out = apply_per_country_latency_penalty(results, region="northern")
    # PT scored alone gets css=50 (single-country normalization). With northern
    # latency penalty ≈ 0.4, css drops to ≈ 30.
    assert 27 < out[0].css < 33
```

Run: `pytest tests/test_scoring.py -v` — expect failures.

- [ ] **Step 2: Implement**

Append to `app/scoring.py`:

```python
def apply_per_country_latency_penalty(
    results: list["CSSResult"],
    region: Optional[str],
) -> list["CSSResult"]:
    """For each country, multiply its CSS by (1 - latency_penalty(country, region))."""
    if region is None:
        return results
    # Lazy import to avoid cycle (geo doesn't import scoring, but be defensive)
    from app.geo import latency_penalty
    out: list[CSSResult] = []
    for r in results:
        try:
            penalty = latency_penalty(r.country, region)
        except KeyError:
            penalty = 0.0
        out.append(CSSResult(
            country=r.country,
            css=round(r.css * (1 - penalty), 2),
            carbon_score=r.carbon_score,
            cost_score=r.cost_score,
            renewable_score=r.renewable_score,
            stability_score=r.stability_score,
        ))
    return out
```

Add `from typing import Optional` to imports if not present.

- [ ] **Step 3: Run + commit**

```
pytest tests/test_scoring.py -v
git add app/scoring.py tests/test_scoring.py
git commit -m "feat(scoring): per-country latency penalty for inference workload"
```

---

## Task 5: Wire workload + region into /api endpoints

**Files:** `app/routes.py`, `tests/test_routes.py`

**Goal:** Add `workload` and `region` query params to `/api/ranking` and `/api/css`. If `workload` is set, use its preset weights (overrides `weights=`). If `region` is set, apply per-country latency penalty.

- [ ] **Step 1: Failing tests**

Append to `tests/test_routes.py`:

```python
def test_ranking_with_workload_inference_western_shifts_iberian_down(client):
    with patch("app.routes._LIVE", False):
        train = client.get("/api/ranking?workload=training").json()
        infer_w = client.get("/api/ranking?workload=inference&region=western").json()
        infer_n = client.get("/api/ranking?workload=inference&region=northern").json()
    # Portugal/Spain should rank lower in inference+northern than in inference+western
    def rank_of(payload, country):
        for i, c in enumerate(payload["countries"]):
            if c["country"] == country: return i
        return None
    assert rank_of(infer_n, "PT") > rank_of(infer_w, "PT") or rank_of(infer_n, "ES") > rank_of(infer_w, "ES")


def test_ranking_inference_without_region_returns_400(client):
    r = client.get("/api/ranking?workload=inference")
    assert r.status_code == 400


def test_ranking_workload_overrides_weights_param(client):
    with patch("app.routes._LIVE", False):
        # workload=training should force balanced-ish weights regardless of weights=cost
        r = client.get("/api/ranking?workload=training&weights=cost").json()
    # Workload preset wins — assert the response weights match training's preset
    assert r["weights"] == {"carbon": 40, "cost": 30, "renewable": 20, "stability": 10}
```

Run: `pytest tests/test_routes.py -v` — expect failures.

- [ ] **Step 2: Implement**

Modify `_parse_weights` calls in `/api/ranking`, `/api/css`, `/api/simulate` to use a new helper that honors workload override:

```python
from app.scoring import (
    ..., WORKLOAD_PRESETS, weights_for_workload, apply_per_country_latency_penalty,
)


VALID_REGIONS = {"central", "western", "northern", "southern", "iberian"}


def _resolve_weights(workload: Optional[str], weights: Optional[str]) -> Weights:
    if workload:
        if workload not in WORKLOAD_PRESETS:
            raise HTTPException(400, f"workload must be one of {sorted(WORKLOAD_PRESETS)}")
        return weights_for_workload(workload)
    return _parse_weights(weights)


def _validate_region(region: Optional[str]) -> None:
    if region is not None and region not in VALID_REGIONS:
        raise HTTPException(400, f"region must be one of {sorted(VALID_REGIONS)}")
```

Update `/api/ranking`:

```python
@router.get("/api/ranking")
def get_ranking(
    weights: Optional[str] = Query(None),
    workload: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    carbon_price: Optional[float] = Query(DEFAULT_CARBON_PRICE_EUR_PER_TCO2),
):
    if workload == "inference" and not region:
        raise HTTPException(400, "inference workload requires region")
    _validate_region(region)
    w = _resolve_weights(workload, weights)
    cache_key = f"ranking:{sorted(w.items())}:{workload}:{region}:{carbon_price}"
    cached = ranking_cache.get(cache_key)
    if cached:
        return cached

    grid = _build_grid(carbon_price)
    results = compute_css(grid, w)
    if workload == "inference":
        results = apply_per_country_latency_penalty(results, region)
    results = rank_countries(results)
    payload = {
        "countries": [
            RankingEntry(
                country=r.country, name=COUNTRY_NAMES.get(r.country, r.country),
                css=r.css, carbon_score=r.carbon_score, cost_score=r.cost_score,
                renewable_score=r.renewable_score, stability_score=r.stability_score,
            ).model_dump() for r in results
        ],
        "weights": w,
        "workload": workload,
        "region": region,
        "carbon_price_eur_per_tco2": carbon_price,
    }
    ranking_cache.set(cache_key, payload)
    return payload
```

Apply analogous changes to `/api/css`. For `/api/simulate`, replace the inline workload-handling with a call through `_resolve_weights`.

- [ ] **Step 3: Run full suite + commit**

```
pytest tests/ -v
git add app/routes.py tests/test_routes.py
git commit -m "feat(api): workload + region params; ranking shifts by serving region for inference"
```

---

## Task 6: Three-way workload UI toggle + serving region

**Files:** `frontend/index.html`, `frontend/style.css`, `frontend/ranking.js`

**Goal:** Replace the 2-button training/inference toggle with three buttons + a region selector that appears only for inference.

- [ ] **Step 1: Edit `index.html`**

Replace the existing `.workload-switcher` inside `.ranking-controls` (in the ranking-strip section) with:

```html
<div class="workload-switcher" role="radiogroup" aria-label="workload mode">
  <button class="workload-btn active" data-workload="training">Training</button>
  <button class="workload-btn" data-workload="fine-tuning">Fine-tuning</button>
  <button class="workload-btn" data-workload="inference">Inference</button>
</div>
<select id="region-select" class="region-select" style="display:none">
  <option value="central">🛰 Central EU</option>
  <option value="western" selected>🛰 Western EU</option>
  <option value="northern">🛰 Northern EU</option>
  <option value="southern">🛰 Southern EU</option>
  <option value="iberian">🛰 Iberian</option>
</select>
```

- [ ] **Step 2: Add region-select style to `style.css`**

Append:

```css
.region-select {
  background: var(--bg-card2); border: 1px solid var(--border);
  color: var(--text); padding: 5px 10px; border-radius: 99px;
  font-size: 11px; font-family: var(--mono); cursor: pointer;
}
```

- [ ] **Step 3: Update `frontend/ranking.js`**

Replace the file with:

```javascript
const RankingState = {
  preset: "balanced",
  workload: "training",
  region: "western",
};

async function renderRanking() {
  const list = document.getElementById("ranking-list");
  try {
    // Workload overrides preset weights server-side; we still pass region for inference.
    const params = new URLSearchParams({ workload: RankingState.workload });
    if (RankingState.workload === "inference") params.set("region", RankingState.region);
    if (RankingState.preset !== "balanced") params.set("weights", RankingState.preset);
    const data = await fetchJson(`/api/ranking?${params}`);
    list.innerHTML = "";
    data.countries.forEach((c, i) => {
      const card = document.createElement("div");
      card.className = "rank-card" + (i === 0 ? " top" : "");
      card.dataset.country = c.country;
      card.innerHTML = `<div class="num">${Math.round(c.css)}</div><div class="name">${c.name}</div>`;
      card.addEventListener("click", () => {
        const sel = document.getElementById("country-select");
        if (sel) { sel.value = c.country; sel.dispatchEvent(new Event("change")); }
      });
      list.appendChild(card);
    });
  } catch (e) {
    list.textContent = "Failed to load ranking.";
    console.error(e);
  }
}

function wireRankingControls() {
  document.querySelectorAll(".preset-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".preset-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      RankingState.preset = btn.dataset.preset;
      renderRanking();
    });
  });
  document.querySelectorAll(".workload-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".workload-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      RankingState.workload = btn.dataset.workload;
      const regionSel = document.getElementById("region-select");
      if (regionSel) regionSel.style.display = btn.dataset.workload === "inference" ? "" : "none";
      renderRanking();
    });
  });
  const regionSel = document.getElementById("region-select");
  if (regionSel) regionSel.addEventListener("change", () => {
    RankingState.region = regionSel.value;
    renderRanking();
  });
}

document.addEventListener("DOMContentLoaded", () => {
  wireRankingControls();
  renderRanking();
});
```

(Note: `fetchJson` is exposed by `api.js` as it was in Task 12 of Plan A. If your build of `api.js` uses a different name, swap.)

- [ ] **Step 4: Smoke test + commit**

Restart uvicorn, refresh the browser. Click Training/Fine-tuning/Inference; for Inference, the region select appears and changing it re-orders the ranking.

```
git add frontend/index.html frontend/style.css frontend/ranking.js
git commit -m "feat(ui): three-way workload toggle + serving region for inference"
```

---

## Task 7: Fix flow-arrow direction

**Files:** `frontend/map.js`

**Goal:** Currently arrows always arc *from* the selected country *to* each partner; only color (blue=import, orange=export) tells direction. Make arrow geometry match physical direction: import flows arc *from* partner *to* selected country, export flows arc *from* selected *to* partner.

- [ ] **Step 1: Edit `drawFlowArrows` in `map.js`**

Find the `window.drawFlowArrows = function(flows, fromCountry) { ... }` block and replace with:

```javascript
window.drawFlowArrows = function(flows, fromCountry) {
  _svgG.selectAll('.flow-arrow').remove();
  if (!flows || !fromCountry) return;
  const selPos = CENTROIDS[fromCountry];
  if (!selPos) return;
  const [sx, sy] = _projection(selPos);

  flows.forEach(flow => {
    const partnerCode = Object.entries(window.MAP_NAMES).find(([k, v]) => v === flow.partner)?.[0];
    if (!partnerCode || !CENTROIDS[partnerCode]) return;
    const [px, py] = _projection(CENTROIDS[partnerCode]);

    // Geometry: source = origin of flow, dest = receiver
    const isExport = flow.direction === 'export';
    const [x1, y1, x2, y2] = isExport ? [sx, sy, px, py] : [px, py, sx, sy];

    const mx = (x1 + x2) / 2 + (y2 - y1) * 0.2;
    const my = (y1 + y2) / 2 - (x2 - x1) * 0.2;

    _svgG.append('path')
      .attr('class', 'flow-arrow')
      .attr('d', `M${x1},${y1} Q${mx},${my} ${x2},${y2}`)
      .attr('fill', 'none')
      .attr('stroke', isExport ? '#f78166' : '#58a6ff')
      .attr('stroke-width', 1.4).attr('opacity', 0.7)
      .attr('marker-end', isExport ? 'url(#arrowOrange)' : 'url(#arrowBlue)');
  });
};
```

- [ ] **Step 2: Visual check + commit**

Reload the browser, select Germany (a known importer from Norway, exporter to Poland). Verify import arrows point INTO Germany and export arrows point OUT.

```
git add frontend/map.js
git commit -m "fix(map): flow-arrow geometry matches actual direction"
```

---

## Task 8: Default-on cross-border flow web

**Files:** `frontend/map.js`, `frontend/api.js`

**Goal:** On map init, fetch flows for all countries in parallel; render each flow as a thin, faded line. When the user selects a country, that country's flows render thicker/brighter (existing behavior). The web gives an at-a-glance "shape" of European electricity trade.

- [ ] **Step 1: Add `fetchAllFlows` helper in `api.js`**

Append to `api.js`:

```javascript
async function fetchAllFlows(countryCodes) {
  const results = await Promise.allSettled(
    countryCodes.map(c => fetchJson(`/api/flows?country=${c}`).then(d => ({country: c, ...d})))
  );
  return results.filter(r => r.status === 'fulfilled').map(r => r.value);
}
window.fetchAllFlows = fetchAllFlows;
```

- [ ] **Step 2: Render web on map init**

In `window.initMap` in `map.js`, AFTER the overview-coloring block, add:

```javascript
// Background flow web — all bilateral imports/exports as thin lines.
try {
  const allFlows = await window.fetchAllFlows(Object.keys(window.MAP_NAMES));
  const seenEdges = new Set();
  allFlows.forEach(({country, flows}) => {
    if (!flows) return;
    const fromPos = CENTROIDS[country];
    if (!fromPos) return;
    const [x1, y1] = _projection(fromPos);
    flows.forEach(flow => {
      const partnerCode = Object.entries(window.MAP_NAMES).find(([k, v]) => v === flow.partner)?.[0];
      if (!partnerCode || !CENTROIDS[partnerCode]) return;
      // dedupe undirected edges
      const edgeKey = [country, partnerCode].sort().join('—');
      if (seenEdges.has(edgeKey)) return;
      seenEdges.add(edgeKey);
      const [x2, y2] = _projection(CENTROIDS[partnerCode]);
      const mx = (x1 + x2) / 2 + (y2 - y1) * 0.18;
      const my = (y1 + y2) / 2 - (x2 - x1) * 0.18;
      _svgG.insert('path', '.country')      // insert behind country layer? prefer above ocean, below countries
        .attr('class', 'flow-web')
        .attr('d', `M${x1},${y1} Q${mx},${my} ${x2},${y2}`)
        .attr('fill', 'none')
        .attr('stroke', 'var(--accent)')
        .attr('stroke-width', Math.min(2.2, 0.5 + flow.flow_gw * 0.3))
        .attr('opacity', 0.18);
    });
  });
} catch (e) { console.warn('flow web fetch failed:', e); }
```

Note: `_svgG.insert(..., '.country')` inserts before the first `.country` so the web sits underneath country fills. If z-ordering looks wrong in browser, swap to `.append` and bump opacity lower.

- [ ] **Step 3: Smoke + commit**

Reload browser. Faded lines connect every country with active flow data. Selecting a country still draws the bright flow arrows on top (Task 7 fix).

```
git add frontend/map.js frontend/api.js
git commit -m "feat(map): background cross-border flow web rendered by default"
```

---

## Task 9: Datacenter dataset (curated JSON)

**Files:** `frontend/datacenters.json`

**Goal:** Compile a single static JSON file with hyperscaler EU regions, top GPU neoclouds with European presence, and announced EU AI Factories. Each entry: `{name, operator, type, lat, lon, country, notes?}`. Type one of `hyperscaler|neocloud|ai-factory`.

- [ ] **Step 1: Create `frontend/datacenters.json`**

```json
{
  "datacenters": [
    {"name": "AWS eu-west-1", "operator": "AWS", "type": "hyperscaler", "country": "IE", "lat": 53.35, "lon": -6.26, "notes": "Dublin"},
    {"name": "AWS eu-west-2", "operator": "AWS", "type": "hyperscaler", "country": "GB", "lat": 51.51, "lon": -0.13, "notes": "London"},
    {"name": "AWS eu-west-3", "operator": "AWS", "type": "hyperscaler", "country": "FR", "lat": 48.86, "lon": 2.35, "notes": "Paris"},
    {"name": "AWS eu-central-1", "operator": "AWS", "type": "hyperscaler", "country": "DE", "lat": 50.11, "lon": 8.68, "notes": "Frankfurt"},
    {"name": "AWS eu-central-2", "operator": "AWS", "type": "hyperscaler", "country": "CH", "lat": 47.38, "lon": 8.54, "notes": "Zurich"},
    {"name": "AWS eu-north-1", "operator": "AWS", "type": "hyperscaler", "country": "SE", "lat": 59.33, "lon": 18.07, "notes": "Stockholm"},
    {"name": "AWS eu-south-1", "operator": "AWS", "type": "hyperscaler", "country": "IT", "lat": 45.46, "lon": 9.19, "notes": "Milan"},
    {"name": "AWS eu-south-2", "operator": "AWS", "type": "hyperscaler", "country": "ES", "lat": 40.42, "lon": -3.70, "notes": "Madrid (Aragón)"},

    {"name": "GCP europe-west1", "operator": "GCP", "type": "hyperscaler", "country": "BE", "lat": 50.45, "lon": 3.82, "notes": "St. Ghislain"},
    {"name": "GCP europe-west2", "operator": "GCP", "type": "hyperscaler", "country": "GB", "lat": 51.51, "lon": -0.13, "notes": "London"},
    {"name": "GCP europe-west3", "operator": "GCP", "type": "hyperscaler", "country": "DE", "lat": 50.11, "lon": 8.68, "notes": "Frankfurt"},
    {"name": "GCP europe-west4", "operator": "GCP", "type": "hyperscaler", "country": "NL", "lat": 53.43, "lon": 6.83, "notes": "Eemshaven"},
    {"name": "GCP europe-west6", "operator": "GCP", "type": "hyperscaler", "country": "CH", "lat": 47.38, "lon": 8.54, "notes": "Zurich"},
    {"name": "GCP europe-west8", "operator": "GCP", "type": "hyperscaler", "country": "IT", "lat": 45.46, "lon": 9.19, "notes": "Milan"},
    {"name": "GCP europe-west9", "operator": "GCP", "type": "hyperscaler", "country": "FR", "lat": 48.86, "lon": 2.35, "notes": "Paris"},
    {"name": "GCP europe-west10", "operator": "GCP", "type": "hyperscaler", "country": "DE", "lat": 52.52, "lon": 13.40, "notes": "Berlin"},
    {"name": "GCP europe-west12", "operator": "GCP", "type": "hyperscaler", "country": "IT", "lat": 45.07, "lon": 7.69, "notes": "Turin"},
    {"name": "GCP europe-north1", "operator": "GCP", "type": "hyperscaler", "country": "FI", "lat": 60.55, "lon": 26.10, "notes": "Hamina"},
    {"name": "GCP europe-southwest1", "operator": "GCP", "type": "hyperscaler", "country": "ES", "lat": 40.42, "lon": -3.70, "notes": "Madrid"},
    {"name": "GCP europe-central2", "operator": "GCP", "type": "hyperscaler", "country": "PL", "lat": 52.23, "lon": 21.01, "notes": "Warsaw"},

    {"name": "Azure West Europe", "operator": "Azure", "type": "hyperscaler", "country": "NL", "lat": 52.37, "lon": 4.89, "notes": "Amsterdam"},
    {"name": "Azure North Europe", "operator": "Azure", "type": "hyperscaler", "country": "IE", "lat": 53.35, "lon": -6.26, "notes": "Dublin"},
    {"name": "Azure UK South", "operator": "Azure", "type": "hyperscaler", "country": "GB", "lat": 51.51, "lon": -0.13, "notes": "London"},
    {"name": "Azure UK West", "operator": "Azure", "type": "hyperscaler", "country": "GB", "lat": 51.48, "lon": -3.18, "notes": "Cardiff"},
    {"name": "Azure Germany West Central", "operator": "Azure", "type": "hyperscaler", "country": "DE", "lat": 50.11, "lon": 8.68, "notes": "Frankfurt"},
    {"name": "Azure France Central", "operator": "Azure", "type": "hyperscaler", "country": "FR", "lat": 48.86, "lon": 2.35, "notes": "Paris"},
    {"name": "Azure Norway East", "operator": "Azure", "type": "hyperscaler", "country": "NO", "lat": 59.91, "lon": 10.75, "notes": "Oslo"},
    {"name": "Azure Sweden Central", "operator": "Azure", "type": "hyperscaler", "country": "SE", "lat": 60.67, "lon": 17.14, "notes": "Gävle"},
    {"name": "Azure Switzerland North", "operator": "Azure", "type": "hyperscaler", "country": "CH", "lat": 47.38, "lon": 8.54, "notes": "Zurich"},
    {"name": "Azure Italy North", "operator": "Azure", "type": "hyperscaler", "country": "IT", "lat": 45.46, "lon": 9.19, "notes": "Milan"},
    {"name": "Azure Spain Central", "operator": "Azure", "type": "hyperscaler", "country": "ES", "lat": 40.42, "lon": -3.70, "notes": "Madrid"},
    {"name": "Azure Poland Central", "operator": "Azure", "type": "hyperscaler", "country": "PL", "lat": 52.23, "lon": 21.01, "notes": "Warsaw"},

    {"name": "CoreWeave Frankfurt", "operator": "CoreWeave", "type": "neocloud", "country": "DE", "lat": 50.11, "lon": 8.68},
    {"name": "CoreWeave Stockholm", "operator": "CoreWeave", "type": "neocloud", "country": "SE", "lat": 59.33, "lon": 18.07},
    {"name": "Nebius Mäntsälä", "operator": "Nebius", "type": "neocloud", "country": "FI", "lat": 60.63, "lon": 25.32, "notes": "Mäntsälä, Finland"},
    {"name": "Nebius Paris", "operator": "Nebius", "type": "neocloud", "country": "FR", "lat": 48.86, "lon": 2.35},
    {"name": "Northern Data Norway", "operator": "Northern Data", "type": "neocloud", "country": "NO", "lat": 60.39, "lon": 5.32, "notes": "Bergen area"},
    {"name": "Scaleway Paris", "operator": "Scaleway", "type": "neocloud", "country": "FR", "lat": 48.86, "lon": 2.35},
    {"name": "Scaleway Amsterdam", "operator": "Scaleway", "type": "neocloud", "country": "NL", "lat": 52.37, "lon": 4.89},
    {"name": "Scaleway Warsaw", "operator": "Scaleway", "type": "neocloud", "country": "PL", "lat": 52.23, "lon": 21.01},
    {"name": "Hetzner Falkenstein", "operator": "Hetzner", "type": "neocloud", "country": "DE", "lat": 50.48, "lon": 12.36, "notes": "GPU cloud"},
    {"name": "Hetzner Helsinki", "operator": "Hetzner", "type": "neocloud", "country": "FI", "lat": 60.17, "lon": 24.94},
    {"name": "OVHcloud Gravelines", "operator": "OVHcloud", "type": "neocloud", "country": "FR", "lat": 50.99, "lon": 2.13, "notes": "Hyperscale GPU campus"},
    {"name": "OVHcloud Frankfurt", "operator": "OVHcloud", "type": "neocloud", "country": "DE", "lat": 50.11, "lon": 8.68},

    {"name": "JUPITER (Jülich)", "operator": "EuroHPC", "type": "ai-factory", "country": "DE", "lat": 50.91, "lon": 6.41, "notes": "Exascale; first EU AI Factory"},
    {"name": "LUMI (Kajaani)", "operator": "EuroHPC", "type": "ai-factory", "country": "FI", "lat": 64.23, "lon": 27.73, "notes": "Pre-exascale; hydropower"},
    {"name": "Leonardo (CINECA)", "operator": "EuroHPC", "type": "ai-factory", "country": "IT", "lat": 44.51, "lon": 11.34, "notes": "Bologna"},
    {"name": "MareNostrum 5 (BSC)", "operator": "EuroHPC", "type": "ai-factory", "country": "ES", "lat": 41.39, "lon": 2.17, "notes": "Barcelona"},
    {"name": "Karolina (IT4I)", "operator": "EuroHPC", "type": "ai-factory", "country": "CZ", "lat": 49.83, "lon": 18.16, "notes": "Ostrava"},
    {"name": "MeluXina", "operator": "EuroHPC", "type": "ai-factory", "country": "LU", "lat": 49.61, "lon": 6.13},
    {"name": "Discoverer", "operator": "EuroHPC", "type": "ai-factory", "country": "BG", "lat": 42.69, "lon": 23.32, "notes": "Sofia"},
    {"name": "Vega", "operator": "EuroHPC", "type": "ai-factory", "country": "SI", "lat": 46.55, "lon": 15.65, "notes": "Maribor"},
    {"name": "Deucalion", "operator": "EuroHPC", "type": "ai-factory", "country": "PT", "lat": 41.55, "lon": -8.42, "notes": "Braga"},
    {"name": "EHPCPL (PSNC)", "operator": "EuroHPC", "type": "ai-factory", "country": "PL", "lat": 52.40, "lon": 16.92, "notes": "Poznań"},
    {"name": "Bayern AI Factory", "operator": "EuroHPC", "type": "ai-factory", "country": "DE", "lat": 48.13, "lon": 11.58, "notes": "Munich-area, planned"},
    {"name": "Athena AI Factory", "operator": "EuroHPC", "type": "ai-factory", "country": "GR", "lat": 37.98, "lon": 23.73, "notes": "Athens, planned"},
    {"name": "Sweden AI Factory", "operator": "EuroHPC", "type": "ai-factory", "country": "SE", "lat": 58.41, "lon": 15.62, "notes": "Linköping, planned"}
  ]
}
```

- [ ] **Step 2: Commit**

```
git add frontend/datacenters.json
git commit -m "data: curated EU datacenter map — hyperscalers + neoclouds + AI Factories"
```

(No tests — it's a static dataset that the next task consumes.)

---

## Task 10: Datacenter overlay layer

**Files:** `frontend/map.js`, `frontend/style.css`, `frontend/index.html`

**Goal:** Add a toggleable overlay that draws each datacenter as a colored dot on the map, with a small legend.

- [ ] **Step 1: Add overlay control to `index.html`**

Inside the `.map-card` div (where the map SVG lives), add immediately after the `<div class="card-title">…</div>` block:

```html
<div class="dc-overlay-controls">
  <label class="dc-toggle"><input type="checkbox" id="dc-toggle-hyperscaler" checked> <span class="dc-dot dc-hyper"></span> Hyperscalers</label>
  <label class="dc-toggle"><input type="checkbox" id="dc-toggle-neocloud" checked> <span class="dc-dot dc-neo"></span> GPU Neoclouds</label>
  <label class="dc-toggle"><input type="checkbox" id="dc-toggle-ai-factory" checked> <span class="dc-dot dc-aif"></span> EU AI Factories</label>
</div>
```

- [ ] **Step 2: Style the overlay in `style.css`**

Append:

```css
.dc-overlay-controls { display: flex; flex-wrap: wrap; gap: 12px; margin: 6px 0 10px; font-size: 11px; color: var(--muted); }
.dc-toggle { display: inline-flex; align-items: center; gap: 6px; cursor: pointer; user-select: none; }
.dc-dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; }
.dc-hyper { background: #58a6ff; }
.dc-neo { background: #d2a8ff; }
.dc-aif { background: #9cc98a; }
.dc-marker { transition: r 0.15s; cursor: pointer; }
.dc-marker:hover { stroke: var(--text); stroke-width: 1; }
```

- [ ] **Step 3: Render markers in `map.js`**

Append to `map.js` (outside `initMap`):

```javascript
const DC_COLORS = { 'hyperscaler': '#58a6ff', 'neocloud': '#d2a8ff', 'ai-factory': '#9cc98a' };
const DC_RADIUS = { 'hyperscaler': 2.5, 'neocloud': 2.8, 'ai-factory': 3.4 };
let _datacenters = [];
const _dcVisible = { 'hyperscaler': true, 'neocloud': true, 'ai-factory': true };

async function _loadDatacenters() {
  try {
    const r = await fetch('/datacenters.json');
    const data = await r.json();
    _datacenters = data.datacenters || [];
  } catch (e) { console.warn('dc load failed:', e); }
}

function _renderDatacenters() {
  _svgG.selectAll('.dc-marker').remove();
  _datacenters.forEach(dc => {
    if (!_dcVisible[dc.type]) return;
    const [x, y] = _projection([dc.lon, dc.lat]);
    if (Number.isNaN(x) || Number.isNaN(y)) return;
    const g = _svgG.append('g').attr('class', 'dc-marker');
    g.append('circle')
      .attr('cx', x).attr('cy', y)
      .attr('r', DC_RADIUS[dc.type])
      .attr('fill', DC_COLORS[dc.type])
      .attr('opacity', 0.85)
      .attr('stroke', 'rgba(0,0,0,0.4)')
      .attr('stroke-width', 0.4);
    g.append('title').text(`${dc.name} · ${dc.operator}${dc.notes ? ' · ' + dc.notes : ''}`);
  });
}

function _wireDatacenterToggles() {
  ['hyperscaler', 'neocloud', 'ai-factory'].forEach(t => {
    const id = `dc-toggle-${t === 'ai-factory' ? 'ai-factory' : t}`;
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('change', () => {
      _dcVisible[t] = el.checked;
      _renderDatacenters();
    });
  });
}
```

In `window.initMap`, AFTER the flow-web block, add:

```javascript
await _loadDatacenters();
_renderDatacenters();
_wireDatacenterToggles();
```

- [ ] **Step 4: Smoke test + commit**

Restart server, refresh browser. Confirm the three datacenter colors render across the map; toggling checkboxes hides/shows each layer; hovering a dot shows a native tooltip.

```
git add frontend/index.html frontend/map.js frontend/style.css
git commit -m "feat(map): toggleable hyperscaler/neocloud/AI-factory overlay"
```

---

## Task 11: Smoke test + tag

**Files:** none

- [ ] **Step 1: Full regression**

```
pytest tests/ -q
```

Expect: all green.

- [ ] **Step 2: End-to-end browser walkthrough**

Restart uvicorn. Open `http://127.0.0.1:8001/`. Verify:
- 35 countries colored by CO₂ on the map (not just 20).
- Three workload buttons; clicking Inference reveals region selector; changing region re-orders ranking.
- Cross-border flow web visible faintly across the continent.
- Selecting a country shows directional flow arrows (imports point INTO selected, exports point OUT).
- Datacenter dots visible (blue hyperscalers, purple neoclouds, green AI Factories); toggles work.

- [ ] **Step 3: Tag**

```
git tag plan-a5-complete
git log --oneline plan-a5-complete -15
```

Plan A.5 done.
