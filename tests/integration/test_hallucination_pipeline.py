"""Integration test: fixture → classify → verify precision.

Loads all 4 known fixtures and runs the classifier end-to-end.
No external calls needed — only vaderSentiment (installed) for the
regulatory_claim and competitor_confusion cases.

DoD gate: precision > 0.85 on 3 TP cases out of 3 expected positives
(fixture-004 expects 0 hallucinations, counted separately as true negatives).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from apps.api.models.brand import BrandManifest
from ml.hallucination.classifier import HallucinationClassifier

_FIXTURES_PATH = Path(__file__).parents[2] / "data" / "fixtures" / "hallucination_test_cases.json"

_SEVERITY_RANK = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


@pytest.fixture(scope="module")
def fixtures() -> list[dict[str, Any]]:
    return json.loads(_FIXTURES_PATH.read_text())


@pytest.fixture(scope="module")
def classifier() -> HallucinationClassifier:
    return HallucinationClassifier()


def _classify_fixture(
    classifier: HallucinationClassifier, case: dict[str, Any]
) -> list[Any]:
    manifest = BrandManifest(**case["manifest"])
    return classifier.classify(
        response_text=case["llm_response"],
        manifest=manifest,
        brand_name=case["brand_name"],
        model_name=case["model_name"],
        embedding_fn=None,
    )


# ---------------------------------------------------------------------------
# Fixture 001 — false attribute (no embedding_fn → false_attribute skipped)
# We only check that no *other* spurious detections fire.
# ---------------------------------------------------------------------------

class TestFixture001FalseAttribute:
    def test_no_regulatory_false_positive(
        self, classifier: HallucinationClassifier, fixtures: list[dict[str, Any]]
    ) -> None:
        case = next(c for c in fixtures if c["test_id"] == "fixture-001-false-attribute")
        results = _classify_fixture(classifier, case)
        reg = [r for r in results if r.hallucination_type == "regulatory_claim"]
        assert len(reg) == 0

    def test_no_competitor_confusion_false_positive(
        self, classifier: HallucinationClassifier, fixtures: list[dict[str, Any]]
    ) -> None:
        case = next(c for c in fixtures if c["test_id"] == "fixture-001-false-attribute")
        results = _classify_fixture(classifier, case)
        confusion = [r for r in results if r.hallucination_type == "competitor_confusion"]
        assert len(confusion) == 0


# ---------------------------------------------------------------------------
# Fixture 002 — competitor confusion
# ---------------------------------------------------------------------------

class TestFixture002CompetitorConfusion:
    def test_detects_competitor_confusion(
        self, classifier: HallucinationClassifier, fixtures: list[dict[str, Any]]
    ) -> None:
        case = next(c for c in fixtures if c["test_id"] == "fixture-002-competitor-confusion")
        results = _classify_fixture(classifier, case)
        confusion = [r for r in results if r.hallucination_type == "competitor_confusion"]
        assert len(confusion) >= 1

    def test_severity_meets_minimum(
        self, classifier: HallucinationClassifier, fixtures: list[dict[str, Any]]
    ) -> None:
        case = next(c for c in fixtures if c["test_id"] == "fixture-002-competitor-confusion")
        expected = case["expected_hallucinations"][0]
        results = _classify_fixture(classifier, case)
        confusion = [r for r in results if r.hallucination_type == "competitor_confusion"]
        assert any(
            _SEVERITY_RANK[r.severity] >= _SEVERITY_RANK[expected["min_severity"]]
            for r in confusion
        )

    def test_betaech_in_attribute_text(
        self, classifier: HallucinationClassifier, fixtures: list[dict[str, Any]]
    ) -> None:
        case = next(c for c in fixtures if c["test_id"] == "fixture-002-competitor-confusion")
        results = _classify_fixture(classifier, case)
        confusion = [r for r in results if r.hallucination_type == "competitor_confusion"]
        assert any("BetaTech" in r.attribute_text for r in confusion)


# ---------------------------------------------------------------------------
# Fixture 003 — regulatory claim
# ---------------------------------------------------------------------------

class TestFixture003RegulatoryClaim:
    def test_detects_hipaa(
        self, classifier: HallucinationClassifier, fixtures: list[dict[str, Any]]
    ) -> None:
        case = next(c for c in fixtures if c["test_id"] == "fixture-003-regulatory-claim")
        results = _classify_fixture(classifier, case)
        reg = [r for r in results if r.hallucination_type == "regulatory_claim"]
        assert len(reg) >= 1

    def test_critical_severity(
        self, classifier: HallucinationClassifier, fixtures: list[dict[str, Any]]
    ) -> None:
        case = next(c for c in fixtures if c["test_id"] == "fixture-003-regulatory-claim")
        results = _classify_fixture(classifier, case)
        reg = [r for r in results if r.hallucination_type == "regulatory_claim"]
        assert any(r.severity == "CRITICAL" for r in reg)

    def test_confidence_is_1_0(
        self, classifier: HallucinationClassifier, fixtures: list[dict[str, Any]]
    ) -> None:
        case = next(c for c in fixtures if c["test_id"] == "fixture-003-regulatory-claim")
        results = _classify_fixture(classifier, case)
        reg = [r for r in results if r.hallucination_type == "regulatory_claim"]
        assert all(r.confidence == 1.0 for r in reg)

    def test_evidence_snippet_contains_claim(
        self, classifier: HallucinationClassifier, fixtures: list[dict[str, Any]]
    ) -> None:
        case = next(c for c in fixtures if c["test_id"] == "fixture-003-regulatory-claim")
        results = _classify_fixture(classifier, case)
        reg = [r for r in results if r.hallucination_type == "regulatory_claim"]
        assert any("HIPAA" in r.evidence_snippet for r in reg)


# ---------------------------------------------------------------------------
# Fixture 004 — clean response (zero false positives)
# ---------------------------------------------------------------------------

class TestFixture004CleanResponse:
    def test_no_regulatory_false_positive(
        self, classifier: HallucinationClassifier, fixtures: list[dict[str, Any]]
    ) -> None:
        case = next(c for c in fixtures if c["test_id"] == "fixture-004-clean-response")
        results = _classify_fixture(classifier, case)
        reg = [r for r in results if r.hallucination_type == "regulatory_claim"]
        assert len(reg) == 0

    def test_no_competitor_confusion_false_positive(
        self, classifier: HallucinationClassifier, fixtures: list[dict[str, Any]]
    ) -> None:
        case = next(c for c in fixtures if c["test_id"] == "fixture-004-clean-response")
        results = _classify_fixture(classifier, case)
        confusion = [r for r in results if r.hallucination_type == "competitor_confusion"]
        assert len(confusion) == 0


# ---------------------------------------------------------------------------
# End-to-end precision gate
# ---------------------------------------------------------------------------

class TestEndToEndPrecision:
    def test_precision_exceeds_threshold(
        self, classifier: HallucinationClassifier, fixtures: list[dict[str, Any]]
    ) -> None:
        """End-to-end precision on non-embedding detectors must exceed 0.85.

        false_attribute is excluded: it requires embedding_fn; without one the
        detector is correctly disabled. Coverage for that path is in the unit tests.
        """
        total_expected = 0
        total_tp = 0

        for case in fixtures:
            results = _classify_fixture(classifier, case)

            for expected in case["expected_hallucinations"]:
                if expected["hallucination_type"] == "false_attribute":
                    continue  # requires embedding_fn — not active in this test
                total_expected += 1
                expected_type = expected["hallucination_type"]
                min_rank = _SEVERITY_RANK[expected["min_severity"]]
                matching = [
                    r for r in results
                    if r.hallucination_type == expected_type
                    and _SEVERITY_RANK[r.severity] >= min_rank
                ]
                if matching:
                    total_tp += 1

        precision = total_tp / total_expected if total_expected > 0 else 0.0
        assert precision >= 0.85, (
            f"End-to-end precision {precision:.2f} < 0.85 "
            f"(TP={total_tp} / expected={total_expected})"
        )

    def test_false_positive_rate_on_clean_fixture(
        self, classifier: HallucinationClassifier, fixtures: list[dict[str, Any]]
    ) -> None:
        """Clean fixture must produce zero detections (0% FPR on that case)."""
        case = next(c for c in fixtures if c["test_id"] == "fixture-004-clean-response")
        results = _classify_fixture(classifier, case)
        # Only regulatory + competitor + sentiment detectors run (no embedding_fn)
        # Clean response should not trigger any of them
        non_false_attr = [r for r in results if r.hallucination_type != "false_attribute"]
        assert len(non_false_attr) == 0
