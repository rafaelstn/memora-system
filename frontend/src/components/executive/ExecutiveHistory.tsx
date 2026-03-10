"use client";

import { useState, useEffect, useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { getExecutiveHistory, getExecutiveHistoryCsvUrl } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import type { ExecutiveWeeklySnapshot } from "@/lib/types";
import { Download, Loader2 } from "lucide-react";

type Period = "4w" | "3m" | "6m";

type MetricKey =
  | "security_score_avg"
  | "error_alert_count"
  | "support_question_count"
  | "code_review_score_avg"
  | "prs_reviewed_count"
  | "incident_resolution_avg_hours"
  | "doc_coverage_pct";

interface MetricDef {
  key: MetricKey;
  label: string;
  color: string;
  higherIsBetter: boolean;
}

const METRICS: MetricDef[] = [
  { key: "security_score_avg", label: "Score Seguranca", color: "#6366f1", higherIsBetter: true },
  { key: "error_alert_count", label: "Alertas de Erro", color: "#ef4444", higherIsBetter: false },
  { key: "support_question_count", label: "Perguntas Suporte", color: "#f59e0b", higherIsBetter: false },
  { key: "code_review_score_avg", label: "Score Code Review", color: "#10b981", higherIsBetter: true },
  { key: "prs_reviewed_count", label: "PRs Revisados", color: "#3b82f6", higherIsBetter: true },
  { key: "incident_resolution_avg_hours", label: "Tempo Resolucao (h)", color: "#8b5cf6", higherIsBetter: false },
  { key: "doc_coverage_pct", label: "Cobertura Docs (%)", color: "#14b8a6", higherIsBetter: true },
];

const PERIOD_LABELS: { value: Period; label: string }[] = [
  { value: "4w", label: "4 semanas" },
  { value: "3m", label: "3 meses" },
  { value: "6m", label: "6 meses" },
];

const MAX_SELECTED = 4;

function formatWeek(dateStr: string): string {
  const d = new Date(dateStr);
  const day = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  return `${day}/${month}`;
}

function formatNumber(val: number): string {
  return Number.isInteger(val) ? String(val) : val.toFixed(1);
}

export default function ExecutiveHistory() {
  const [period, setPeriod] = useState<Period>("4w");
  const [data, setData] = useState<ExecutiveWeeklySnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<MetricKey[]>([
    "security_score_avg",
    "error_alert_count",
    "code_review_score_avg",
    "doc_coverage_pct",
  ]);

  useEffect(() => {
    setLoading(true);
    setError("");
    getExecutiveHistory(period)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Erro ao carregar historico"))
      .finally(() => setLoading(false));
  }, [period]);

  const averages = useMemo(() => {
    if (data.length === 0) return {} as Record<MetricKey, number>;
    const sums: Record<string, number> = {};
    for (const m of METRICS) sums[m.key] = 0;
    for (const row of data) {
      for (const m of METRICS) sums[m.key] += row[m.key] ?? 0;
    }
    const avgs: Record<string, number> = {};
    for (const m of METRICS) avgs[m.key] = sums[m.key] / data.length;
    return avgs as Record<MetricKey, number>;
  }, [data]);

  const chartData = useMemo(
    () =>
      data.map((row) => ({
        week: formatWeek(row.week_start),
        ...Object.fromEntries(METRICS.map((m) => [m.key, row[m.key] ?? 0])),
      })),
    [data],
  );

  const toggleMetric = (key: MetricKey) => {
    setSelected((prev) => {
      if (prev.includes(key)) return prev.filter((k) => k !== key);
      if (prev.length >= MAX_SELECTED) return prev;
      return [...prev, key];
    });
  };

  const handleExportCSV = async () => {
    const token = await getAccessToken();
    const url = getExecutiveHistoryCsvUrl(period);
    const a = document.createElement("a");
    a.href = token ? `${url}&token=${encodeURIComponent(token)}` : url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const selectedDefs = METRICS.filter((m) => selected.includes(m.key));

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Historico Semanal</h2>
        <div className="flex items-center gap-3">
          {/* Period tabs */}
          <div className="flex rounded-lg border border-border overflow-hidden">
            {PERIOD_LABELS.map((p) => (
              <button
                key={p.value}
                onClick={() => setPeriod(p.value)}
                className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                  period === p.value
                    ? "bg-accent-surface text-accent-text"
                    : "hover:bg-hover text-muted"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
          <button
            onClick={handleExportCSV}
            className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium hover:bg-hover"
          >
            <Download size={12} />
            Exportar CSV
          </button>
        </div>
      </div>

      {/* Metric checkboxes */}
      <div className="flex flex-wrap gap-2">
        {METRICS.map((m) => {
          const isSelected = selected.includes(m.key);
          const disabled = !isSelected && selected.length >= MAX_SELECTED;
          return (
            <button
              key={m.key}
              onClick={() => toggleMetric(m.key)}
              disabled={disabled}
              className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
                isSelected
                  ? "border-transparent text-white"
                  : disabled
                    ? "border-border text-muted opacity-40 cursor-not-allowed"
                    : "border-border text-muted hover:bg-hover"
              }`}
              style={isSelected ? { backgroundColor: m.color } : undefined}
            >
              {m.label}
            </button>
          );
        })}
        <span className="text-[10px] text-muted self-center ml-1">max {MAX_SELECTED}</span>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-48">
          <Loader2 className="animate-spin text-muted" size={24} />
        </div>
      ) : data.length === 0 ? (
        <div className="rounded-lg border border-border p-8 text-center text-sm text-muted">
          Nenhum dado historico disponivel para este periodo.
        </div>
      ) : (
        <>
          {/* Chart */}
          {selectedDefs.length > 0 && (
            <div className="rounded-xl border border-border bg-card-bg p-4">
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                  <XAxis dataKey="week" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--color-card-bg, #1a1a2e)",
                      border: "1px solid var(--color-border, #333)",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                  />
                  <Legend
                    formatter={(value: string) => {
                      const m = METRICS.find((mt) => mt.key === value);
                      return m?.label ?? value;
                    }}
                    wrapperStyle={{ fontSize: "11px" }}
                  />
                  {selectedDefs.map((m) => (
                    <Line
                      key={m.key}
                      type="monotone"
                      dataKey={m.key}
                      stroke={m.color}
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      activeDot={{ r: 5 }}
                      name={m.key}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Comparative table */}
          <div className="rounded-xl border border-border overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border bg-hover/50">
                  <th className="px-3 py-2 text-left font-semibold">Semana</th>
                  {METRICS.map((m) => (
                    <th key={m.key} className="px-3 py-2 text-right font-semibold whitespace-nowrap">
                      {m.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.map((row, idx) => {
                  const isLast = idx === data.length - 1;
                  return (
                    <tr
                      key={row.id}
                      className={`border-b border-border last:border-0 ${
                        isLast ? "bg-accent-surface/5" : "hover:bg-hover/30"
                      }`}
                    >
                      <td className="px-3 py-2 font-medium whitespace-nowrap">
                        {formatWeek(row.week_start)}
                        {isLast && (
                          <span className="ml-1.5 text-[10px] text-accent-text bg-accent-surface/20 rounded px-1 py-0.5">
                            atual
                          </span>
                        )}
                      </td>
                      {METRICS.map((m) => {
                        const val = row[m.key] ?? 0;
                        const avg = averages[m.key] ?? 0;
                        const better = m.higherIsBetter ? val >= avg : val <= avg;
                        const cellColor =
                          avg === 0 ? "" : better ? "text-green-500" : "text-red-500";
                        return (
                          <td
                            key={m.key}
                            className={`px-3 py-2 text-right tabular-nums ${cellColor}`}
                          >
                            {formatNumber(val)}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
              {/* Averages row */}
              <tfoot>
                <tr className="border-t border-border bg-hover/30">
                  <td className="px-3 py-2 font-semibold">Media</td>
                  {METRICS.map((m) => (
                    <td key={m.key} className="px-3 py-2 text-right font-semibold tabular-nums text-muted">
                      {formatNumber(averages[m.key] ?? 0)}
                    </td>
                  ))}
                </tr>
              </tfoot>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
