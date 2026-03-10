"use client";

import { useState, useEffect, useRef } from "react";
import {
  getLatestSnapshot,
  generateSnapshot,
  getSnapshotHistory,
  getRealtimeMetrics,
} from "@/lib/api";
import type {
  ExecutiveSnapshot,
  ExecutiveRealtimeMetrics,
  ExecutiveHighlight,
  ExecutiveRisk,
  ExecutiveRecommendation,
} from "@/lib/types";
import {
  Activity,
  AlertTriangle,
  ArrowUp,
  ArrowDown,
  Minus,
  CheckCircle2,
  RefreshCcw,
  Shield,
  Server,
  Database,
  Clock,
  Loader2,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { ExportPDFButton } from "@/components/ui/export-pdf-button";
import ExecutiveHistory from "@/components/executive/ExecutiveHistory";

function HealthGauge({ score }: { score: number }) {
  const color =
    score >= 80
      ? "text-green-500"
      : score >= 60
        ? "text-yellow-500"
        : score >= 40
          ? "text-orange-500"
          : "text-red-500";
  const bg =
    score >= 80
      ? "bg-green-500/10"
      : score >= 60
        ? "bg-yellow-500/10"
        : score >= 40
          ? "bg-orange-500/10"
          : "bg-red-500/10";

  return (
    <div className={`flex flex-col items-center justify-center rounded-2xl p-6 ${bg}`}>
      <span className={`text-6xl font-bold ${color}`}>{score}</span>
      <span className="text-sm text-muted mt-1">Health Score</span>
      <div className="w-full mt-3 h-2 rounded-full bg-border overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color.replace("text-", "bg-")}`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}

function HighlightCard({ h }: { h: ExecutiveHighlight }) {
  const icon =
    h.type === "positive" ? (
      <ArrowUp className="text-green-500" size={16} />
    ) : h.type === "negative" ? (
      <ArrowDown className="text-red-500" size={16} />
    ) : (
      <Minus className="text-muted" size={16} />
    );
  const border =
    h.type === "positive"
      ? "border-green-500/30"
      : h.type === "negative"
        ? "border-red-500/30"
        : "border-border";

  return (
    <div className={`flex items-start gap-3 rounded-lg border p-3 ${border}`}>
      <span className="mt-0.5">{icon}</span>
      <p className="text-sm">{h.text}</p>
    </div>
  );
}

function RiskCard({ r }: { r: ExecutiveRisk }) {
  const colors = {
    low: "bg-blue-500/10 border-blue-500/30 text-blue-600",
    medium: "bg-yellow-500/10 border-yellow-500/30 text-yellow-600",
    high: "bg-red-500/10 border-red-500/30 text-red-600",
  };
  const c = colors[r.severity] || colors.medium;

  return (
    <div className={`rounded-lg border p-4 ${c.split(" ").slice(0, 2).join(" ")}`}>
      <div className="flex items-center gap-2 mb-2">
        <AlertTriangle size={16} className={c.split(" ")[2]} />
        <span className={`text-xs font-semibold uppercase ${c.split(" ")[2]}`}>
          {r.severity}
        </span>
      </div>
      <p className="text-sm mb-2">{r.description}</p>
      <p className="text-xs text-muted">{r.recommendation}</p>
    </div>
  );
}

function RecommendationItem({ r }: { r: ExecutiveRecommendation }) {
  return (
    <div className="flex items-start gap-3 py-3 border-b border-border last:border-0">
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-surface text-accent-text text-xs font-bold">
        {r.priority}
      </span>
      <div>
        <p className="text-sm font-medium">{r.action}</p>
        <p className="text-xs text-muted mt-0.5">{r.reason}</p>
      </div>
    </div>
  );
}

function MetricCard({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-border bg-card-bg p-6">
      <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${color}`}>
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold">{value}</p>
        <p className="text-xs text-muted">{label}</p>
      </div>
    </div>
  );
}

export default function ExecutiveDashboardPage() {
  const [snapshot, setSnapshot] = useState<ExecutiveSnapshot | null>(null);
  const [metrics, setMetrics] = useState<ExecutiveRealtimeMetrics | null>(null);
  const [history, setHistory] = useState<ExecutiveSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [showHistory, setShowHistory] = useState(false);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    Promise.allSettled([
      getLatestSnapshot().then(setSnapshot).catch(() => null),
      getRealtimeMetrics().then(setMetrics),
    ]).finally(() => setLoading(false));

    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    pollIntervalRef.current = setInterval(() => {
      getRealtimeMetrics().then(setMetrics).catch(() => {});
    }, 15000);
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, []);

  const handleGenerate = async (period: "week" | "month") => {
    setGenerating(true);
    setError("");
    try {
      const snap = await generateSnapshot(period);
      setSnapshot(snap);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Erro ao gerar snapshot");
    } finally {
      setGenerating(false);
    }
  };

  const loadHistory = async () => {
    if (showHistory) {
      setShowHistory(false);
      return;
    }
    try {
      const res = await getSnapshotHistory();
      setHistory(res.snapshots);
      setShowHistory(true);
    } catch {
      // ignore
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-muted" size={32} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold mb-1">Visao Executiva</h1>
          <p className="text-sm text-muted">
            Panorama consolidado de todos os sistemas
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => handleGenerate("week")}
            disabled={generating}
            className="flex items-center gap-2 rounded-lg bg-accent-surface px-4 py-2 text-sm font-medium text-accent-text hover:opacity-90 disabled:opacity-50"
          >
            {generating ? (
              <Loader2 className="animate-spin" size={14} />
            ) : (
              <RefreshCcw size={14} />
            )}
            Gerar Semanal
          </button>
          <button
            onClick={() => handleGenerate("month")}
            disabled={generating}
            className="flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-hover disabled:opacity-50"
          >
            Gerar Mensal
          </button>
          {snapshot?.id && (
            <ExportPDFButton
              endpoint={`/api/executive/snapshot/${snapshot.id}/pdf`}
              filename={`executive-${snapshot.id}.pdf`}
              size="sm"
            />
          )}
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {/* Real-time metrics */}
      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard
            icon={<Server size={20} className="text-blue-500" />}
            label="Sistemas Monitorados"
            value={metrics.systems_monitored}
            color="bg-blue-500/10"
          />
          <MetricCard
            icon={<AlertTriangle size={20} className="text-yellow-500" />}
            label="Alertas Abertos"
            value={metrics.alerts_open}
            color="bg-yellow-500/10"
          />
          <MetricCard
            icon={<Shield size={20} className="text-red-500" />}
            label="Incidentes Ativos"
            value={metrics.incidents_open}
            color="bg-red-500/10"
          />
          <MetricCard
            icon={<Database size={20} className="text-green-500" />}
            label="Repos Indexados"
            value={metrics.repos_indexed}
            color="bg-green-500/10"
          />
        </div>
      )}

      {/* Snapshot */}
      {snapshot ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Health Score + Summary */}
          <div className="space-y-4">
            <HealthGauge score={snapshot.health_score} />
            {snapshot.summary && (
              <div className="rounded-lg border border-border p-4">
                <p className="text-sm leading-relaxed">{snapshot.summary}</p>
                <p className="text-xs text-muted mt-2 flex items-center gap-1">
                  <Clock size={12} />
                  {new Date(snapshot.generated_at).toLocaleString("pt-BR")}
                </p>
              </div>
            )}
          </div>

          {/* Center: Highlights + Risks */}
          <div className="space-y-4">
            {snapshot.highlights.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                  <Activity size={14} />
                  Destaques
                </h3>
                <div className="space-y-2">
                  {snapshot.highlights.map((h, i) => (
                    <HighlightCard key={i} h={h} />
                  ))}
                </div>
              </div>
            )}

            {snapshot.risks.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                  <AlertTriangle size={14} />
                  Riscos
                </h3>
                <div className="space-y-2">
                  {snapshot.risks.map((r, i) => (
                    <RiskCard key={i} r={r} />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right: Recommendations */}
          <div>
            {snapshot.recommendations.length > 0 && (
              <div className="rounded-lg border border-border p-4">
                <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                  <CheckCircle2 size={14} />
                  Recomendacoes
                </h3>
                {snapshot.recommendations
                  .sort((a, b) => a.priority - b.priority)
                  .map((r, i) => (
                    <RecommendationItem key={i} r={r} />
                  ))}
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-border bg-card-bg p-12 text-center">
          <Activity className="mx-auto mb-4 text-muted" size={36} />
          <p className="text-sm text-muted mb-1">
            Nenhum snapshot gerado ainda.
          </p>
          <p className="text-xs text-muted">
            Clique em &quot;Gerar Semanal&quot; para criar o primeiro relatorio.
          </p>
        </div>
      )}

      {/* History toggle */}
      <button
        onClick={loadHistory}
        className="flex items-center gap-2 text-sm text-muted hover:text-foreground mt-2"
      >
        {showHistory ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        Historico de Snapshots
      </button>

      {showHistory && history.length > 0 && (
        <div className="rounded-lg border border-border divide-y divide-border">
          {history.map((s) => (
            <div
              key={s.id}
              className="flex items-center justify-between px-4 py-3 hover:bg-hover cursor-pointer"
              onClick={() => setSnapshot(s)}
            >
              <div className="flex items-center gap-3">
                <span
                  className={`text-lg font-bold ${
                    s.health_score >= 80
                      ? "text-green-500"
                      : s.health_score >= 60
                        ? "text-yellow-500"
                        : "text-red-500"
                  }`}
                >
                  {s.health_score}
                </span>
                <span className="text-sm text-muted truncate max-w-md">
                  {s.summary || "Sem resumo"}
                </span>
              </div>
              <span className="text-xs text-muted whitespace-nowrap">
                {new Date(s.generated_at).toLocaleDateString("pt-BR")}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Weekly History with Chart & Table */}
      <div className="rounded-xl border border-border bg-card-bg p-6">
        <ExecutiveHistory />
      </div>
    </div>
  );
}
