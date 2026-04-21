"""
Structured AI briefing with pragmatic pull-quote RAG.
Returns a pydantic-validated StructuredBriefing rather than free text.
"""
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import google.generativeai as genai

from app.models import StructuredBriefing

logger = logging.getLogger(__name__)

_QUOTES_PATH = Path(__file__).parent.parent / "frontend" / "strategic_quotes.json"


def load_strategic_quotes() -> list[dict]:
    """Load the curated pull-quote JSON. Returns [] on failure."""
    try:
        with _QUOTES_PATH.open() as f:
            return json.load(f).get("cards", [])
    except Exception as e:
        logger.warning("could not load strategic quotes: %s", e)
        return []


def pick_relevant_quotes(
    carbon_score: float,
    cost_score: float,
    renewable_score: float,
    stability_score: float,
    workload: str,
    quotes: list[dict],
    max_n: int = 2,
) -> list[dict]:
    """
    Rule-based relevance. Score each quote by tag match to the current situation;
    return the top-N. Deterministic and inspectable — no vectors.
    """
    if not quotes:
        return []

    def score(q: dict) -> int:
        tags = set(q.get("tags", []))
        s = 0
        # Workload affinity
        if workload in tags:
            s += 3
        # Cost/renewable/carbon signals
        if cost_score < 40 and "macro" in tags:    s += 2       # expensive markets — macro framing
        if carbon_score < 40 and "siting" in tags: s += 2       # dirty grid — siting urgency
        if renewable_score > 70 and "strategy" in tags: s += 2  # renewable leader — strategic framing
        if stability_score < 40 and "hardware" in tags: s += 1  # unstable pricing — hardware economics
        # Baseline inference affinity for inference mode
        if workload == "inference" and "inference" in tags: s += 1
        # Baseline training affinity
        if workload in ("training", "fine-tuning") and "training" in tags: s += 1
        return s

    ranked = sorted(quotes, key=score, reverse=True)
    picked = []
    seen_ids = set()
    for q in ranked:
        if q["id"] in seen_ids:
            continue
        picked.append(q)
        seen_ids.add(q["id"])
        if len(picked) >= max_n:
            break
    # Ensure at least one quote comes back even for low-signal inputs
    if not picked and quotes:
        picked = [quotes[0]]
    return picked


def build_briefing_prompt(
    country: str,
    country_name: str,
    co2_g_per_kwh: float,
    price_eur_mwh: float,
    renewable_pct: float,
    css: float,
    workload: str,
    quotes: list[dict],
) -> str:
    quote_block = "\n\n".join(
        f"STRATEGIC CONTEXT ({q['source']}):\n"
        f"  {q['quote']}"
        for q in quotes
    ) if quotes else "(no strategic context selected)"

    return (
        "You are a concise energy-and-AI analyst. Output MUST be valid JSON with keys "
        "headline (string, \u226490 chars), bullets (array of EXACTLY 3 strings, each \u2264160 chars), "
        "risk_flag ('low' | 'med' | 'high').\n\n"
        f"Live situation \u2014 country {country_name} ({country}):\n"
        f"  CO\u2082 intensity: {co2_g_per_kwh:.0f} g/kWh\n"
        f"  Day-ahead price: \u20ac{price_eur_mwh:.0f}/MWh\n"
        f"  Renewable share: {renewable_pct:.0f}%\n"
        f"  Compute Siting Score: {css:.0f} / 100\n"
        f"  Workload context: {workload}\n\n"
        f"{quote_block}\n\n"
        "Write as an analyst: specific numbers, one concrete strategic implication per bullet. "
        "risk_flag = low if CSS \u2265 70 (site here happily); med if 40\u201370 (tradeoffs); "
        "high if < 40 (avoid unless forced). No preamble; JSON only."
    )


def _fallback_briefing(
    country: str, country_name: str, co2_g_per_kwh: float, price_eur_mwh: float,
    renewable_pct: float, css: float, workload: str,
) -> StructuredBriefing:
    """Deterministic fallback when Gemini is unavailable."""
    if css >= 70:
        risk = "low"
        h = f"{country_name} is a strong {workload} site right now (CSS {css:.0f})."
    elif css >= 40:
        risk = "med"
        h = f"{country_name} is middle-of-the-pack for {workload} today (CSS {css:.0f})."
    else:
        risk = "high"
        h = f"{country_name} is a poor {workload} site right now (CSS {css:.0f})."

    bullets = [
        f"Grid intensity is {co2_g_per_kwh:.0f} g CO\u2082/kWh with {renewable_pct:.0f}% renewable share.",
        f"Day-ahead price sits at \u20ac{price_eur_mwh:.0f}/MWh.",
        f"Workload context: {workload} \u2014 CSS rank reflects the weight profile for this mode.",
    ]
    return StructuredBriefing(
        country=country,
        headline=h,
        bullets=bullets,
        risk_flag=risk,  # type: ignore[arg-type]
        as_of=datetime.now(timezone.utc).isoformat(),
        sources=["ENTSO-E day-ahead", "app/scoring.py", "mock fallback"],
    )


def get_structured_briefing(
    country: str,
    country_name: str,
    co2_g_per_kwh: float,
    price_eur_mwh: float,
    renewable_pct: float,
    css: float,
    workload: str = "training",
) -> StructuredBriefing:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    quotes = load_strategic_quotes()
    picked = pick_relevant_quotes(
        carbon_score=min(100.0, max(0.0, (1000.0 - co2_g_per_kwh) / 10.0)),  # rough proxy
        cost_score=min(100.0, max(0.0, (200.0 - price_eur_mwh) / 2.0)),
        renewable_score=renewable_pct,
        stability_score=50.0,
        workload=workload,
        quotes=quotes,
    )
    if not key:
        return _fallback_briefing(country, country_name, co2_g_per_kwh, price_eur_mwh, renewable_pct, css, workload)

    prompt = build_briefing_prompt(
        country=country, country_name=country_name,
        co2_g_per_kwh=co2_g_per_kwh, price_eur_mwh=price_eur_mwh,
        renewable_pct=renewable_pct, css=css, workload=workload, quotes=picked,
    )
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(
            prompt,
            generation_config={
                "max_output_tokens": 500,
                "temperature": 0.3,
                "response_mime_type": "application/json",
            },
        )
        parsed = json.loads(response.text)
        headline = parsed.get("headline", "").strip() or "Grid snapshot unavailable."
        bullets_raw = parsed.get("bullets", [])
        bullets = [str(b).strip() for b in bullets_raw][:3]
        while len(bullets) < 3:
            bullets.append("(no additional data)")
        risk = parsed.get("risk_flag", "med")
        if risk not in ("low", "med", "high"):
            risk = "med"
        sources = ["ENTSO-E day-ahead", "Gemini 2.0 Flash"] + [q["source"] for q in picked]
        return StructuredBriefing(
            country=country,
            headline=headline,
            bullets=bullets,
            risk_flag=risk,  # type: ignore[arg-type]
            as_of=datetime.now(timezone.utc).isoformat(),
            sources=sources,
        )
    except Exception as e:
        logger.warning("structured briefing fallback: %s", e)
        return _fallback_briefing(country, country_name, co2_g_per_kwh, price_eur_mwh, renewable_pct, css, workload)
