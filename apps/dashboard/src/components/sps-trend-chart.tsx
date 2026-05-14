"use client";

import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { brandTokens } from "@/lib/brand-tokens";
import type { SPSScore } from "@/lib/api-client";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function pivotScores(scores: SPSScore[]): {
  chartData: Record<string, string | number>[];
  clusters: string[];
} {
  // Group by date (day), then pivot by intent_cluster_slug
  const byDate = new Map<string, Record<string, number>>();

  for (const s of scores) {
    const date = s.calculated_at.split("T")[0];
    if (!byDate.has(date)) byDate.set(date, {});
    byDate.get(date)![s.intent_cluster_slug] = Math.round(s.score * 1000) / 1000;
  }

  const chartData = Array.from(byDate.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, vals]) => ({ date: formatDate(date), ...vals }));

  const clusters = [...new Set(scores.map((s) => s.intent_cluster_slug))];

  return { chartData, clusters };
}

const CLUSTER_LABEL: Record<string, string> = {
  reliability:       "Reliability",
  innovation:        "Innovation",
  pricing_value:     "Pricing",
  market_leadership: "Leadership",
  compliance:        "Compliance",
  support_quality:   "Support",
};

// ---------------------------------------------------------------------------
// Custom tooltip
// ---------------------------------------------------------------------------
function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={{
        background: brandTokens.colors.white,
        border: `1px solid ${brandTokens.colors.primary10}`,
        borderRadius: 8,
        padding: "10px 14px",
        boxShadow: "0 2px 8px rgba(0,51,102,0.12)",
        fontFamily: brandTokens.typography.fontBody,
        minWidth: 160,
      }}
    >
      <div
        style={{
          fontSize: 11,
          fontWeight: 600,
          color: brandTokens.colors.dark,
          marginBottom: 8,
        }}
      >
        {label}
      </div>
      {payload.map((entry) => (
        <div
          key={entry.name}
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: 12,
            fontSize: 11,
            color: brandTokens.colors.mid,
            marginBottom: 3,
          }}
        >
          <span style={{ color: entry.color }}>
            {CLUSTER_LABEL[entry.name] ?? entry.name}
          </span>
          <strong style={{ color: brandTokens.colors.dark }}>
            {(entry.value * 100).toFixed(1)}%
          </strong>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// SPSTrendChart
// ---------------------------------------------------------------------------

interface SPSTrendChartProps {
  scores: SPSScore[];
  isLoading?: boolean;
  /** ISO date strings to annotate as hallucination events */
  hallucinationDates?: string[];
}

export function SPSTrendChart({
  scores,
  isLoading,
  hallucinationDates = [],
}: SPSTrendChartProps) {
  const { chartData, clusters } = useMemo(() => pivotScores(scores), [scores]);

  if (isLoading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: 300,
        }}
      >
        <p
          style={{
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 13,
            color: brandTokens.colors.mid,
          }}
        >
          Loading SPS history…
        </p>
      </div>
    );
  }

  if (!chartData.length) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: 300,
          border: `1px dashed ${brandTokens.colors.primary10}`,
          borderRadius: 8,
        }}
      >
        <p
          style={{
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 13,
            color: brandTokens.colors.mid,
          }}
        >
          No SPS data yet — run the embedding pipeline to populate scores.
        </p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={chartData} margin={{ top: 8, right: 24, bottom: 8, left: 0 }}>
        <CartesianGrid
          strokeDasharray="3 3"
          stroke={brandTokens.colors.primary10}
          vertical={false}
        />
        <XAxis
          dataKey="date"
          tick={{
            fontSize: 10,
            fill: brandTokens.colors.mid,
            fontFamily: brandTokens.typography.fontBody,
          }}
          tickLine={false}
          axisLine={{ stroke: brandTokens.colors.primary10 }}
        />
        <YAxis
          domain={[0, 1]}
          tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
          tick={{
            fontSize: 10,
            fill: brandTokens.colors.mid,
            fontFamily: brandTokens.typography.fontBody,
          }}
          tickLine={false}
          axisLine={false}
          width={40}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 10,
            paddingTop: 12,
          }}
          formatter={(value: string) => CLUSTER_LABEL[value] ?? value}
        />
        {/* Industry benchmark line */}
        <ReferenceLine
          y={0.6}
          stroke={brandTokens.colors.mid}
          strokeDasharray="5 5"
          label={{
            value: "Avg",
            position: "insideTopRight",
            fill: brandTokens.colors.mid,
            fontSize: 9,
            fontFamily: brandTokens.typography.fontBody,
          }}
        />
        {/* Hallucination event annotations */}
        {hallucinationDates.map((d) => (
          <ReferenceLine
            key={d}
            x={formatDate(d)}
            stroke={brandTokens.status.danger.base}
            strokeDasharray="4 4"
            label={{
              value: "⚠",
              position: "top",
              fill: brandTokens.status.danger.base,
              fontSize: 10,
            }}
          />
        ))}
        {/* One Line per cluster */}
        {clusters.map((slug, i) => (
          <Line
            key={slug}
            type="monotone"
            dataKey={slug}
            stroke={brandTokens.dataSeries[i % brandTokens.dataSeries.length]}
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
            isAnimationActive
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
