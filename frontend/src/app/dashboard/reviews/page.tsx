"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  FileSearch,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Plus,
  GitPullRequest,
  Code,
  Trash2,
  Bug,
  Shield,
  Zap,
  Link2,
  Ruler,
} from "lucide-react";
import toast from "react-hot-toast";
import { cn } from "@/lib/utils";
import { Modal } from "@/components/ui/modal";
import {
  listReviews,
  getReviewStats,
  createManualReview,
  deleteReview,
  listRepos,
} from "@/lib/api";
import type {
  CodeReviewSummary,
  ReviewStats,
  ReviewVerdict,
} from "@/lib/types";

const VERDICT_CONFIG: Record<
  ReviewVerdict,
  { label: string; color: string; bg: string }
> = {
  approved: { label: "Aprovado", color: "text-green-500", bg: "bg-green-500/10" },
  approved_with_warnings: { label: "Com ressalvas", color: "text-yellow-500", bg: "bg-yellow-500/10" },
  needs_changes: { label: "Precisa mudancas", color: "text-orange-500", bg: "bg-orange-500/10" },
  rejected: { label: "Rejeitado", color: "text-red-500", bg: "bg-red-500/10" },
};

const CATEGORY_ICONS: Record<string, typeof Bug> = {
  bug: Bug,
  security: Shield,
  performance: Zap,
  consistency: Link2,
  pattern: Ruler,
};

function scoreColor(score: number | null | undefined): string {
  if (score == null) return "text-muted";
  if (score >= 85) return "text-green-500";
  if (score >= 70) return "text-yellow-500";
  if (score >= 50) return "text-orange-500";
  return "text-red-500";
}

function scoreBg(score: number | null | undefined): string {
  if (score == null) return "bg-muted/10";
  if (score >= 85) return "bg-green-500/10";
  if (score >= 70) return "bg-yellow-500/10";
  if (score >= 50) return "bg-orange-500/10";
  return "bg-red-500/10";
}

const LANGUAGES = [
  "python", "javascript", "typescript", "java", "go", "rust",
  "ruby", "php", "c", "cpp", "csharp", "swift", "kotlin",
];

export default function ReviewsPage() {
  const [reviews, setReviews] = useState<CodeReviewSummary[]>([]);
  const [stats, setStats] = useState<ReviewStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);

  // Filters
  const [filterSource, setFilterSource] = useState<string>("");
  const [filterVerdict, setFilterVerdict] = useState<string>("");

  // Manual review modal
  const [showManual, setShowManual] = useState(false);
  const [manualCode, setManualCode] = useState("");
  const [manualLang, setManualLang] = useState("python");
  const [manualContext, setManualContext] = useState("");
  const [manualRepoId, setManualRepoId] = useState("");
  const [manualLoading, setManualLoading] = useState(false);
  const [repos, setRepos] = useState<{ name: string }[]>([]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [r, s, rp] = await Promise.all([
        listReviews({
          source_type: filterSource || undefined,
          verdict: filterVerdict || undefined,
        }),
        getReviewStats(),
        listRepos(),
      ]);
      setReviews(r);
      setStats(s);
      setRepos(rp);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao carregar revisoes");
    } finally {
      setLoading(false);
    }
  }, [filterSource, filterVerdict]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  async function handleManualReview() {
    if (!manualCode.trim()) {
      toast.error("Cole o codigo para revisar");
      return;
    }
    setManualLoading(true);
    try {
      const result = await createManualReview({
        code: manualCode,
        language: manualLang,
        context: manualContext || undefined,
        repo_id: manualRepoId || undefined,
      });
      toast.success("Analise iniciada! Atualize em instantes.");
      setShowManual(false);
      setManualCode("");
      setManualContext("");
      setTimeout(fetchData, 5000);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao criar revisao");
    } finally {
      setManualLoading(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Deletar esta revisao?")) return;
    setDeleting(id);
    try {
      await deleteReview(id);
      setReviews((prev) => prev.filter((r) => r.id !== id));
      toast.success("Revisao deletada");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao deletar");
    } finally {
      setDeleting(null);
    }
  }

  // Trend arrow
  const trend = stats?.weekly_trend || [];
  let trendDirection: "up" | "down" | "flat" = "flat";
  if (trend.length >= 2) {
    const recent = trend[trend.length - 1]?.avg_score;
    const prev = trend[trend.length - 2]?.avg_score;
    if (recent != null && prev != null) {
      if (recent > prev + 2) trendDirection = "up";
      else if (recent < prev - 2) trendDirection = "down";
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold flex items-center gap-2">
            <FileSearch size={22} className="text-accent" />
            Revisao de Codigo
          </h1>
          <p className="text-sm text-muted mt-1">
            Revisoes automaticas de PRs e manuais de trechos de codigo
          </p>
        </div>
        <button
          onClick={() => setShowManual(true)}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors"
        >
          <Plus size={16} />
          Revisar codigo
        </button>
      </div>

      {/* Stats cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="rounded-xl border border-border bg-card-bg p-4">
            <div className="flex items-center justify-between">
              <p className="text-xs text-muted font-medium">Score Medio</p>
              {trendDirection === "up" && <TrendingUp size={14} className="text-green-500" />}
              {trendDirection === "down" && <TrendingDown size={14} className="text-red-500" />}
              {trendDirection === "flat" && <Minus size={14} className="text-muted" />}
            </div>
            <p className={cn("text-2xl font-bold mt-1", scoreColor(stats.avg_score))}>
              {stats.avg_score != null ? stats.avg_score : "—"}
            </p>
          </div>
          <div className="rounded-xl border border-border bg-card-bg p-4">
            <p className="text-xs text-muted font-medium">Revisoes este mes</p>
            <p className="text-2xl font-bold mt-1">{stats.this_month}</p>
          </div>
          <div className="rounded-xl border border-border bg-card-bg p-4">
            <p className="text-xs text-muted font-medium">Findings criticos</p>
            <p className={cn("text-2xl font-bold mt-1", stats.critical_findings > 0 ? "text-red-500" : "text-muted")}>
              {stats.critical_findings}
            </p>
          </div>
          <div className="rounded-xl border border-border bg-card-bg p-4">
            <p className="text-xs text-muted font-medium">Taxa de aprovacao</p>
            <p className="text-2xl font-bold mt-1 text-green-500">
              {stats.approval_rate != null ? `${stats.approval_rate}%` : "—"}
            </p>
          </div>
        </div>
      )}

      {/* Findings by category */}
      {stats && Object.keys(stats.findings_by_category).length > 0 && (
        <div className="rounded-xl border border-border bg-card-bg p-4">
          <p className="text-xs text-muted font-medium mb-3">Findings por categoria</p>
          <div className="flex flex-wrap gap-3">
            {Object.entries(stats.findings_by_category).map(([cat, count]) => {
              const Icon = CATEGORY_ICONS[cat] || Bug;
              return (
                <div key={cat} className="flex items-center gap-1.5 text-sm">
                  <Icon size={14} className="text-muted" />
                  <span className="capitalize">{cat}</span>
                  <span className="text-muted font-medium">({count})</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3">
        <select
          value={filterSource}
          onChange={(e) => setFilterSource(e.target.value)}
          className="px-3 py-1.5 text-sm rounded-lg border border-border bg-card-bg"
        >
          <option value="">Todas as fontes</option>
          <option value="pr">PRs</option>
          <option value="manual">Manual</option>
        </select>
        <select
          value={filterVerdict}
          onChange={(e) => setFilterVerdict(e.target.value)}
          className="px-3 py-1.5 text-sm rounded-lg border border-border bg-card-bg"
        >
          <option value="">Todos os veredictos</option>
          <option value="approved">Aprovado</option>
          <option value="approved_with_warnings">Com ressalvas</option>
          <option value="needs_changes">Precisa mudancas</option>
          <option value="rejected">Rejeitado</option>
        </select>
      </div>

      {/* Reviews list */}
      {loading ? (
        <div className="flex items-center justify-center py-12 text-muted">
          <Loader2 size={20} className="animate-spin mr-2" /> Carregando...
        </div>
      ) : reviews.length === 0 ? (
        <div className="text-center py-16 text-muted">
          <FileSearch size={40} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">Nenhuma revisao encontrada</p>
          <p className="text-xs mt-1">
            Revisoes aparecem automaticamente ao abrir PRs ou clique em &ldquo;Revisar codigo&rdquo;
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {reviews.map((review) => {
            const verdict = review.overall_verdict
              ? VERDICT_CONFIG[review.overall_verdict]
              : null;
            return (
              <div
                key={review.id}
                className="flex items-center gap-4 rounded-xl border border-border bg-card-bg p-4 hover:border-accent/30 transition-colors"
              >
                {/* Score circle */}
                <div
                  className={cn(
                    "flex items-center justify-center w-12 h-12 rounded-full text-lg font-bold shrink-0",
                    scoreBg(review.overall_score),
                    scoreColor(review.overall_score)
                  )}
                >
                  {review.status === "analyzing" ? (
                    <Loader2 size={18} className="animate-spin" />
                  ) : review.status === "failed" ? (
                    <AlertTriangle size={18} className="text-red-500" />
                  ) : (
                    review.overall_score ?? "—"
                  )}
                </div>

                {/* Info */}
                <Link href={`/dashboard/reviews/${review.id}`} className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    {review.source_type === "pr" ? (
                      <GitPullRequest size={14} className="text-purple-500 shrink-0" />
                    ) : (
                      <Code size={14} className="text-blue-500 shrink-0" />
                    )}
                    <p className="text-sm font-medium truncate">
                      {review.source_type === "pr"
                        ? review.pr_title || `PR #${review.pr_number}`
                        : `Revisao manual${review.language ? ` (${review.language})` : ""}`}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 mt-1">
                    {verdict && (
                      <span className={cn("text-xs font-medium px-2 py-0.5 rounded-full", verdict.bg, verdict.color)}>
                        {verdict.label}
                      </span>
                    )}
                    {review.status === "analyzing" && (
                      <span className="text-xs text-blue-500">Analisando...</span>
                    )}
                    {review.status === "failed" && (
                      <span className="text-xs text-red-500">Falha</span>
                    )}
                    {review.pr_author && (
                      <span className="text-xs text-muted">por {review.pr_author}</span>
                    )}
                    {review.repo_id && (
                      <span className="text-xs text-muted font-mono">{review.repo_id}</span>
                    )}
                    <span className="text-xs text-muted">
                      {review.created_at
                        ? new Date(review.created_at).toLocaleDateString("pt-BR")
                        : ""}
                    </span>
                  </div>
                </Link>

                {/* Actions */}
                <button
                  onClick={() => handleDelete(review.id)}
                  disabled={deleting === review.id}
                  className="p-1.5 rounded-lg border border-border hover:bg-hover text-red-400 hover:text-red-500 transition-colors shrink-0"
                  title="Deletar"
                >
                  {deleting === review.id ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <Trash2 size={14} />
                  )}
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Manual Review Modal */}
      <Modal
        open={showManual}
        onClose={() => setShowManual(false)}
        title="Revisar Codigo Manualmente"
      >
        <div className="space-y-4">
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-sm font-medium mb-1">Linguagem</label>
              <select
                value={manualLang}
                onChange={(e) => setManualLang(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card-bg"
              >
                {LANGUAGES.map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
            </div>
            {repos.length > 0 && (
              <div className="flex-1">
                <label className="block text-sm font-medium mb-1">Repositorio (opcional)</label>
                <select
                  value={manualRepoId}
                  onChange={(e) => setManualRepoId(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card-bg"
                >
                  <option value="">Nenhum</option>
                  {repos.map((r) => (
                    <option key={r.name} value={r.name}>
                      {r.name}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Codigo *</label>
            <textarea
              value={manualCode}
              onChange={(e) => setManualCode(e.target.value)}
              rows={12}
              placeholder="Cole o codigo aqui..."
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground placeholder:text-muted font-mono resize-y"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Contexto (opcional)</label>
            <textarea
              value={manualContext}
              onChange={(e) => setManualContext(e.target.value)}
              rows={2}
              placeholder='Ex: "Esse codigo vai substituir o modulo de autenticacao atual"'
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground placeholder:text-muted resize-y"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={() => setShowManual(false)}
              className="px-4 py-2 text-sm rounded-lg border border-border hover:bg-hover transition-colors"
            >
              Cancelar
            </button>
            <button
              onClick={handleManualReview}
              disabled={manualLoading}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors disabled:opacity-50"
            >
              {manualLoading && <Loader2 size={14} className="animate-spin" />}
              Analisar
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
