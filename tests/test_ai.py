from unittest.mock import MagicMock, patch
from app.ai import build_prompt, AIBriefing


def test_build_prompt_contains_country():
    prompt = build_prompt(
        country="Denmark",
        renewable_pct=68.0,
        co2_intensity=115.0,
        price_eur_mwh=78.0,
        sources={"Wind": 55.0, "Gas": 18.0},
        net_gw=0.3,
    )
    assert "Denmark" in prompt
    assert "68" in prompt
    assert "115" in prompt


def test_ai_briefing_returns_text():
    with patch("app.ai.genai") as mock_genai:
        mock_response = MagicMock()
        mock_response.text = "Denmark is running 68% renewables today."
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response

        briefing = AIBriefing(api_key="test")
        result = briefing.generate(
            country="DK",
            country_name="Denmark",
            renewable_pct=68.0,
            co2_intensity=115.0,
            price_eur_mwh=78.0,
            sources={"Wind": 55.0, "Gas": 18.0},
            net_gw=0.3,
        )
    assert "Denmark" in result.text


def test_ai_briefing_fallback_on_error():
    with patch("app.ai.genai") as mock_genai:
        mock_genai.GenerativeModel.return_value.generate_content.side_effect = Exception("API error")
        briefing = AIBriefing(api_key="test")
        result = briefing.generate(
            country="DK", country_name="Denmark",
            renewable_pct=68.0, co2_intensity=115.0, price_eur_mwh=78.0,
            sources={}, net_gw=0.0,
        )
    assert result.text != ""
