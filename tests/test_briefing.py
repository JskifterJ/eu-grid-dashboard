import pytest
from unittest.mock import patch, MagicMock

from app.briefing import (
    build_briefing_prompt, pick_relevant_quotes, get_structured_briefing, load_strategic_quotes,
)
from app.models import StructuredBriefing


def test_load_strategic_quotes_returns_list():
    quotes = load_strategic_quotes()
    assert isinstance(quotes, list)
    assert len(quotes) >= 3
    for q in quotes:
        assert "id" in q and "tags" in q


def test_pick_relevant_quotes_high_carbon():
    # High carbon score (clean grid) → shouldn't pair with "h100-flood" but "datacenter-demand"/"power-constraint"
    quotes = load_strategic_quotes()
    picked = pick_relevant_quotes(
        carbon_score=95.0, cost_score=70.0, renewable_score=80.0,
        stability_score=70.0, workload="training", quotes=quotes,
    )
    assert 1 <= len(picked) <= 2


def test_pick_relevant_quotes_inference_workload_prefers_inference_tag():
    quotes = load_strategic_quotes()
    picked = pick_relevant_quotes(
        carbon_score=50.0, cost_score=50.0, renewable_score=50.0,
        stability_score=50.0, workload="inference", quotes=quotes,
    )
    # At least one picked quote has "inference" in tags
    assert any("inference" in q["tags"] for q in picked)


def test_build_briefing_prompt_includes_country_and_numbers():
    quotes = load_strategic_quotes()[:1]
    prompt = build_briefing_prompt(
        country="FR", country_name="France",
        co2_g_per_kwh=45.0, price_eur_mwh=72.0, renewable_pct=88.0,
        css=94.0, workload="training", quotes=quotes,
    )
    assert "France" in prompt
    assert "45" in prompt
    assert "72" in prompt
    assert "94" in prompt


def test_structured_briefing_fallback_when_no_key():
    with patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
        result = get_structured_briefing(
            country="FR", country_name="France",
            co2_g_per_kwh=45.0, price_eur_mwh=72.0, renewable_pct=88.0,
            css=94.0, workload="training",
        )
    assert isinstance(result, StructuredBriefing)
    assert result.country == "FR"
    assert len(result.bullets) == 3
    assert result.risk_flag in {"low", "med", "high"}
    assert len(result.sources) >= 1


def test_structured_briefing_mocked_gemini_success():
    import json as _json
    mock_response = MagicMock()
    mock_response.text = _json.dumps({
        "headline": "France grid running clean at 45 g CO₂/kWh.",
        "bullets": [
            "Nuclear + hydro keep intensity near the European floor.",
            "€72/MWh is mid-pack; French pricing has low intra-day σ.",
            "CSS 94 — top-3 in Europe right now for training siting.",
        ],
        "risk_flag": "low",
    })
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key"}):
        with patch("app.briefing.genai.GenerativeModel") as mock_model:
            mock_instance = MagicMock()
            mock_instance.generate_content.return_value = mock_response
            mock_model.return_value = mock_instance

            result = get_structured_briefing(
                country="FR", country_name="France",
                co2_g_per_kwh=45.0, price_eur_mwh=72.0, renewable_pct=88.0,
                css=94.0, workload="training",
            )
    assert result.country == "FR"
    assert "clean" in result.headline.lower()
    assert len(result.bullets) == 3
    assert result.risk_flag == "low"
