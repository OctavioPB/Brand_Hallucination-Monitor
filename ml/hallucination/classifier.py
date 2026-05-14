"""HallucinationClassifier — detects false, confused, and drifted LLM responses.

Three detection mechanisms:
  1. false_attribute  — cosine_sim(response_embedding, false_attr_embedding) > threshold
  2. competitor_confusion — competitor name in positive-sentiment sentence
  3. regulatory_claim — regulatory claim keyword found verbatim in response
  4. sentiment_drift — VADER compound < threshold on full response

Severity:
  CRITICAL  similarity > 0.92, OR regulatory claim in avoid list
  HIGH      similarity 0.82–0.92, OR competitor confusion in positive context
  MEDIUM    competitor confusion in neutral context, OR sentiment drift
  LOW       similarity 0.75–0.82

Design: embedding calls are isolated in _embed_texts() for easy mocking in tests.
"""
import re
from typing import Any

import structlog
from pydantic import BaseModel, Field

from apps.api.models.brand import BrandManifest

logger = structlog.get_logger(__name__)

# Cosine similarity thresholds for false-attribute detection
_CRITICAL_THRESHOLD = 0.92
_HIGH_THRESHOLD = 0.82
_LOW_THRESHOLD = 0.75

# VADER compound score boundaries
_POSITIVE_VADER = 0.05
_NEGATIVE_VADER = -0.05
_CONFUSION_POSITIVE_VADER = 0.10  # competitor mentioned in positive sentence

_SEVERITY_RANK = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


class HallucinationResult(BaseModel):
    hallucination_type: str  # false_attribute | competitor_confusion | regulatory_claim | sentiment_drift
    severity: str            # LOW | MEDIUM | HIGH | CRITICAL
    attribute_slug: str
    attribute_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_snippet: str    # sentence or phrase that triggered the detection
    model_name: str


class HallucinationClassifier:
    """Classify a single LLM response for hallucinations against a BrandManifest."""

    def classify(
        self,
        response_text: str,
        manifest: BrandManifest,
        brand_name: str,
        model_name: str,
        embedding_fn: "EmbeddingFn | None" = None,
    ) -> list[HallucinationResult]:
        """Run all detectors and return deduplicated results sorted by severity desc.

        Args:
            response_text: Raw LLM response text.
            manifest: Ground-truth manifest for the brand.
            brand_name: Display name used for logging.
            model_name: LLM model identifier (e.g. "gpt-4o").
            embedding_fn: Optional callable (texts: list[str]) → list[list[float]].
                          Required only for false_attribute detection.
                          If None, false_attribute detection is skipped.
        """
        results: list[HallucinationResult] = []

        results += self._check_regulatory_claims(response_text, manifest, model_name)
        results += self._check_competitor_confusion(response_text, manifest, brand_name, model_name)
        results += self._check_sentiment_drift(response_text, manifest, brand_name, model_name)

        if embedding_fn is not None and manifest.false_attributes:
            results += self._check_false_attributes(
                response_text, manifest, model_name, embedding_fn
            )

        # Deduplicate: keep only the highest-severity result per attribute_slug
        deduped: dict[str, HallucinationResult] = {}
        for r in results:
            existing = deduped.get(r.attribute_slug)
            if existing is None or _SEVERITY_RANK[r.severity] > _SEVERITY_RANK[existing.severity]:
                deduped[r.attribute_slug] = r

        return sorted(deduped.values(), key=lambda x: -_SEVERITY_RANK[x.severity])

    # ------------------------------------------------------------------
    # Detector 1: Regulatory claims (verbatim keyword match)
    # ------------------------------------------------------------------

    def _check_regulatory_claims(
        self,
        response_text: str,
        manifest: BrandManifest,
        model_name: str,
    ) -> list[HallucinationResult]:
        results = []
        lower_response = response_text.lower()

        for claim in manifest.regulatory_claims_to_avoid:
            if claim.lower() in lower_response:
                snippet = self._extract_snippet(response_text, claim)
                slug = re.sub(r"[^a-z0-9]+", "_", claim.lower()).strip("_")
                results.append(
                    HallucinationResult(
                        hallucination_type="regulatory_claim",
                        severity="CRITICAL",
                        attribute_slug=f"regulatory_{slug}",
                        attribute_text=claim,
                        confidence=1.0,
                        evidence_snippet=snippet,
                        model_name=model_name,
                    )
                )
                logger.warning(
                    "Regulatory claim detected",
                    claim=claim,
                    model=model_name,
                )

        return results

    # ------------------------------------------------------------------
    # Detector 2: Competitor confusion (VADER on sentence containing competitor)
    # ------------------------------------------------------------------

    def _check_competitor_confusion(
        self,
        response_text: str,
        manifest: BrandManifest,
        brand_name: str,
        model_name: str,
    ) -> list[HallucinationResult]:
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        except ImportError:
            logger.warning("vaderSentiment not installed — skipping competitor confusion check")
            return []

        analyzer = SentimentIntensityAnalyzer()
        sentences = re.split(r"(?<=[.!?])\s+", response_text)
        results = []

        for competitor in manifest.competitor_list:
            competitor_lower = competitor.lower()

            # Find the sentence with the highest positive compound for this competitor.
            # Using max-compound rather than first-match avoids missing a strongly
            # positive sentence that comes after a neutral one.
            best_compound: float | None = None
            best_sentence: str = ""

            for sentence in sentences:
                if competitor_lower not in sentence.lower():
                    continue
                scores = analyzer.polarity_scores(sentence)
                compound = scores["compound"]
                if compound <= _NEGATIVE_VADER:
                    continue  # negative context — likely contrast, not confusion
                if best_compound is None or compound > best_compound:
                    best_compound = compound
                    best_sentence = sentence

            if best_compound is None:
                continue

            if best_compound > _CONFUSION_POSITIVE_VADER:
                severity = "HIGH"
                confidence = min(1.0, (best_compound - _CONFUSION_POSITIVE_VADER) / 0.5 + 0.7)
            else:
                severity = "MEDIUM"
                confidence = 0.55

            slug = re.sub(r"[^a-z0-9]+", "_", competitor.lower()).strip("_")
            results.append(
                HallucinationResult(
                    hallucination_type="competitor_confusion",
                    severity=severity,
                    attribute_slug=f"competitor_{slug}",
                    attribute_text=competitor,
                    confidence=round(confidence, 3),
                    evidence_snippet=best_sentence[:200],
                    model_name=model_name,
                )
            )

        return results

    # ------------------------------------------------------------------
    # Detector 3: Sentiment drift (VADER compound on full response)
    # ------------------------------------------------------------------

    def _check_sentiment_drift(
        self,
        response_text: str,
        manifest: BrandManifest,
        brand_name: str,
        model_name: str,
    ) -> list[HallucinationResult]:
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        except ImportError:
            return []

        if not manifest.true_attributes:
            return []

        analyzer = SentimentIntensityAnalyzer()
        scores = analyzer.polarity_scores(response_text)
        compound = scores["compound"]

        if compound < _NEGATIVE_VADER:
            confidence = min(1.0, abs(compound))
            return [
                HallucinationResult(
                    hallucination_type="sentiment_drift",
                    severity="MEDIUM",
                    attribute_slug="sentiment_drift_negative",
                    attribute_text=f"Negative sentiment (compound={compound:.3f})",
                    confidence=round(confidence, 3),
                    evidence_snippet=response_text[:200],
                    model_name=model_name,
                )
            ]
        return []

    # ------------------------------------------------------------------
    # Detector 4: False attribute similarity (embedding-based)
    # ------------------------------------------------------------------

    def _check_false_attributes(
        self,
        response_text: str,
        manifest: BrandManifest,
        model_name: str,
        embedding_fn: "EmbeddingFn",
    ) -> list[HallucinationResult]:
        from ml.scoring.proximity import calculate_sps

        all_texts = [response_text] + manifest.false_attributes
        try:
            vectors = embedding_fn(all_texts)
        except Exception:
            logger.exception("Embedding call failed in false_attribute check")
            return []

        if len(vectors) != len(all_texts):
            logger.warning("Unexpected vector count from embedding_fn")
            return []

        response_vec = vectors[0]
        results = []

        for i, attr_text in enumerate(manifest.false_attributes):
            attr_vec = vectors[i + 1]
            similarity = calculate_sps(response_vec, attr_vec)

            # Remap SPS [0,1] back to cosine [-1,1] for threshold comparison
            # SPS = (cosine + 1) / 2 → cosine = 2*SPS - 1
            cosine = 2.0 * similarity - 1.0

            if cosine < _LOW_THRESHOLD:
                continue

            if cosine >= _CRITICAL_THRESHOLD:
                severity = "CRITICAL"
            elif cosine >= _HIGH_THRESHOLD:
                severity = "HIGH"
            else:
                severity = "LOW"

            slug = re.sub(r"[^a-z0-9]+", "_", attr_text.lower()).strip("_")[:64]
            results.append(
                HallucinationResult(
                    hallucination_type="false_attribute",
                    severity=severity,
                    attribute_slug=f"false_{slug}",
                    attribute_text=attr_text,
                    confidence=round(cosine, 4),
                    evidence_snippet=response_text[:200],
                    model_name=model_name,
                )
            )
            logger.info(
                "False attribute detected",
                attr=attr_text,
                cosine=cosine,
                severity=severity,
                model=model_name,
            )

        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_snippet(text: str, keyword: str, window: int = 100) -> str:
        """Extract a window of text around the first occurrence of keyword."""
        lower = text.lower()
        idx = lower.find(keyword.lower())
        if idx == -1:
            return text[:window]
        start = max(0, idx - window // 2)
        end = min(len(text), idx + len(keyword) + window // 2)
        return text[start:end]


# Type alias for the embedding callable used by _check_false_attributes
# Signature: (texts: list[str]) -> list[list[float]]
EmbeddingFn = Any
