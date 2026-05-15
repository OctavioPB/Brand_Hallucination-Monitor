"use client";

import { useCostBreakdown, useCostSummary, useInfraCosts } from "@/hooks/use-costs";
import { useBrands } from "@/hooks/use-brands";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

// ---------------------------------------------------------------------------
// Budget meter
// ---------------------------------------------------------------------------

function BudgetMeter({ pct }: { pct: number }) {
  const color =
    pct >= 90 ? "bg-red-500" : pct >= 70 ? "bg-yellow-400" : "bg-emerald-500";
  return (
    <div className="w-full bg-neutral-800 rounded-full h-2.5 mt-3">
      <div
        className={`${color} h-2.5 rounded-full transition-all duration-500`}
        style={{ width: `${Math.min(pct, 100)}%` }}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// KPI card
// ---------------------------------------------------------------------------

function KpiCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="rounded-2xl bg-neutral-900 border border-neutral-800 p-5">
      <p className="text-xs text-neutral-400 uppercase tracking-widest">{label}</p>
      <p className="text-3xl font-semibold text-white mt-1">{value}</p>
      {sub && <p className="text-xs text-neutral-500 mt-1">{sub}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Spend chart
// ---------------------------------------------------------------------------

function SpendChart({ days }: { days: number }) {
  const { data = [], isLoading } = useCostBreakdown(days);

  // Aggregate by day for the area chart
  const byDay = data.reduce<Record<string, number>>((acc, r) => {
    acc[r.day] = (acc[r.day] ?? 0) + r.cost_usd;
    return acc;
  }, {});
  const chartData = Object.entries(byDay)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([day, cost]) => ({ day, cost: parseFloat(cost.toFixed(4)) }));

  if (isLoading) {
    return (
      <div className="h-48 flex items-center justify-center text-neutral-500 text-sm">
        Loading…
      </div>
    );
  }
  if (chartData.length === 0) {
    return (
      <div className="h-48 flex items-center justify-center text-neutral-500 text-sm">
        No spend data yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={192}>
      <AreaChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="costGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
        <XAxis
          dataKey="day"
          tick={{ fontSize: 10, fill: "#737373" }}
          tickFormatter={(v: string) => v.slice(5)}
        />
        <YAxis
          tick={{ fontSize: 10, fill: "#737373" }}
          tickFormatter={(v: number) => `$${v.toFixed(3)}`}
        />
        <Tooltip
          contentStyle={{ background: "#171717", border: "1px solid #262626", borderRadius: 8 }}
          labelStyle={{ color: "#a3a3a3", fontSize: 11 }}
          itemStyle={{ color: "#e5e5e5", fontSize: 12 }}
          formatter={(v: number) => [`$${v.toFixed(4)}`, "Cost"]}
        />
        <Area
          type="monotone"
          dataKey="cost"
          stroke="#6366f1"
          strokeWidth={2}
          fill="url(#costGradient)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// ---------------------------------------------------------------------------
// Breakdown table
// ---------------------------------------------------------------------------

function BreakdownTable({ days }: { days: number }) {
  const { data = [], isLoading } = useCostBreakdown(days);

  if (isLoading) return <p className="text-neutral-500 text-sm">Loading…</p>;
  if (data.length === 0)
    return <p className="text-neutral-500 text-sm">No records yet.</p>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-neutral-500 uppercase tracking-widest border-b border-neutral-800">
            <th className="pb-2 pr-4">Day</th>
            <th className="pb-2 pr-4">Job type</th>
            <th className="pb-2 pr-4 text-right">Cost (USD)</th>
            <th className="pb-2 pr-4 text-right">Tokens</th>
            <th className="pb-2 text-right">API calls</th>
          </tr>
        </thead>
        <tbody>
          {data.map((r, i) => (
            <tr
              key={i}
              className="border-b border-neutral-800/50 hover:bg-neutral-800/30 transition-colors"
            >
              <td className="py-2 pr-4 text-neutral-300">{r.day}</td>
              <td className="py-2 pr-4">
                <span className="px-2 py-0.5 rounded-full text-xs bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                  {r.job_type}
                </span>
              </td>
              <td className="py-2 pr-4 text-right font-mono text-emerald-400">
                ${r.cost_usd.toFixed(4)}
              </td>
              <td className="py-2 pr-4 text-right text-neutral-400">
                {r.tokens.toLocaleString()}
              </td>
              <td className="py-2 text-right text-neutral-400">{r.calls}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Infra cost table (Airflow DAG tasks)
// ---------------------------------------------------------------------------

function InfraTable() {
  const { data = [], isLoading } = useInfraCosts(7);

  if (isLoading) return <p className="text-neutral-500 text-sm">Loading…</p>;
  if (data.length === 0)
    return <p className="text-neutral-500 text-sm">No Airflow cost records yet.</p>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-neutral-500 uppercase tracking-widest border-b border-neutral-800">
            <th className="pb-2 pr-4">DAG</th>
            <th className="pb-2 pr-4">Task</th>
            <th className="pb-2 pr-4">Component</th>
            <th className="pb-2 pr-4">Model</th>
            <th className="pb-2 text-right">Cost (USD)</th>
          </tr>
        </thead>
        <tbody>
          {data.map((r, i) => (
            <tr
              key={i}
              className="border-b border-neutral-800/50 hover:bg-neutral-800/30 transition-colors"
            >
              <td className="py-2 pr-4 text-xs text-neutral-400 font-mono truncate max-w-[160px]">
                {r.dag_id}
              </td>
              <td className="py-2 pr-4 text-xs text-neutral-400 font-mono">{r.task_id}</td>
              <td className="py-2 pr-4">
                <span className="px-2 py-0.5 rounded-full text-xs bg-violet-500/10 text-violet-300 border border-violet-500/20">
                  {r.cost_component}
                </span>
              </td>
              <td className="py-2 pr-4 text-xs text-neutral-400">{r.model ?? "—"}</td>
              <td className="py-2 text-right font-mono text-emerald-400">
                ${r.cost_usd.toFixed(4)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function CostsPage() {
  const { data: summary, isLoading: summaryLoading } = useCostSummary();

  const todaySpend = summary?.total_cost_usd ?? 0;
  const cap = summary?.budget_cap_usd ?? 0;
  const pct = summary?.budget_used_pct ?? 0;

  return (
    <div className="space-y-8">
      {/* Hero */}
      <div>
        <h1 className="text-2xl font-semibold text-white">Cost Dashboard</h1>
        <p className="text-sm text-neutral-400 mt-1">
          Embedding spend, API usage, and Airflow task cost tagging.
        </p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Today's spend"
          value={summaryLoading ? "…" : `$${todaySpend.toFixed(4)}`}
          sub={`of $${cap.toFixed(2)} daily cap`}
        />
        <KpiCard
          label="Budget used"
          value={summaryLoading ? "…" : `${pct.toFixed(1)}%`}
          sub="rolling 24h window"
        />
        <KpiCard
          label="API calls today"
          value={summaryLoading ? "…" : (summary?.api_calls ?? 0).toLocaleString()}
          sub="OpenAI embeddings"
        />
        <KpiCard
          label="Cache hit tokens"
          value={
            summaryLoading
              ? "…"
              : (summary?.vectors_from_cache ?? 0).toLocaleString()
          }
          sub="vectors served from Redis"
        />
      </div>

      {/* Budget meter */}
      {!summaryLoading && (
        <div className="rounded-2xl bg-neutral-900 border border-neutral-800 p-5">
          <div className="flex justify-between items-center">
            <p className="text-sm text-neutral-300">Daily budget</p>
            <p className="text-sm font-mono text-neutral-400">
              ${todaySpend.toFixed(4)} / ${cap.toFixed(2)}
            </p>
          </div>
          <BudgetMeter pct={pct} />
          {pct >= 90 && (
            <p className="mt-2 text-xs text-red-400">
              ⚠ Approaching daily limit — new embedding jobs will be paused.
            </p>
          )}
        </div>
      )}

      {/* Spend trend chart */}
      <div className="rounded-2xl bg-neutral-900 border border-neutral-800 p-5">
        <h2 className="text-sm font-medium text-neutral-300 mb-4">
          Spend trend — last 30 days
        </h2>
        <SpendChart days={30} />
      </div>

      {/* Breakdown + Infra side-by-side */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 rounded-2xl bg-neutral-900 border border-neutral-800 p-5">
          <h2 className="text-sm font-medium text-neutral-300 mb-4">
            Cost breakdown by job type (30 days)
          </h2>
          <BreakdownTable days={30} />
        </div>

        <div className="rounded-2xl bg-neutral-900 border border-neutral-800 p-5">
          <h2 className="text-sm font-medium text-neutral-300 mb-4">
            Airflow task costs (7 days)
          </h2>
          <InfraTable />
        </div>
      </div>
    </div>
  );
}
