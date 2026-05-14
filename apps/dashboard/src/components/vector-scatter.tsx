"use client";

import { useState, useRef, useCallback } from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import { brandTokens } from "@/lib/brand-tokens";
import type { VectorPoint } from "@/lib/api-client";

// ---------------------------------------------------------------------------
// Cluster → color mapping (BRAND.md data series order)
// ---------------------------------------------------------------------------
const CLUSTER_COLORS: Record<string, string> = {
  reliability:       brandTokens.dataSeries[0], // corporate blue
  innovation:        brandTokens.dataSeries[1], // green
  pricing_value:     brandTokens.dataSeries[2], // purple
  market_leadership: brandTokens.dataSeries[3], // orange
  compliance:        brandTokens.dataSeries[4], // pink
  support_quality:   "#2563EB",
};

const CLUSTER_LABELS: Record<string, string> = {
  reliability:       "Reliability",
  innovation:        "Innovation",
  pricing_value:     "Pricing & Value",
  market_leadership: "Market Leadership",
  compliance:        "Compliance",
  support_quality:   "Support Quality",
};

// ---------------------------------------------------------------------------
// Custom dot shape — colored by cluster
// ---------------------------------------------------------------------------
function renderDot(props: {
  cx?: number;
  cy?: number;
  payload?: VectorPoint;
}) {
  const { cx = 0, cy = 0, payload } = props;
  const color = payload
    ? (CLUSTER_COLORS[payload.cluster_slug] ?? brandTokens.colors.primary)
    : brandTokens.colors.primary;
  return (
    <circle
      key={`dot-${cx}-${cy}`}
      cx={cx}
      cy={cy}
      r={10}
      fill={color}
      stroke={brandTokens.colors.white}
      strokeWidth={2}
      style={{ transition: "cx 0.4s ease, cy 0.4s ease" }}
    />
  );
}

// ---------------------------------------------------------------------------
// Custom tooltip
// ---------------------------------------------------------------------------
function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: VectorPoint }>;
}) {
  if (!active || !payload?.length) return null;
  const p = payload[0]?.payload;
  if (!p) return null;
  return (
    <div
      style={{
        background: brandTokens.colors.white,
        border: `1px solid ${brandTokens.colors.primary10}`,
        borderRadius: 8,
        padding: "10px 14px",
        boxShadow: "0 2px 8px rgba(0,51,102,0.12)",
        fontFamily: brandTokens.typography.fontBody,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginBottom: 6,
        }}
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            backgroundColor:
              CLUSTER_COLORS[p.cluster_slug] ?? brandTokens.colors.primary,
            flexShrink: 0,
          }}
        />
        <span
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: brandTokens.colors.dark,
          }}
        >
          {p.label}
        </span>
      </div>
      <div style={{ fontSize: 11, color: brandTokens.colors.mid }}>
        SPS Score:{" "}
        <strong style={{ color: brandTokens.colors.dark }}>
          {(p.score * 100).toFixed(1)}%
        </strong>
      </div>
      <div
        style={{
          fontSize: 10,
          color: brandTokens.colors.mid,
          marginTop: 3,
          letterSpacing: "0.5px",
        }}
      >
        ({p.x.toFixed(2)}, {p.y.toFixed(2)})
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Control button style
// ---------------------------------------------------------------------------
const ctrlBtn: React.CSSProperties = {
  fontFamily: brandTokens.typography.fontBody,
  fontSize: 10,
  letterSpacing: "1.5px",
  textTransform: "uppercase",
  background: brandTokens.colors.light,
  border: `1px solid ${brandTokens.colors.primary10}`,
  borderRadius: 6,
  padding: "4px 12px",
  cursor: "pointer",
  color: brandTokens.colors.mid,
};

// ---------------------------------------------------------------------------
// VectorScatter
// ---------------------------------------------------------------------------

interface VectorScatterProps {
  points: VectorPoint[];
  isLoading?: boolean;
}

export function VectorScatter({ points, isLoading }: VectorScatterProps) {
  const [scale, setScale] = useState(1);
  const [translate, setTranslate] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0, tx: 0, ty: 0 });

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    setScale((prev) => Math.max(0.5, Math.min(4, prev - e.deltaY * 0.001)));
  }, []);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      setIsDragging(true);
      dragStart.current = {
        x: e.clientX,
        y: e.clientY,
        tx: translate.x,
        ty: translate.y,
      };
    },
    [translate]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isDragging) return;
      setTranslate({
        x: dragStart.current.tx + (e.clientX - dragStart.current.x),
        y: dragStart.current.ty + (e.clientY - dragStart.current.y),
      });
    },
    [isDragging]
  );

  const handleMouseUp = useCallback(() => setIsDragging(false), []);
  const handleReset = () => {
    setScale(1);
    setTranslate({ x: 0, y: 0 });
  };

  if (isLoading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: 380,
        }}
      >
        <p
          style={{
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 13,
            color: brandTokens.colors.mid,
          }}
        >
          Loading vector map…
        </p>
      </div>
    );
  }

  if (!points.length) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: 380,
          flexDirection: "column",
          gap: 8,
        }}
      >
        <p
          style={{
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 13,
            color: brandTokens.colors.mid,
          }}
        >
          No SPS data yet — run a scan to populate the vector map.
        </p>
      </div>
    );
  }

  return (
    <div>
      {/* Zoom controls */}
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          gap: 6,
          marginBottom: 12,
        }}
      >
        <button onClick={() => setScale((s) => Math.min(4, s + 0.25))} style={ctrlBtn}>
          +
        </button>
        <button onClick={() => setScale((s) => Math.max(0.5, s - 0.25))} style={ctrlBtn}>
          −
        </button>
        <button onClick={handleReset} style={ctrlBtn}>
          Reset
        </button>
        <span
          style={{
            fontFamily: brandTokens.typography.fontBody,
            fontSize: 10,
            color: brandTokens.colors.mid,
            alignSelf: "center",
            marginLeft: 4,
          }}
        >
          Scroll to zoom · Drag to pan
        </span>
      </div>

      {/* Chart canvas */}
      <div
        style={{
          overflow: "hidden",
          cursor: isDragging ? "grabbing" : "grab",
          borderRadius: 8,
          height: 360,
          border: `1px solid ${brandTokens.colors.primary10}`,
          backgroundColor: brandTokens.colors.white,
        }}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <div
          style={{
            transform: `translate(${translate.x}px, ${translate.y}px) scale(${scale})`,
            transformOrigin: "center",
            height: "100%",
          }}
        >
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 20, right: 30, bottom: 20, left: 30 }}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke={brandTokens.colors.primary10}
              />
              <XAxis
                type="number"
                dataKey="x"
                domain={[-1, 1]}
                tickCount={5}
                tick={{
                  fontSize: 10,
                  fill: brandTokens.colors.mid,
                  fontFamily: brandTokens.typography.fontBody,
                }}
                tickLine={false}
                axisLine={{ stroke: brandTokens.colors.primary10 }}
              />
              <YAxis
                type="number"
                dataKey="y"
                domain={[-1, 1]}
                tickCount={5}
                tick={{
                  fontSize: 10,
                  fill: brandTokens.colors.mid,
                  fontFamily: brandTokens.typography.fontBody,
                }}
                tickLine={false}
                axisLine={{ stroke: brandTokens.colors.primary10 }}
              />
              <ReferenceLine
                x={0}
                stroke={brandTokens.colors.primary30}
                strokeDasharray="4 4"
              />
              <ReferenceLine
                y={0}
                stroke={brandTokens.colors.primary30}
                strokeDasharray="4 4"
              />
              <Tooltip
                content={<CustomTooltip />}
                cursor={{ strokeDasharray: "3 3" }}
              />
              <Scatter
                data={points}
                isAnimationActive
                shape={renderDot as React.FC}
              />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Legend */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 16,
          marginTop: 16,
        }}
      >
        {Object.entries(CLUSTER_LABELS).map(([slug, label]) => {
          const color = CLUSTER_COLORS[slug] ?? brandTokens.colors.primary;
          return (
            <div
              key={slug}
              style={{ display: "flex", alignItems: "center", gap: 6 }}
            >
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  backgroundColor: color,
                  flexShrink: 0,
                }}
              />
              <span
                style={{
                  fontFamily: brandTokens.typography.fontBody,
                  fontSize: 10,
                  color: brandTokens.colors.mid,
                }}
              >
                {label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
