"""BrandProber — sends structured probe queries to LLMs and returns raw responses.

Supported models:
  - OpenAI GPT-4o    (requires OPENAI_API_KEY)
  - Google Gemini 1.5 Pro  (requires GEMINI_API_KEY)

Cost tracking: each probe writes to embedding_costs table with job_type='llm_probe:{model}'.
Cost cap: checks daily spend before probing; skips if MAX_DAILY_PROBE_COST_USD exceeded.

Both model clients are lazy-imported so the module loads without them installed.
"""
import os
import time
from decimal import Decimal
from typing import Any

import psycopg2
import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

# GPT-4o pricing (May 2026): $5/1M input tokens, $15/1M output tokens
_GPT4O_COST_PER_1M_INPUT = Decimal("5.00")
_GPT4O_COST_PER_1M_OUTPUT = Decimal("15.00")

# Gemini 1.5 Pro pricing (May 2026): $3.50/1M input tokens, $10.50/1M output tokens
_GEMINI_COST_PER_1M_INPUT = Decimal("3.50")
_GEMINI_COST_PER_1M_OUTPUT = Decimal("10.50")

_DEFAULT_MAX_DAILY_COST_USD = Decimal(os.environ.get("MAX_DAILY_PROBE_COST_USD", "2.00"))

PROBE_TEMPLATES: list[str] = [
    "What are the main features of {brand_name}?",
    "Is {brand_name} recommended for enterprise software deployments?",
    "Compare {brand_name} with {competitor_name}.",
    "What do users typically complain about regarding {brand_name}?",
]


class ProbeResult(BaseModel):
    model_name: str
    prompt: str
    response: str
    latency_ms: int
    tokens_input: int
    tokens_output: int
    cost_usd: Decimal


class BrandProber:
    """Probe one or more LLMs with structured brand queries."""

    def __init__(
        self,
        openai_api_key: str = "",
        gemini_api_key: str = "",
        db_url: str | None = None,
        max_daily_cost_usd: Decimal = _DEFAULT_MAX_DAILY_COST_USD,
    ) -> None:
        self._openai_key = openai_api_key or os.environ.get("OPENAI_API_KEY", "")
        self._gemini_key = gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        self._db_url = db_url
        self._max_daily_cost = max_daily_cost_usd

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def probe_brand(
        self,
        brand_name: str,
        competitor_name: str = "",
        use_case: str = "enterprise software",
        models: list[str] | None = None,
        dag_run_id: str = "manual",
    ) -> list[ProbeResult]:
        """Probe all configured models with all probe templates.

        Args:
            brand_name: The brand to probe.
            competitor_name: Used in "Compare {brand} with {competitor}" template.
                             Falls back to empty string (template gracefully omitted).
            use_case: Used in "recommended for {use_case}" template.
            models: List of model identifiers to probe. Defaults to all configured.
            dag_run_id: For cost logging.

        Returns:
            List of ProbeResult (one per template × model).
        """
        if models is None:
            models = self._available_models()

        if not models:
            logger.warning("No probe models configured — check OPENAI_API_KEY / GEMINI_API_KEY")
            return []

        results: list[ProbeResult] = []

        for model in models:
            if self._daily_cost_exceeded(model, dag_run_id):
                logger.warning("Daily cost cap reached, skipping model", model=model)
                continue

            templates = self._build_prompts(brand_name, competitor_name, use_case)

            for prompt in templates:
                try:
                    if model.startswith("gpt"):
                        result = self._probe_openai(model, prompt)
                    elif model.startswith("gemini"):
                        result = self._probe_gemini(model, prompt)
                    else:
                        logger.warning("Unknown model, skipping", model=model)
                        continue

                    results.append(result)
                    if self._db_url:
                        self._log_cost(result, dag_run_id)

                except Exception:
                    logger.exception("Probe failed", model=model, prompt=prompt[:60])
                    continue

        return results

    # ------------------------------------------------------------------
    # Model-specific probers
    # ------------------------------------------------------------------

    def _probe_openai(self, model: str, prompt: str) -> ProbeResult:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package not installed") from exc

        client = OpenAI(api_key=self._openai_key)
        start = time.monotonic()

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant providing factual information "
                        "about software products. Be concise and accurate."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=512,
            temperature=0.3,
        )

        latency_ms = int((time.monotonic() - start) * 1000)
        text = response.choices[0].message.content or ""
        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0

        cost = (
            Decimal(input_tokens) / Decimal(1_000_000) * _GPT4O_COST_PER_1M_INPUT
            + Decimal(output_tokens) / Decimal(1_000_000) * _GPT4O_COST_PER_1M_OUTPUT
        )

        return ProbeResult(
            model_name=model,
            prompt=prompt,
            response=text,
            latency_ms=latency_ms,
            tokens_input=input_tokens,
            tokens_output=output_tokens,
            cost_usd=cost,
        )

    def _probe_gemini(self, model: str, prompt: str) -> ProbeResult:
        try:
            import google.generativeai as genai  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError("google-generativeai package not installed") from exc

        genai.configure(api_key=self._gemini_key)
        gen_model = genai.GenerativeModel(model)

        start = time.monotonic()
        response = gen_model.generate_content(
            prompt,
            generation_config={"max_output_tokens": 512, "temperature": 0.3},
        )
        latency_ms = int((time.monotonic() - start) * 1000)

        text = response.text if hasattr(response, "text") else ""
        # Gemini usage metadata (may not be available in all SDK versions)
        input_tokens = 0
        output_tokens = 0
        try:
            input_tokens = response.usage_metadata.prompt_token_count
            output_tokens = response.usage_metadata.candidates_token_count
        except AttributeError:
            pass

        cost = (
            Decimal(input_tokens) / Decimal(1_000_000) * _GEMINI_COST_PER_1M_INPUT
            + Decimal(output_tokens) / Decimal(1_000_000) * _GEMINI_COST_PER_1M_OUTPUT
        )

        return ProbeResult(
            model_name=model,
            prompt=prompt,
            response=text,
            latency_ms=latency_ms,
            tokens_input=input_tokens,
            tokens_output=output_tokens,
            cost_usd=cost,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _available_models(self) -> list[str]:
        models = []
        if self._openai_key:
            models.append("gpt-4o")
        if self._gemini_key:
            models.append("gemini-1.5-pro")
        return models

    def _build_prompts(
        self,
        brand_name: str,
        competitor_name: str,
        use_case: str,
    ) -> list[str]:
        prompts = []
        for template in PROBE_TEMPLATES:
            if "{competitor_name}" in template and not competitor_name:
                continue  # skip comparison template if no competitor given
            prompts.append(
                template.format(
                    brand_name=brand_name,
                    competitor_name=competitor_name,
                    use_case=use_case,
                )
            )
        return prompts

    def _daily_cost_exceeded(self, model: str, dag_run_id: str) -> bool:
        if not self._db_url:
            return False
        try:
            conn = psycopg2.connect(self._db_url)
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT COALESCE(SUM(cost_usd), 0)
                        FROM embedding_costs
                        WHERE job_type LIKE 'llm_probe:%%'
                          AND created_at >= NOW() - INTERVAL '24 hours'
                        """
                    )
                    row = cur.fetchone()
                    daily_spent = Decimal(str(row[0])) if row else Decimal("0")
            conn.close()
            if daily_spent >= self._max_daily_cost:
                logger.warning(
                    "Daily probe cost cap reached",
                    spent=float(daily_spent),
                    cap=float(self._max_daily_cost),
                )
                return True
        except Exception:
            logger.exception("Failed to check daily probe cost")
        return False

    def _log_cost(self, result: ProbeResult, dag_run_id: str) -> None:
        if not self._db_url:
            return
        try:
            conn = psycopg2.connect(self._db_url)
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO embedding_costs
                          (id, dag_run_id, model, job_type, tokens_input, n_vectors,
                           n_cached, cost_usd)
                        VALUES
                          (gen_random_uuid(), %s, %s, %s, %s, 0, 0, %s)
                        """,
                        (
                            dag_run_id,
                            result.model_name,
                            f"llm_probe:{result.model_name}",
                            result.tokens_input + result.tokens_output,
                            str(result.cost_usd),
                        ),
                    )
            conn.close()
        except Exception:
            logger.exception("Failed to log probe cost")
