"""Report data assembly and PDF rendering for weekly brand safety reports.

Usage:
    generator = ReportGenerator(db_session)
    report = await generator.generate_weekly(brand_id=..., organization_id=..., week_start=date.today())
"""
from __future__ import annotations

import io
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.db import AlertORM
from apps.api.models.probe_result import ProbeResultORM
from apps.api.models.report import ReportORM
from apps.api.models.sps_score import SPSScoreORM

logger = structlog.get_logger(__name__)

# Recommended action templates per intent cluster
_RECOMMENDED_ACTIONS: dict[str, str] = {
    "reliability": (
        "Publish customer success stories and uptime reports to reinforce reliability signals."
    ),
    "innovation": (
        "Increase technical blog posts and feature announcements to boost innovation associations."
    ),
    "pricing_value": (
        "Ensure pricing pages are clear and competitive comparison content is up to date."
    ),
    "market_leadership": (
        "Submit for analyst reports (Gartner, Forrester) to strengthen leadership positioning."
    ),
    "compliance": (
        "Publish security whitepapers and compliance certifications to reinforce trust signals."
    ),
    "support_quality": (
        "Encourage customers to leave reviews mentioning support experience on G2/Trustpilot."
    ),
}

_SPS_WARN = 0.50
_SPS_CRITICAL = 0.35


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ClusterSPS:
    slug: str
    current_score: float
    previous_score: float

    @property
    def delta(self) -> float:
        return self.current_score - self.previous_score

    @property
    def trend(self) -> str:
        if self.delta > 0.02:
            return "improving"
        if self.delta < -0.02:
            return "declining"
        return "stable"


@dataclass
class ReportContent:
    brand_id: str
    brand_name: str
    week_start: date
    week_end: date
    clusters: list[ClusterSPS] = field(default_factory=list)
    top_hallucinations: list[dict[str, Any]] = field(default_factory=list)
    total_probes: int = 0
    total_hallucinations: int = 0
    active_alerts: int = 0
    recommended_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "brand_id": self.brand_id,
            "brand_name": self.brand_name,
            "week_start": self.week_start.isoformat(),
            "week_end": self.week_end.isoformat(),
            "clusters": [
                {
                    "slug": c.slug,
                    "current_score": round(c.current_score, 4),
                    "previous_score": round(c.previous_score, 4),
                    "delta": round(c.delta, 4),
                    "trend": c.trend,
                }
                for c in self.clusters
            ],
            "top_hallucinations": self.top_hallucinations,
            "total_probes": self.total_probes,
            "total_hallucinations": self.total_hallucinations,
            "active_alerts": self.active_alerts,
            "recommended_actions": self.recommended_actions,
        }


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class ReportGenerator:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def generate_weekly(
        self,
        brand_id: uuid.UUID,
        organization_id: str,
        brand_name: str,
        week_start: date | None = None,
    ) -> ReportORM:
        """Assemble a full weekly report and persist it.  Returns the saved ReportORM row."""
        ws = week_start or (date.today() - timedelta(days=7))
        we = ws + timedelta(days=6)

        content = await self._assemble(brand_id, brand_name, ws, we)

        pdf = self._render_pdf(content)

        report = ReportORM(
            id=uuid.uuid4(),
            organization_id=organization_id,
            brand_id=brand_id,
            report_type="weekly",
            title=f"Brand Safety Report — {ws.strftime('%b %d')}–{we.strftime('%b %d, %Y')}",
            content_json=content.to_dict(),
            pdf_bytes=pdf,
            week_start=ws,
        )
        self._db.add(report)
        await self._db.commit()
        await self._db.refresh(report)

        logger.info(
            "Weekly report generated",
            brand_id=str(brand_id),
            week_start=ws.isoformat(),
            report_id=str(report.id),
        )
        return report

    # ------------------------------------------------------------------
    # Data assembly
    # ------------------------------------------------------------------

    async def _assemble(
        self,
        brand_id: uuid.UUID,
        brand_name: str,
        week_start: date,
        week_end: date,
    ) -> ReportContent:
        current_start = datetime(week_start.year, week_start.month, week_start.day, tzinfo=timezone.utc)
        current_end = datetime(week_end.year, week_end.month, week_end.day, 23, 59, 59, tzinfo=timezone.utc)
        previous_start = current_start - timedelta(days=7)
        previous_end = current_start - timedelta(seconds=1)

        # ---- SPS scores ----
        current_sps = await self._latest_sps_per_cluster(brand_id, current_start, current_end)
        previous_sps = await self._latest_sps_per_cluster(brand_id, previous_start, previous_end)

        clusters = [
            ClusterSPS(
                slug=slug,
                current_score=score,
                previous_score=previous_sps.get(slug, score),
            )
            for slug, score in current_sps.items()
        ]
        clusters.sort(key=lambda c: c.current_score)

        # ---- Probe results / hallucinations ----
        probes_result = await self._db.execute(
            select(ProbeResultORM)
            .where(
                ProbeResultORM.brand_id == brand_id,
                ProbeResultORM.probed_at >= current_start,
                ProbeResultORM.probed_at <= current_end,
            )
            .order_by(ProbeResultORM.hallucinations_detected.desc())
        )
        probes = probes_result.scalars().all()

        top_hallucinations = [
            {
                "model_name": p.model_name,
                "probe_prompt": p.probe_prompt[:120],
                "hallucinations_detected": p.hallucinations_detected,
                "cost_usd": float(p.cost_usd),
                "probed_at": p.probed_at.isoformat(),
            }
            for p in probes
            if p.hallucinations_detected > 0
        ][:5]

        total_hallucinations = sum(p.hallucinations_detected for p in probes)

        # ---- Active unacknowledged alerts ----
        alerts_result = await self._db.execute(
            select(AlertORM).where(
                AlertORM.brand_id == brand_id,
                AlertORM.acknowledged.is_(False),
            )
        )
        active_alerts = len(alerts_result.scalars().all())

        # ---- Recommended actions ----
        recommended: list[str] = []
        for c in clusters:
            if c.current_score < _SPS_WARN and c.slug in _RECOMMENDED_ACTIONS:
                recommended.append(
                    f"[{c.slug.replace('_', ' ').title()} — {c.current_score * 100:.0f}%] "
                    + _RECOMMENDED_ACTIONS[c.slug]
                )
        if not recommended:
            recommended.append(
                "Maintain current content strategy — all SPS scores are above warning threshold."
            )

        return ReportContent(
            brand_id=str(brand_id),
            brand_name=brand_name,
            week_start=week_start,
            week_end=week_end,
            clusters=clusters,
            top_hallucinations=top_hallucinations,
            total_probes=len(probes),
            total_hallucinations=total_hallucinations,
            active_alerts=active_alerts,
            recommended_actions=recommended,
        )

    async def _latest_sps_per_cluster(
        self,
        brand_id: uuid.UUID,
        since: datetime,
        until: datetime,
    ) -> dict[str, float]:
        """Return the latest SPS score per cluster within the date window."""
        result = await self._db.execute(
            select(SPSScoreORM)
            .where(
                SPSScoreORM.brand_id == brand_id,
                SPSScoreORM.calculated_at >= since,
                SPSScoreORM.calculated_at <= until,
            )
            .order_by(SPSScoreORM.calculated_at.desc())
        )
        rows = result.scalars().all()

        # Latest score per cluster (already ordered desc so first wins)
        seen: dict[str, float] = {}
        for r in rows:
            if r.intent_cluster_slug not in seen:
                seen[r.intent_cluster_slug] = r.score
        return seen

    # ------------------------------------------------------------------
    # PDF rendering via reportlab
    # ------------------------------------------------------------------

    def _render_pdf(self, content: ReportContent) -> bytes:
        """Render a compact PDF using reportlab. Returns raw bytes."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                HRFlowable,
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )
        except ImportError:
            logger.warning("reportlab not installed — PDF bytes will be empty")
            return b""

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()
        brand_blue = colors.HexColor("#003366")
        gold = colors.HexColor("#C8982A")

        h1 = ParagraphStyle(
            "h1",
            fontName="Helvetica-Bold",
            fontSize=18,
            textColor=brand_blue,
            spaceAfter=4,
        )
        h2 = ParagraphStyle(
            "h2",
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=brand_blue,
            spaceBefore=14,
            spaceAfter=4,
        )
        body = ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=9,
            textColor=colors.HexColor("#1C1C2E"),
            leading=14,
        )
        muted = ParagraphStyle(
            "muted",
            fontName="Helvetica",
            fontSize=8,
            textColor=colors.HexColor("#6B7280"),
        )

        elements: list[object] = []

        # ---- Header ----
        elements.append(Paragraph(f"hallucin8 · Brand Safety Report", h1))
        elements.append(
            Paragraph(
                f"{content.brand_name} · {content.week_start.strftime('%b %d')}–"
                f"{content.week_end.strftime('%b %d, %Y')}",
                muted,
            )
        )
        elements.append(HRFlowable(width="100%", thickness=1, color=gold, spaceAfter=12))

        # ---- Executive summary ----
        elements.append(Paragraph("Executive Summary", h2))
        elements.append(
            Paragraph(
                f"This week <b>{content.brand_name}</b> recorded "
                f"<b>{content.total_probes}</b> LLM probes across monitored models, "
                f"with <b>{content.total_hallucinations}</b> hallucination detections. "
                f"There are currently <b>{content.active_alerts}</b> unacknowledged alert(s).",
                body,
            )
        )
        elements.append(Spacer(1, 8))

        # ---- SPS cluster table ----
        elements.append(Paragraph("Semantic Proximity Scores (SPS)", h2))
        if content.clusters:
            table_data = [["Cluster", "This Week", "Last Week", "Delta", "Trend"]]
            for c in sorted(content.clusters, key=lambda x: x.slug):
                delta_str = f"{c.delta:+.1%}"
                row_color = None
                if c.current_score < _SPS_CRITICAL:
                    row_color = colors.HexColor("#FDEAEA")
                elif c.current_score < _SPS_WARN:
                    row_color = colors.HexColor("#FEF0E6")
                table_data.append([
                    c.slug.replace("_", " ").title(),
                    f"{c.current_score:.1%}",
                    f"{c.previous_score:.1%}",
                    delta_str,
                    c.trend.capitalize(),
                ])
            sps_table = Table(table_data, colWidths=[5 * cm, 2.5 * cm, 2.5 * cm, 2 * cm, 2.5 * cm])
            sps_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), brand_blue),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0EAF4")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6F9")]),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ])
            )
            elements.append(sps_table)
        else:
            elements.append(Paragraph("No SPS data available for this period.", muted))

        # ---- Top hallucinations ----
        elements.append(Paragraph("Top Hallucinations Detected", h2))
        if content.top_hallucinations:
            for i, h in enumerate(content.top_hallucinations, 1):
                elements.append(
                    Paragraph(
                        f"{i}. <b>{h['model_name']}</b> — "
                        f"{h['hallucinations_detected']} flag(s) · "
                        f"<i>{h['probe_prompt']}…</i>",
                        body,
                    )
                )
                elements.append(Spacer(1, 3))
        else:
            elements.append(Paragraph("No hallucinations detected this week.", muted))

        # ---- Recommended actions ----
        elements.append(Paragraph("Recommended Actions", h2))
        for action in content.recommended_actions:
            elements.append(Paragraph(f"• {action}", body))
            elements.append(Spacer(1, 4))

        # ---- Footer ----
        elements.append(Spacer(1, 16))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E0EAF4")))
        elements.append(
            Paragraph(
                f"Generated {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · "
                "hallucin8 — SGE Semantic Dominance & Brand Hallucination Monitor",
                muted,
            )
        )

        doc.build(elements)
        return buf.getvalue()
