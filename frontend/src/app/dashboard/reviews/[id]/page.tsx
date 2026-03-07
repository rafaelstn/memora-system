"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Loader2,
  ExternalLink,
  GitPullRequest,
  Code,
  Bug,
  Shield,
  Zap,
  Link2,
  Ruler,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
} from "lucide-react";
import toast from "react-hot-toast";
import { cn } from "@/lib/utils";
import { getReview } from "@/lib/api";
import type {
  CodeReviewDetail,
  FindingCategory,
  FindingSeverity,
  ReviewVerdict,
  ReviewFinding,
} from "@/lib/types";

const VERDICT_CONFIG: Record<
  ReviewVerdict,
  { label: string; color: string; bg: string }
> = {
  approved: { label: "Aprovado", color: "text-green-500", bg: "bg-green-500/10" },
  approved_with_warnings: { label: "Aprovado com ressalvas", color: "text-yellow-500", bg: "bg-yellow-500/10" },
  needs_changes: { label: "Precisa de alteracoes", color: "text-orange-500", bg: "bg-orange-500/10" },
  rejected: { label: "Rejeitado", color: "text-red-500", bg: "bg-red-500/10" },
};

const CATEGORY_CONFIG: Record<
  FindingCategory,
  { label: string; icon: typeof Bug; color: string }
> = {
  bug: { label: "Bugs", icon: Bug, color: "text-red-400" },
  security: { label: "Seguranca", icon: Shield, color: "text-orange-400" },
  performance: { label: "Performance", icon: Zap, color: "text-yellow-400" },
  consistency: { label: "Consistencia", icon: Link2, color: "text-blue-400" },
  pattern: { label: "Padroes", icon: Ruler, color: "text-purple-400" },
};

const SEVERITY_CONFIG: Record<
  FindingSeverity,
  { label: string; color: string; bg: string }
> = {
  critical: { label: "CRITICAL", color: "text-red-500", bg: "bg-red-500/10" },
  high: { label: "HIGH", color: "text-orange-500", bg: "bg-orange-500/10" },
  medium: { label: "MEDIUM", color: "text-yellow-500", bg: "bg-yellow-500/10" },
  low: { label: "LOW", color: "text-blue-500", bg: "bg-blue-500/10" },
  info: { label: "INFO", color: "text-muted", bg: "bg-muted/10" },
};

function scoreColor(score: number | null | undefined): string {
  if (score == null) return "text-muted";
  if (score >= 85) return "text-green-500";
  if (score >= 70) return "text-yellow-500";
  if (score >= 50) return "text-orange-500";
  return "text-red-500";
}

export default function ReviewDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [review, setReview] = useState<CodeReviewDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState<FindingCategory | "all">("all");
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getReview(id)
      .then(setReview)
      .catch((err) => {
        toast.error(err instanceof Error ? err.message : "Erro ao carregar revisao");
        router.push("/dashboard/reviews");
      })
      .finally(() => setLoading(false));
  }, [id, router]);

  // Auto-refresh while analyzing
  useEffect(() => {
    if (!review || review.status !== "analyzing") return;
    const interval = setInterval(() => {
      getReview(id).then(setReview).catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, [review?.status, id]);

  function toggleCategory(cat: string) {
    setCollapsedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 size={24} className="animate-spin text-muted" />
      </div>
    );
  }

  if (!review) return null;

  const verdict = review.overall_verdict ? VERDICT_CONFIG[review.overall_verdict] : null;

  // Group findings by category
  const findingsByCategory: Record<string, ReviewFinding[]> = {};
  for (const f of review.findings) {
    findingsByCategory[f.category] = findingsByCategory[f.category] || [];
    findingsByCategory[f.category].push(f);
  }

  // Severity distribution
  const severityCounts: Record<string, number> = {};
  for (const f of review.findings) {
    severityCounts[f.severity] = (severityCounts[f.severity] || 0) + 1;
  }

  const filteredFindings =
    activeCategory === "all"
      ? review.findings
      : review.findings.filter((f) => f.category === activeCategory);

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Back link */}
      <Link
        href="/dashboard/reviews"
        className="inline-flex items-center gap-1 text-sm text-muted hover:text-foreground transition-colors"
      >
        <ArrowLeft size={14} />
        Voltar
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {review.source_type === "pr" ? (
              <GitPullRequest size={18} className="text-purple-500 shrink-0" />
            ) : (
              <Code size={18} className="text-blue-500 shrink-0" />
            )}
            <h1 className="text-xl font-semibold truncate">
              {review.source_type === "pr"
                ? review.pr_title || `PR #${review.pr_number}`
                : `Revisao Manual${review.language ? ` (${review.language})` : ""}`}
            </h1>
          </div>
          <div className="flex items-center gap-3 text-sm text-muted">
            {review.pr_author && <span>por {review.pr_author}</span>}
            {review.repo_id && <span className="font-mono">{review.repo_id}</span>}
            {review.created_at && (
              <span>{new Date(review.created_at).toLocaleDateString("pt-BR")}</span>
            )}
            {review.pr_url && (
              <a
                href={review.pr_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-accent hover:underline"
              >
                Ver PR <ExternalLink size={12} />
              </a>
            )}
          </div>
        </div>

        {/* Score */}
        <div className="text-center shrink-0">
          {review.status === "analyzing" ? (
            <div className="flex flex-col items-center gap-2">
              <Loader2 size={24} className="animate-spin text-accent" />
              <span className="text-xs text-muted">Analisando...</span>
            </div>
          ) : (
            <>
              <div
                className={cn(
                  "text-4xl font-bold",
                  scoreColor(review.overall_score)
                )}
              >
                {review.overall_score ?? "—"}
              </div>
              <p className="text-xs text-muted">/100</p>
            </>
          )}
        </div>
      </div>

      {/* Verdict badge + status */}
      {verdict && (
        <div className="flex items-center gap-3">
          <span
            className={cn(
              "text-sm font-medium px-3 py-1 rounded-full",
              verdict.bg,
              verdict.color
            )}
          >
            {verdict.label}
          </span>
          {review.github_comment_posted && (
            <span className="text-xs text-green-500">Comentario postado no GitHub</span>
          )}
        </div>
      )}

      {/* Summary */}
      {review.summary && review.status === "completed" && (
        <div className="rounded-xl border border-border bg-card-bg p-4">
          <p className="text-sm font-medium mb-2">Resumo</p>
          <div className="text-sm text-muted leading-relaxed whitespace-pre-wrap">
            {review.summary}
          </div>
        </div>
      )}

      {/* Severity distribution bar */}
      {review.findings.length > 0 && (
        <div className="rounded-xl border border-border bg-card-bg p-4">
          <p className="text-sm font-medium mb-3">
            Distribuicao ({review.findings.length} findings)
          </p>
          <div className="flex gap-2 flex-wrap">
            {(["critical", "high", "medium", "low", "info"] as FindingSeverity[]).map((sev) => {
              const count = severityCounts[sev] || 0;
              if (count === 0) return null;
              const config = SEVERITY_CONFIG[sev];
              return (
                <span
                  key={sev}
                  className={cn("text-xs font-medium px-2 py-1 rounded-full", config.bg, config.color)}
                >
                  {config.label}: {count}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* Category filter tabs */}
      {review.findings.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => setActiveCategory("all")}
            className={cn(
              "text-xs px-3 py-1.5 rounded-full border transition-colors",
              activeCategory === "all"
                ? "border-accent bg-accent/10 text-accent"
                : "border-border hover:bg-hover"
            )}
          >
            Todos ({review.findings.length})
          </button>
          {(["bug", "security", "performance", "consistency", "pattern"] as FindingCategory[]).map(
            (cat) => {
              const count = findingsByCategory[cat]?.length || 0;
              if (count === 0) return null;
              const config = CATEGORY_CONFIG[cat];
              const Icon = config.icon;
              return (
                <button
                  key={cat}
                  onClick={() => setActiveCategory(cat)}
                  className={cn(
                    "inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded-full border transition-colors",
                    activeCategory === cat
                      ? "border-accent bg-accent/10 text-accent"
                      : "border-border hover:bg-hover"
                  )}
                >
                  <Icon size={12} />
                  {config.label} ({count})
                </button>
              );
            }
          )}
        </div>
      )}

      {/* Findings */}
      {review.status === "completed" && review.findings.length === 0 && (
        <div className="text-center py-12 text-muted">
          <CheckCircle2 size={40} className="mx-auto mb-3 text-green-500 opacity-50" />
          <p className="text-sm">Nenhum problema encontrado!</p>
        </div>
      )}

      {filteredFindings.length > 0 && (
        <div className="space-y-3">
          {filteredFindings.map((finding) => {
            const catConfig = CATEGORY_CONFIG[finding.category];
            const sevConfig = SEVERITY_CONFIG[finding.severity];
            const CatIcon = catConfig?.icon || Bug;

            return (
              <div
                key={finding.id}
                className="rounded-xl border border-border bg-card-bg overflow-hidden"
              >
                <div className="p-4">
                  <div className="flex items-start gap-3">
                    <CatIcon size={16} className={cn("mt-0.5 shrink-0", catConfig?.color)} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <span
                          className={cn(
                            "text-[10px] font-bold px-1.5 py-0.5 rounded",
                            sevConfig.bg,
                            sevConfig.color
                          )}
                        >
                          {sevConfig.label}
                        </span>
                        <h3 className="text-sm font-medium">{finding.title}</h3>
                      </div>
                      {finding.file_path && (
                        <p className="text-xs text-muted font-mono mb-2">
                          {finding.file_path}
                          {finding.line_start ? `:${finding.line_start}` : ""}
                          {finding.line_end && finding.line_end !== finding.line_start
                            ? `-${finding.line_end}`
                            : ""}
                        </p>
                      )}
                      <p className="text-sm text-muted leading-relaxed">{finding.description}</p>
                      {finding.code_snippet && (
                        <pre className="mt-2 p-3 rounded-lg bg-black/5 dark:bg-white/5 text-xs font-mono overflow-x-auto">
                          {finding.code_snippet}
                        </pre>
                      )}
                      {finding.suggestion && (
                        <div className="mt-2 p-3 rounded-lg bg-green-500/5 border border-green-500/10">
                          <p className="text-xs font-medium text-green-600 dark:text-green-400 mb-1">
                            Sugestao
                          </p>
                          <p className="text-sm text-muted">{finding.suggestion}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
