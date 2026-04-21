# EU Grid Dashboard

> **Where in Europe should AI compute run — right now? The answer changes every hour.**

An opinionated, live dashboard that scores 35 European countries on a **Compute Siting Score (CSS)** combining carbon intensity, cost, renewable share, and price stability, then lets you simulate a training or inference workload against today's grid conditions — **including when to run it and its full lifecycle carbon**.

**Live data** via the ENTSO-E Transparency Platform. **IPCC AR5** emission factors. **EU ETS** carbon price internalized into the cost dimension. **Per-country latency penalty** for inference workloads. **Shareable URL permalinks** for every scenario.

[Open the live dashboard →](https://eu-grid-dashboard.onrender.com) _(check `render.yaml` for the exact service name)_

---

## The thesis in one paragraph

Europe's electricity mix decarbonizes unevenly — France runs nuclear-clean around the clock, Norway is almost entirely hydro, Poland still burns coal, Germany tracks the wind. AI compute is a massive, relocatable, price-sensitive new load — precisely the kind that can chase clean electrons. The optimal *where and when* for a training run shifts hourly; inference siting is tightly bound by user latency. This dashboard proves it by scoring European countries live, letting you simulate a workload, and connecting to the strategic backdrop in the [gpu_industry](https://github.com/jskifterj/gpu_industry) repository.

## Architecture

- **Backend**: FastAPI + pydantic v2 + pandas, Python 3.11 (Render).
- **Frontend**: Vanilla JS + D3 v7 (choropleth + flow web) + Chart.js 4 (forecast lines). No build step.
- **Data sources**: ENTSO-E Transparency Platform (generation, prices, day-ahead forecast, cross-border flows). IPCC AR5 lifecycle emission factors. IEA physical-content Primary Energy Factors.
- **Storage**: On-disk SQLite for historicals (immutable once written); in-memory TTL cache for hot-path queries.
- **AI**: Gemini 2.0 Flash with `response_mime_type=application/json` for structured analyst briefings. Pragmatic pull-quote RAG over `gpu_industry` (rule-based tag matching, no vector DB).

See [docs/methodology.md](docs/methodology.md) for the full CSS formula and data-source citations.
See [docs/adr/](docs/adr/) for the architecture decision records.

## Run locally

```bash
git clone <repo-url>
cd eu-grid-dashboard
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# With live data:
export ENTSO_API_KEY="your-entsoe-key"    # https://transparency.entsoe.eu
export GEMINI_API_KEY="your-gemini-key"   # https://ai.google.dev  (optional — mock briefing if unset)

uvicorn app.main:app --reload --port 8001
```

Open <http://localhost:8001/>.

Without `ENTSO_API_KEY` the app runs in **demo mode** with realistic mock data — useful for development and review.

## Run tests

```bash
pytest tests/ -v
```

## Key endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/ranking?workload=training&weights=balanced` | All countries sorted by CSS |
| `GET /api/css?country=FR&workload=inference&region=western` | One country's CSS breakdown |
| `GET /api/simulate?country=FR&mw=10&hours=6&workload=training` | Emissions + cost for a workload |
| `GET /api/forecast?country=FR` | 24 h CO₂ + price forecast |
| `GET /api/eval?country=FR&metric=co2` | MAPE of market forecast vs naive baseline |
| `GET /api/briefing?country=FR&workload=training` | Structured analyst note (headline + 3 bullets + risk flag) |
| `GET /api/time-of-day?country=FR&hours=6` | Best/worst 6-hour window in the 24 h forecast; savings delta |
| `GET /api/lca?country=FR&mw=10&hours=6&hardware=H100` | Full lifecycle CO₂: operational + embodied hardware + embodied datacenter |

## What this demonstrates

This is a deliberate portfolio piece for **solutions-engineer, product management, and applied-AI-engineer** roles:

- **Product thinking**: opinionated design — the dashboard takes a position, doesn't just report numbers.
- **Technical fluency**: live data integration, multi-source aggregation (multi-zone bidding zones), caching, structured API, deployed on Render.
- **Applied AI**: structured Gemini output, pragmatic RAG over curated pull-quotes, forecast evaluation against a naive baseline.
- **Domain credibility**: IPCC AR5 citations, IEA PEF conventions, EU ETS carbon pricing, bidding-zone caveats acknowledged and footnoted.
- **LCA literacy**: operational CO₂ is one piece; full lifecycle includes embodied hardware (GPU manufacturing, amortized) and datacenter buildout.
- **Narrative**: ties to `gpu_industry` strategic analysis — the dashboard is the operational layer; the analysis is the strategic layer.

## Decision-support features

Three features added in Plan C turn the dashboard from a scoring tool into an actionable decision layer:

- **Time-of-day optimization**: given a 24 h CO₂ forecast and a workload duration, the simulator sweeps every window and surfaces the best and worst start times — with a savings-delta in kg CO₂ and percentage.
- **Deferred batch economics**: a product-concept panel illustrating what an off-peak inference tier could look like — the avoided-carbon and cost case for scheduling interruptible workloads outside peak-demand windows.
- **Full lifecycle carbon (LCA)**: an Operational / Full-LCA toggle and hardware selector (A100, H100, H200, B200, MI300X, Groq-LPU) that breaks total carbon into three components — operational electricity, embodied hardware (GPU manufacturing amortized over service life), and embodied datacenter buildout.

## Author

[Johannes Skifter](https://jskifterj.github.io) · Chief of Staff, Impossible Cloud · jskifter@icn.global

## License

MIT
