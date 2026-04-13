import os
from datetime import datetime, timezone

import google.generativeai as genai

from app.models import GridSummary


def build_prompt(
    country: str,
    renewable_pct: float,
    co2_intensity: float,
    price_eur_mwh: float,
    sources: dict[str, float],
    net_gw: float,
) -> str:
    top_sources = sorted(sources.items(), key=lambda x: x[1], reverse=True)[:4]
    sources_str = ", ".join(f"{name} {pct:.0f}%" for name, pct in top_sources)
    net_label = f"net exporting {abs(net_gw):.1f} GW" if net_gw > 0 else f"net importing {abs(net_gw):.1f} GW"

    return f"""You are a concise energy analyst. Write exactly one paragraph (3-4 sentences) summarising current grid conditions for {country}.

Data (right now):
- Generation mix: {sources_str}
- Renewable share: {renewable_pct:.1f}%
- CO₂ intensity: {co2_intensity:.0f} g/kWh
- Day-ahead price: €{price_eur_mwh:.0f}/MWh
- Cross-border: {net_label}

Write in plain English. Be specific about the numbers. Note anything unusual or interesting. No bullet points, no headers — one paragraph only."""


class AIBriefing:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel("gemini-2.0-flash")

    def generate(
        self,
        country: str,
        country_name: str,
        renewable_pct: float,
        co2_intensity: float,
        price_eur_mwh: float,
        sources: dict[str, float],
        net_gw: float,
    ) -> GridSummary:
        prompt = build_prompt(
            country=country_name,
            renewable_pct=renewable_pct,
            co2_intensity=co2_intensity,
            price_eur_mwh=price_eur_mwh,
            sources=sources,
            net_gw=net_gw,
        )
        try:
            response = self._model.generate_content(
                prompt,
                generation_config={"max_output_tokens": 300, "temperature": 0.4},
            )
            text = response.text.strip()
        except Exception:
            text = f"{country_name} grid data is currently available. Renewable share: {renewable_pct:.0f}%, CO₂ intensity: {co2_intensity:.0f} g/kWh, price: €{price_eur_mwh:.0f}/MWh."

        return GridSummary(
            country=country,
            text=text,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )


def get_ai_briefing() -> AIBriefing:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    return AIBriefing(api_key=api_key)
