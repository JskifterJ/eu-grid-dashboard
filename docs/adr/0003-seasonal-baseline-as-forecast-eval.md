# ADR 0003: Seasonal baseline as the forecast evaluation benchmark

**Status:** Accepted · 2026-04-20
**Deciders:** Johannes Skifter

---

## Context

The dashboard displays a 24 h-ahead forecast of CO₂ intensity and day-ahead electricity price per country, sourced from ENTSO-E. Any dashboard that displays a forecast without evaluating it is making an implicit claim ("this is useful") that it cannot support. The Forecast Accuracy panel is designed to make that claim explicit and testable.

We need to choose an **evaluation benchmark**: what is the forecast being compared against? Options:

1. **No benchmark** — just display MAPE of the market forecast vs realized.
2. **Persistence baseline** — last-observed value carried forward.
3. **Seasonal naive baseline** — same-hour, same-day-of-week mean over the last N weeks.
4. **A trained ML model** (e.g., gradient-boosted regression, LSTM).

The question the panel must answer is: *does the ENTSO-E market forecast contain information beyond what a trivial predictor could achieve?* If not, displaying it as a forecast would be misleading.

---

## Decision

Use the **seasonal naive baseline**: same-hour-of-day, same-day-of-week mean over the **last 4 weeks** of historical data.

Implementation in `app/forecast.py`:
```python
def seasonal_baseline(country: str, target_hour: datetime) -> float:
    """Mean of the same weekday-hour combination across the last 4 matching weeks."""
    ...
```

The Forecast Accuracy panel shows **MAPE side-by-side** for both the market forecast and the seasonal baseline, over the last 7 full days per country. If the market forecast's MAPE is not materially lower than the baseline's, the panel labels it: "market forecast does not significantly outperform naive baseline for this country."

---

## Why this benchmark

**It is the hardest trivially-constructable bar.** Persistence (last hour → next hour) is too easy to beat for prices that revert to a daily pattern. A seasonal naive baseline accounts for both the time-of-day curve and the weekday/weekend structure of electricity demand — the dominant sources of predictability in European grids. Beating it is a meaningful signal.

**It is honest.** For some countries (especially those with high renewable penetration and low interconnection), the market forecast MAPE and the seasonal baseline MAPE are similar. Showing this openly is more credible than hiding it.

**It is reproducible.** The seasonal baseline is deterministic given the historical data. A technical reviewer can verify the MAPE calculation without access to the ENTSO-E API key.

**It is pedagogically useful.** The evaluation panel is a "show your work" section for an applied-AI-engineer audience. Presenting a trivial but honest benchmark, and explaining why it was chosen, demonstrates statistical hygiene — which is more impressive than a lower MAPE from a model whose methodology is opaque.

---

## Consequences

**Positive:**
- Forecast claims are now defensible. The dashboard cannot be criticized for presenting ENTSO-E forecasts as if they were validated predictors.
- The panel doubles as a cross-country comparison: countries where the market forecast adds value (low volatile renewables, stable demand) vs those where it does not.
- No ML dependency. The baseline is a rolling mean over SQLite historicals.

**Negative / tradeoffs:**
- The 4-week window is a design choice, not an optimization. A longer window increases stability; a shorter window tracks seasonality changes faster. 4 weeks was chosen as a round number covering a full month of weekday patterns. This should be noted in the UI.
- MAPE is undefined when the realized value is zero (division-by-zero). In practice, CO₂ intensity is never exactly zero in the current European mix. For price, near-zero and negative prices (which do occur) are handled by falling back to MAE for those hours and flagging the count.

---

## Alternatives considered

| Option | Why rejected |
|---|---|
| **No benchmark** | Does not answer "is the forecast useful?" Cannot claim forecast adds value without a reference point. |
| **Persistence baseline** | Too easy to beat. A forecast that merely repeats the last value will fail against a seasonal naive baseline, but persistence is not the right bar for a 24 h-ahead claim. |
| **ML model (gradient boosting, LSTM)** | Adds model training, versioning, and reproducibility burden. The goal of this panel is to evaluate the market forecast, not to compete with it. A trained model would be competing, not benchmarking. Revisit if the product evolves into providing its own forecasts. |
| **Climatological mean (full history mean)** | Ignores seasonality and day-of-week structure — trivially beaten by any model. Not a fair bar. |
