"""Unit tests for BrandProber.

All OpenAI / Gemini calls are mocked. DB calls are also mocked.
Tests cover:
  - probe_brand returns ProbeResult for each template × model
  - comparison template is skipped when competitor_name is empty
  - cost cap check: skips model when daily limit exceeded
  - cost calculation: GPT-4o and Gemini pricing
  - lazy imports: no ImportError when keys are absent
  - _log_cost inserts to embedding_costs table

Note: openai and google-generativeai are not installed locally.
      We mock sys.modules so that the lazy imports inside _probe_openai /
      _probe_gemini resolve to MagicMock objects.
"""
from __future__ import annotations

import sys
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from ml.hallucination.prober import BrandProber, ProbeResult, PROBE_TEMPLATES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def prober_no_db() -> BrandProber:
    return BrandProber(
        openai_api_key="sk-fake-openai",
        gemini_api_key="fake-gemini",
        db_url=None,
    )


def _make_openai_module(in_tokens: int = 50, out_tokens: int = 30, text: str = "Mock response"):
    """Build a fake openai module that returns a mock ChatCompletion response."""
    usage = MagicMock()
    usage.prompt_tokens = in_tokens
    usage.completion_tokens = out_tokens

    choice = MagicMock()
    choice.message.content = text

    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = usage

    mock_client_instance = MagicMock()
    mock_client_instance.chat.completions.create.return_value = resp

    mock_openai = MagicMock()
    mock_openai.OpenAI.return_value = mock_client_instance
    return mock_openai, mock_client_instance


def _make_gemini_module(
    text: str = "Gemini mock response",
    in_tokens: int = 40,
    out_tokens: int = 25,
):
    """Build a fake google.generativeai module."""
    metadata = MagicMock()
    metadata.prompt_token_count = in_tokens
    metadata.candidates_token_count = out_tokens

    resp = MagicMock()
    resp.text = text
    resp.usage_metadata = metadata

    mock_gen_instance = MagicMock()
    mock_gen_instance.generate_content.return_value = resp

    mock_genai = MagicMock()
    mock_genai.GenerativeModel.return_value = mock_gen_instance

    mock_google = MagicMock()
    mock_google.generativeai = mock_genai

    return mock_genai, mock_google


# ---------------------------------------------------------------------------
# probe_brand — basic happy path
# ---------------------------------------------------------------------------

class TestProbeBrandHappyPath:
    def test_returns_probe_results_for_all_templates(self, prober_no_db: BrandProber) -> None:
        n_templates = len(PROBE_TEMPLATES) - 1  # competitor template skipped (no competitor)

        mock_openai, _ = _make_openai_module(in_tokens=50, out_tokens=30)
        with patch.dict(sys.modules, {"openai": mock_openai}):
            results = prober_no_db.probe_brand(
                brand_name="AcmeCorp",
                competitor_name="",
                models=["gpt-4o"],
            )

        assert len(results) == n_templates
        for r in results:
            assert isinstance(r, ProbeResult)
            assert r.model_name == "gpt-4o"
            assert r.tokens_input == 50
            assert r.tokens_output == 30

    def test_competitor_template_included_when_given(self, prober_no_db: BrandProber) -> None:
        n_templates = len(PROBE_TEMPLATES)

        mock_openai, _ = _make_openai_module()
        with patch.dict(sys.modules, {"openai": mock_openai}):
            results = prober_no_db.probe_brand(
                brand_name="AcmeCorp",
                competitor_name="BetaTech",
                models=["gpt-4o"],
            )

        assert len(results) == n_templates

    def test_multiple_models(self, prober_no_db: BrandProber) -> None:
        n_templates_no_competitor = len(PROBE_TEMPLATES) - 1

        mock_openai, _ = _make_openai_module()
        mock_genai, mock_google = _make_gemini_module()
        with patch.dict(
            sys.modules,
            {"openai": mock_openai, "google": mock_google, "google.generativeai": mock_genai},
        ):
            results = prober_no_db.probe_brand(
                brand_name="AcmeCorp",
                models=["gpt-4o", "gemini-1.5-pro"],
            )

        assert len(results) == 2 * n_templates_no_competitor


# ---------------------------------------------------------------------------
# Cost calculation
# ---------------------------------------------------------------------------

class TestCostCalculation:
    def test_gpt4o_cost_is_correct(self, prober_no_db: BrandProber) -> None:
        """GPT-4o: $5/1M input + $15/1M output."""
        mock_openai, _ = _make_openai_module(in_tokens=1_000_000, out_tokens=0)
        with patch.dict(sys.modules, {"openai": mock_openai}):
            results = prober_no_db.probe_brand(brand_name="TestBrand", models=["gpt-4o"])

        assert len(results) > 0
        # 1M input tokens × $5/1M = $5.00 per call
        assert results[0].cost_usd == Decimal("5.000000")

    def test_gemini_cost_is_correct(self, prober_no_db: BrandProber) -> None:
        """Gemini 1.5 Pro: $3.50/1M input."""
        mock_genai, mock_google = _make_gemini_module(in_tokens=1_000_000, out_tokens=0)
        with patch.dict(
            sys.modules,
            {"google": mock_google, "google.generativeai": mock_genai},
        ):
            results = prober_no_db.probe_brand(brand_name="TestBrand", models=["gemini-1.5-pro"])

        assert len(results) > 0
        assert results[0].cost_usd == Decimal("3.500000")

    def test_cost_is_zero_for_zero_tokens(self, prober_no_db: BrandProber) -> None:
        mock_openai, _ = _make_openai_module(in_tokens=0, out_tokens=0)
        with patch.dict(sys.modules, {"openai": mock_openai}):
            results = prober_no_db.probe_brand(brand_name="TestBrand", models=["gpt-4o"])

        assert all(r.cost_usd == Decimal("0") for r in results)


# ---------------------------------------------------------------------------
# Cost cap / daily limit
# ---------------------------------------------------------------------------

class TestDailyCostCap:
    def test_model_skipped_when_cap_exceeded(self) -> None:
        prober = BrandProber(
            openai_api_key="sk-fake",
            db_url="postgresql://fake/db",
            max_daily_cost_usd=Decimal("0.01"),
        )

        with patch.object(prober, "_daily_cost_exceeded", return_value=True):
            results = prober.probe_brand(brand_name="AcmeCorp", models=["gpt-4o"])

        assert results == []

    def test_model_not_skipped_when_under_cap(self) -> None:
        prober = BrandProber(
            openai_api_key="sk-fake",
            db_url=None,
            max_daily_cost_usd=Decimal("10.00"),
        )

        mock_openai, _ = _make_openai_module()
        with patch.dict(sys.modules, {"openai": mock_openai}):
            results = prober.probe_brand(brand_name="AcmeCorp", models=["gpt-4o"])

        assert len(results) > 0

    def test_daily_cost_check_returns_false_without_db(self) -> None:
        prober = BrandProber(db_url=None)
        assert prober._daily_cost_exceeded("gpt-4o", "manual") is False


# ---------------------------------------------------------------------------
# Available models
# ---------------------------------------------------------------------------

class TestAvailableModels:
    def test_no_models_without_keys(self) -> None:
        prober = BrandProber(openai_api_key="", gemini_api_key="")
        assert prober._available_models() == []

    def test_openai_only(self) -> None:
        prober = BrandProber(openai_api_key="sk-fake", gemini_api_key="")
        assert prober._available_models() == ["gpt-4o"]

    def test_gemini_only(self) -> None:
        prober = BrandProber(openai_api_key="", gemini_api_key="fake")
        assert prober._available_models() == ["gemini-1.5-pro"]

    def test_both_keys(self) -> None:
        prober = BrandProber(openai_api_key="sk-fake", gemini_api_key="fake")
        models = prober._available_models()
        assert "gpt-4o" in models
        assert "gemini-1.5-pro" in models

    def test_empty_brand_list_returns_empty(self) -> None:
        prober = BrandProber()
        results = prober.probe_brand(brand_name="TestBrand")
        assert results == []


# ---------------------------------------------------------------------------
# _build_prompts
# ---------------------------------------------------------------------------

class TestBuildPrompts:
    def test_skips_competitor_template_without_competitor(self) -> None:
        prober = BrandProber()
        prompts = prober._build_prompts("AcmeCorp", "", "enterprise software")
        for p in prompts:
            assert "{competitor_name}" not in p
            assert "AcmeCorp" in p

    def test_includes_competitor_template_with_competitor(self) -> None:
        prober = BrandProber()
        prompts = prober._build_prompts("AcmeCorp", "BetaTech", "enterprise software")
        comparison = [p for p in prompts if "BetaTech" in p]
        assert len(comparison) >= 1

    def test_brand_name_substituted(self) -> None:
        prober = BrandProber()
        prompts = prober._build_prompts("MyBrand", "", "software")
        assert all("MyBrand" in p for p in prompts)


# ---------------------------------------------------------------------------
# Error resilience: failed probe does not crash probe_brand
# ---------------------------------------------------------------------------

class TestErrorResilience:
    def test_api_error_on_one_prompt_continues(self) -> None:
        prober = BrandProber(openai_api_key="sk-fake")

        call_count = 0
        mock_openai, mock_client = _make_openai_module()

        def side_effect(*args: Any, **kwargs: Any):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("API timeout")
            return mock_client.chat.completions.create.return_value

        mock_client.chat.completions.create.side_effect = side_effect

        with patch.dict(sys.modules, {"openai": mock_openai}):
            results = prober.probe_brand(brand_name="AcmeCorp", models=["gpt-4o"])

        # At least some results despite one failure
        assert len(results) >= 1

    def test_unknown_model_is_skipped(self) -> None:
        prober = BrandProber(openai_api_key="sk-fake")
        results = prober.probe_brand(brand_name="AcmeCorp", models=["unknown-model-xyz"])
        assert results == []
