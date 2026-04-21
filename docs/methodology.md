# CSS Methodology

This document describes how the **Compute Siting Score (CSS)** is computed, what data sources feed it, and where the model falls short.

---

## Overview

The CSS is a composite 0–100 score that ranks European countries as destinations for AI compute workloads. It is computed per country, per hour, by normalising four grid metrics across all covered countries and combining them with configurable weights. A score of 100 means the cleanest, cheapest, most stable grid in the sample at that moment; a score of 0 means the worst. The score answers the question: *given today's grid, where in Europe should a compute job run?*

The formula is:

```
CSS(c) = Σ  w_d × normalized_d(c)      where Σ w = 100, each normalized_d ∈ [0, 100]
```

Normalisation is min-max across all covered countries at the same hour, so scores are always relative, not absolute. A country's CSS tells you its rank in the current cross-European sample; it does not tell you whether European grids are clean in absolute terms.

---

## The four dimensions

### 1. Carbon intensity

**What it measures:** lifecycle CO₂-equivalent emissions per unit of electricity delivered, in g CO₂e/kWh.

**Formula:**

```
carbon_intensity(c) = Σ (generation_source_GW × emission_factor_gco2_per_kwh) / total_GW(c)
```

Generation volumes (GW) come from the ENTSO-E Transparency Platform generation-per-source feed. Emission factors are the **IPCC AR5 (2014) median lifecycle values** — the same values used in grid-carbon research (e.g., Ember, electricityMaps). Lifecycle means manufacture, fuel cycle, and end-of-life are included; these are higher than operational-only factors, which is intentional: a data centre operator comparing grid options is responsible for the full system, not just combustion.

Selected factors (g CO₂e/kWh): coal ~820, gas (CCGT) ~490, oil ~650, nuclear ~12, onshore wind ~11, solar PV ~48, hydro ~24, biomass ~230.

**Source:** IPCC, 2014. *Climate Change 2014: Mitigation of Climate Change*. Working Group III, Annex II, Table A.III.2. [https://www.ipcc.ch/report/ar5/wg3/](https://www.ipcc.ch/report/ar5/wg3/)

Lower is better; the normalization is flipped so a lower raw value yields a higher score.

### 2. Cost (carbon-internalized)

**What it measures:** the effective economic cost of electricity after internalising the social cost of carbon at the prevailing EU ETS price.

**Formula:**

```
effective_cost(c) = day_ahead_price_eur_mwh(c) + co2_g_per_kwh(c) × carbon_price_eur_per_tco2 / 1000
```

Day-ahead prices come from the ENTSO-E day-ahead market auction (published the day before for every hour). The default carbon price is **€75/tCO₂**, which approximates the 2026 EU ETS spot. This is configurable per request; setting it to 0 recovers the raw market price.

The carbon term converts: g/kWh × €/t ÷ 1000 = €/MWh. A country emitting 500 g/kWh at €75/t carries an implicit carbon surcharge of €37.50/MWh on top of its market price.

Lower is better.

### 3. Renewable share

**What it measures:** the fraction of total electricity output from variable and firm renewables — wind (onshore and offshore), solar (utility and distributed), hydro (run-of-river and reservoir), geothermal, and biomass.

**Formula:**

```
renewable_share(c) = Σ renewable_GW(c) / total_GW(c)
```

This is electricity-output basis (MWh-delivered), not primary-energy basis. CSS scores on what the compute actually consumes. Primary Energy Factors (PEF, see below) are available as a visualization toggle but are not applied to the CSS.

Higher is better.

### 4. Price stability

**What it measures:** the short-run predictability of electricity costs, expressed as the 24-hour rolling standard deviation of day-ahead prices (€/MWh).

A high σ indicates a volatile grid — driven by weather-dependent renewables with insufficient storage or interconnection, or by demand spikes. A training-workload operator who cannot easily reschedule benefits from a stable price floor.

**Formula:**

```
stability(c) = σ  of  [day_ahead_price_h-23 … day_ahead_price_h]  (€/MWh, rolling 24 h)
```

Lower σ is better; the normalization is flipped.

---

## Normalization

Each dimension is min-max normalized across all countries in the sample at the same hour:

```
score_lower_is_better(v) = 100 × (max − v) / (max − min)
score_higher_is_better(v) = 100 × (v − min) / (max − min)
```

If all countries return the same value (e.g., during a data outage), all scores are set to 50.0 rather than producing a divide-by-zero. Scores are always relative to the current cross-European sample; they move as the mix of countries shifts.

---

## Weight presets

| Preset | Carbon | Cost | Renewable | Stability | Rationale |
|---|---|---|---|---|---|
| Balanced (default) | 40 | 30 | 20 | 10 | Carbon-conscious trainer who still cares about cost |
| Green | 60 | 15 | 20 | 5 | Maximise decarbonization; cost secondary |
| Cost | 10 | 60 | 15 | 15 | Minimise effective spend; carbon secondary |
| Training | 40 | 30 | 20 | 10 | Same as Balanced — training is relocatable |
| Fine-tuning | 30 | 40 | 20 | 10 | Shorter runs; cost sensitivity rises |
| Inference | 20 | 45 | 15 | 20 | Continuous load; stability and cost dominate |

Weights must sum to 100. Custom weights are accepted via the `weights` query parameter (e.g., `weights=50-20-20-10`).

---

## Primary Energy Factors (PEF)

PEF converts electricity output to primary energy input, accounting for conversion losses. The dashboard implements **IEA physical-content convention** values:

| Source | PEF |
|---|---|
| Hard coal | 2.7 |
| Lignite | 3.0 |
| Gas (CCGT) | 2.0 |
| Gas (open-cycle) | 2.5 |
| Oil | 2.6 |
| Peat | 2.9 |
| Nuclear | 3.0 |
| Biomass | 1.2 |
| Waste | 1.1 |
| Wind, solar, hydro, geothermal | 1.0 |

PEF is applied **only** to the generation-mix visualization via an explicit UI toggle ("Electricity output" vs "Primary energy input"). It is not applied to the CSS. Renewable share inside CSS uses electricity-MWh to stay consistent with the other per-kWh-delivered dimensions. Showing PEF in the visualization is useful context for readers familiar with energy statistics; applying it to the score would penalize nuclear and gas more than a compute operator should: they are buying delivered kWh, not primary BTUs.

**Source:** IEA, 2021. *Energy Statistics Manual*. [https://www.iea.org/data-and-statistics/data-tools/energy-statistics-data-browser](https://www.iea.org/data-and-statistics/data-tools/energy-statistics-data-browser)

---

## Forecasting (24 h ahead)

The dashboard shows two forecasts side-by-side and evaluates both against realized values.

**Market forecast** — ENTSO-E publishes the day-ahead auction result for every hour of the next day. For CO₂ intensity, the same process applies: ENTSO-E day-ahead generation-by-source forecast × IPCC emission factors → forecasted g CO₂/kWh. This is the market's own prediction, made by grid operators with full visibility of scheduled generation.

**Naive seasonal baseline** — Same-hour, same-day-of-week mean over the last four weeks. No model. Serves as the evaluation benchmark: if the market forecast does not consistently beat this trivial predictor, we cannot claim the forecast has predictive value.

**Evaluation metric:** MAPE (Mean Absolute Percentage Error), computed over the last 7 full days per country, per metric. Surfaced on the Forecast Accuracy panel. This is the "show your work" signal — a dashboard that displays forecasts without evaluating them is claiming more than it demonstrates.

---

## Inference latency penalty

Training workloads are freely relocatable across Europe; inference is not. A model serving European users from Iceland incurs real latency cost. The dashboard applies a defensible geometric penalty:

```
penalty(c, r) = min(0.4,  max(0,  (dist_km(c, r) − 500) / 2500))
CSS_inference(c) = CSS(c) × (1 − penalty(c, r))
```

Where `r` is the selected serving-region centroid (Central, Western, Northern, Southern, or Iberian Europe) and `c` is the candidate country centroid. Distances are haversine from a fixed table of population-weighted centroids, pre-computed at build time.

The **500 km free zone** reflects realistic EU CDN experience — within ~500 km, latency differences between European datacentre regions are negligible for most inference workloads. The **2500 km slope** means a country at the geographic extreme of the continent loses at most 40 CSS points relative to its raw score. A country cannot be penalized below 60% of its clean-grid score; physical proximity cannot fully override a dramatically cleaner grid.

---

## Time-of-day optimization

Given a 24-hour CO₂ forecast for a country and a desired workload duration of N hours, the optimizer sweeps every contiguous N-hour window in the forecast and identifies the start index that minimizes mean carbon intensity.

**Best-window formula:**

```
best_start = argmin_{i}  mean(co2[i .. i+N])
```

where `co2` is the hourly forecast array (g CO₂/kWh) and the window wraps only within the 24-hour horizon (no wrap-around).

**Savings metrics:**

```
savings_pct  = (worst_avg − best_avg) / worst_avg × 100
kg_avoided   = mw × hours × (worst_avg − best_avg)
```

`worst_avg` is the mean CO₂ of the worst N-hour window; `best_avg` is the mean of the best. Units: `MW × h × (g/kWh)` = `MWh × g/kWh` = `(1000 kWh) × g/kWh` = `1000 g` = **1 kg** — so the product comes out in kg CO₂ directly.

**Caveat:** Real training runs may require a contiguous window longer than 24 hours. The sweep logic generalizes to any forecast horizon, but the dashboard currently publishes only 24-hour ENTSO-E day-ahead forecasts. Longer windows require a multi-day or medium-term forecast that ENTSO-E does not currently expose via the Transparency Platform.

---

## Life-cycle assessment (LCA)

The simulator's **Full LCA** mode decomposes total workload carbon into three components:

### 1. Operational (electricity)

```
operational_kg = mw × hours × co2_g_per_kwh × pue
```

Units check: `MW × h × g/kWh` = `MWh × g/kWh` = `1000 kWh × g/kWh` = `1000 g` = `1 kg`. So the product gives kg CO₂ directly; PUE simply multiplies the result.

`pue` (Power Usage Effectiveness) scales the compute draw to total datacenter power. PUE defaults by region:

| Region | Default PUE |
|---|---|
| Nordic (NO, SE, FI, IS) | 1.10 |
| Northern EU (DK, NL, IE, EE, LV, LT) | 1.20 |
| Central EU (DE, FR, BE, AT, CH, PL, CZ, SK, HU) | 1.25 |
| Southern EU (IT, ES, PT, GR, HR, SI, RO, BG) | 1.40 |
| Island / peripheral (MT, CY) | 1.45 |

### 2. Embodied hardware (GPU manufacturing)

```
gpus_per_mw        = 1 000 / gpu_power_kw
embodied_hw_kg     = gpu_embodied_kg × gpus_per_mw × mw × hours / (life_years × 8760)
```

GPU power draw (`gpu_power_kw`) and embodied CO₂ (`gpu_embodied_kg`) are looked up from the hardware table below. `life_years = 3` (hyperscale / neocloud standard). The formula amortizes total manufacturing emissions linearly over the hardware's service life and allocates the fraction consumed by this workload.

**GPU embodied CO₂ table (kg CO₂e per unit):**

| GPU | Embodied CO₂ (kg) | TDP (W) | Source |
|---|---|---|---|
| A100 80 GB | 900 | 400 | NVIDIA ESG Report; Patterson et al. 2021 |
| H100 SXM | 1,300 | 700 | NVIDIA ESG Report; Patterson et al. 2021 |
| H200 SXM | 1,400 | 700 | NVIDIA ESG Report (estimated) |
| B200 | 1,900 | 1,000 | NVIDIA ESG Report (estimated) |
| MI300X | 1,500 | 750 | AMD Sustainability Filing |
| Groq LPU | 600 | 300 | Groq LCA estimate |

All values carry **±30% uncertainty** — manufacturing process disclosures are incomplete and vary by facility. Treat these as order-of-magnitude anchors, not precise figures.

**Citations:** NVIDIA Corporate Sustainability Reports; Patterson, D. et al. (2021). *Carbon Considerations for Large Language Model Training*. arXiv:2104.10350; AMD 2023 Sustainability Report.

### 3. Embodied datacenter (construction)

```
embodied_dc_kg = 7 × mw × 1 000 × (hours / 8760)
```

The 7 kg CO₂/kW/year factor is the LBNL + industry LCA median for datacenter construction amortized over a 20-year facility life. It covers structural steel, concrete, cooling plant, and power infrastructure but excludes IT equipment (captured in the hardware term above).

**Source:** Lawrence Berkeley National Laboratory, *United States Data Center Energy Usage Report* (2016); industry LCA studies (Uptime Institute, Green Grid).

### Key insight

With clean operational power — France at ~40 g CO₂/kWh — embodied carbon becomes the dominant share. Operational electricity drops to roughly 50% of total lifecycle carbon. **Once the grid is clean enough, hardware manufacturing is where the carbon lives.** This is the core argument for hardware efficiency and longer GPU service lives in low-carbon regions.

---

## Bidding-zone aggregation

ENTSO-E data is organized by bidding zone, not by country. Several countries span multiple zones:

| Country | Bidding zones |
|---|---|
| Norway | NO_1, NO_2, NO_3, NO_4, NO_5 |
| Sweden | SE_1, SE_2, SE_3, SE_4 |
| Denmark | DK_1, DK_2 |
| Italy | IT_North, IT_Centre-North, IT_Centre-South, IT_South, IT_Sardinia, IT_Sicily |
| Germany / Luxembourg | DE_LU |

For multi-zone countries, generation volumes are **summed** across zones and prices are **generation-weighted averaged**. This produces a single country-level metric suitable for the CSS. The DE_LU zone spans two sovereign states; DE is listed as a single country and LU is omitted from the ranking.

Cross-border flow queries use the primary bidding zone only. This is a known simplification: internal zone-to-zone flows within Norway or Sweden are not reflected in the flow web. This is acknowledged in the UI tooltip and does not affect CSS computation.

---

## Caveats and known limitations

1. **Emission factors are lifecycle medians from 2014.** Technology has improved — solar and wind factors have likely decreased. AR5 is used because it is the most widely cited consistent set; AR6 (2022) does not replace the lifecycle annex on a like-for-like basis. Factors should be revisited when the next IPCC technology annex publishes.

2. **Generation mix is real-time; not all sources are reported promptly.** Some small generators report with a delay. ENTSO-E data can be revised. The 15-minute TTL cache means CSS reflects conditions ~15 minutes stale at worst.

3. **Day-ahead prices are not spot prices.** The dashboard uses auction prices, which settle the night before. Intra-day markets and balancing prices can differ materially in volatile conditions.

4. **CSS is relative, not absolute.** A CSS of 80 in summer (when Norway's hydro is full) is not the same as CSS of 80 in winter (when it might not exist). Comparisons across time should use the raw dimension values, not CSS.

5. **Carbon accounting boundary is grid electricity only.** Embodied carbon in datacenter construction, cooling, and hardware manufacturing is excluded. This is standard for operational carbon accounting but understates the full lifecycle impact of a compute decision.

6. **Bidding-zone aggregation hides internal price differences.** The cheapest hour in NO_1 may differ from NO_5. The aggregated Norway price is an approximation.

7. **ENTSO-E day-ahead generation forecast availability varies by country.** Where it is not published, the forecast panel falls back to the naive seasonal baseline and marks the source accordingly.

8. **LCA embodied values carry ±30% uncertainty.** GPU and datacenter manufacturing emissions are derived from incomplete public disclosures. All LCA hardware figures should be treated as order-of-magnitude estimates; the uncertainty band is wide enough that operational and embodied carbon could swap rank for mid-carbon grids.

9. **Time-of-day optimization assumes contiguously interruptible workloads.** The best-window calculation finds the optimal N-hour block in a 24-hour forecast. Real workloads that cannot pause mid-run, or that require checkpointing infrastructure, may not be able to exploit the full savings delta shown.

---

## Citations

- **IPCC AR5 (2014):** IPCC Working Group III, *Climate Change 2014: Mitigation of Climate Change*, Annex II, Table A.III.2 — Lifecycle GHG emission intensities by technology. [https://www.ipcc.ch/report/ar5/wg3/](https://www.ipcc.ch/report/ar5/wg3/)
- **IEA Energy and AI (2025):** IEA, *Energy and AI*, 2025. Datacenter electricity demand projections (415 TWh 2024 → 945 TWh 2030). [https://www.iea.org/reports/energy-and-ai](https://www.iea.org/reports/energy-and-ai)
- **Ember European Electricity Review (2025):** Ember, *European Electricity Review 2025*. Country-level generation mix context. [https://ember-climate.org/insights/research/european-electricity-review-2025/](https://ember-climate.org/insights/research/european-electricity-review-2025/)
- **Eurostat Energy Statistics:** Eurostat, *Energy Statistics — Supply, Transformation, Consumption*. Cross-check for annual generation mix. [https://ec.europa.eu/eurostat/statistics-explained/index.php/Energy_statistics_-_supply,_transformation_and_consumption](https://ec.europa.eu/eurostat/statistics-explained/index.php/Energy_statistics_-_supply,_transformation_and_consumption)
- **IEA Energy Statistics Manual:** IEA, *Energy Statistics Manual*, 2021. Physical-content Primary Energy Factor convention. [https://www.iea.org/data-and-statistics](https://www.iea.org/data-and-statistics)
- **Patterson et al. (2021):** Patterson, D. et al. *Carbon Considerations for Large Language Model Training*. arXiv:2104.10350. GPU embodied carbon and operational carbon methodology.
- **NVIDIA ESG Reports:** NVIDIA Corporation, *Corporate Sustainability / ESG Reports* (2022–2024). GPU product carbon footprint disclosures.
- **AMD Sustainability Filing:** AMD, *2023 Corporate Responsibility Summary*. GPU embodied CO₂ estimates for MI300X-class hardware.
- **LBNL Datacenter Energy Report:** Shehabi, A. et al. *United States Data Center Energy Usage Report*. Lawrence Berkeley National Laboratory, 2016. Datacenter embodied carbon factor (7 kg CO₂/kW/year).
