"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import toast from "react-hot-toast";
import {
  FileText,
  GraduationCap,
  RefreshCw,
  Upload,
  Copy,
  Check,
  ChevronDown,
  ChevronRight,
  Loader2,
  ArrowLeft,
  Sparkles,
  PartyPopper,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/hooks/useAuth";
import {
  generateDocs,
  getDocsStatus,
  getReadme,
  getOnboardingGuide,
  pushReadmeToGitHub,
  getOnboardingProgress,
  completeOnboardingStep,
} from "@/lib/api";
import type { RepoDocStatus, RepoDoc, OnboardingProgress } from "@/lib/types";

type Tab = "readme" | "onboarding";

interface OnboardingStep {
  id: string;
  title: string;
  file?: string;
  time?: string;
  content: string;
}

function parseOnboardingSteps(markdown: string): OnboardingStep[] {
  const steps: OnboardingStep[] = [];
  const regex = /### Passo (\d+)\s*[—–-]\s*(.+?)(?:\n|$)([\s\S]*?)(?=### Passo \d+|## |$)/gi;
  let match;

  while ((match = regex.exec(markdown)) !== null) {
    const num = match[1];
    const title = match[2].trim();
    const body = match[3].trim();

    // Extract file reference
    const fileMatch = body.match(/\*\*Arquivo:\*\*\s*(.+)/i);
    const timeMatch = body.match(/\*\*Tempo estimado:\*\*\s*(.+)/i);

    steps.push({
      id: `step-${num}`,
      title,
      file: fileMatch?.[1]?.replace(/`/g, "").trim(),
      time: timeMatch?.[1]?.replace(/`/g, "").trim(),
      content: body,
    });
  }

  return steps;
}

export default function DocsPage() {
  const params = useParams();
  const repoName = decodeURIComponent(params.repoName as string);
  const { role } = useAuth();
  const isAdmin = role === "admin";
  const canManage = role === "admin" || role === "dev";

  const [tab, setTab] = useState<Tab>("readme");
  const [status, setStatus] = useState<RepoDocStatus>({});
  const [readme, setReadme] = useState<RepoDoc | null>(null);
  const [onboarding, setOnboarding] = useState<RepoDoc | null>(null);
  const [progress, setProgress] = useState<OnboardingProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [pushing, setPushing] = useState(false);
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());
  const [showConfetti, setShowConfetti] = useState(false);

  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const copiedTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const confettiTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Cleanup all timers on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      if (copiedTimeoutRef.current) clearTimeout(copiedTimeoutRef.current);
      if (confettiTimeoutRef.current) clearTimeout(confettiTimeoutRef.current);
    };
  }, []);

  const loadData = useCallback(async () => {
    try {
      const s = await getDocsStatus(repoName);
      setStatus(s);

      if (s.readme) {
        try {
          const r = await getReadme(repoName);
          setReadme(r);
        } catch (e: unknown) {
          console.error("Erro ao carregar README:", e);
        }
      }
      if (s.onboarding_guide) {
        try {
          const o = await getOnboardingGuide(repoName);
          setOnboarding(o);
        } catch (e: unknown) {
          console.error("Erro ao carregar guia de onboarding:", e);
        }
      }

      try {
        const p = await getOnboardingProgress(repoName);
        setProgress(p);
      } catch (e: unknown) {
        console.error("Erro ao carregar progresso de onboarding:", e);
      }
    } catch (e: unknown) {
      console.error("Erro ao carregar status da documentacao:", e);
    }
    setLoading(false);
  }, [repoName]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Poll while generating
  useEffect(() => {
    if (!generating) return;
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    pollIntervalRef.current = setInterval(async () => {
      try {
        const s = await getDocsStatus(repoName);
        setStatus(s);
        const target = generating === "all" ? "readme" : generating;
        const docStatus = s[target as keyof RepoDocStatus];
        if (docStatus?.generated_at) {
          setGenerating(null);
          await loadData();
          toast.success("Documentacao gerada com sucesso!");
        }
      } catch (e: unknown) {
        console.error("Erro ao verificar status de geracao:", e);
      }
    }, 3000);
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [generating, repoName, loadData]);

  async function handleGenerate(docType: string) {
    if (!canManage) return;
    setGenerating(docType);
    try {
      await generateDocs(repoName, docType);
    } catch (e: any) {
      toast.error(e.message || "Erro ao gerar documentacao");
      setGenerating(null);
    }
  }

  async function handlePush() {
    if (!isAdmin) return;
    setPushing(true);
    try {
      await pushReadmeToGitHub(repoName);
      toast.success("README enviado para o GitHub!");
      await loadData();
    } catch (e: any) {
      toast.error(e.message || "Erro ao enviar para GitHub");
    }
    setPushing(false);
  }

  function handleCopy() {
    const content = tab === "readme" ? readme?.content : onboarding?.content;
    if (content) {
      navigator.clipboard.writeText(content);
      setCopied(true);
      if (copiedTimeoutRef.current) clearTimeout(copiedTimeoutRef.current);
      copiedTimeoutRef.current = setTimeout(() => setCopied(false), 2000);
    }
  }

  async function handleToggleStep(stepId: string) {
    // Toggle UI
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(stepId)) next.delete(stepId);
      else next.add(stepId);
      return next;
    });
  }

  async function handleCompleteStep(stepId: string) {
    try {
      const result = await completeOnboardingStep(repoName, stepId);
      setProgress({
        started: true,
        steps_total: result.steps_total,
        steps_completed: result.steps_completed,
        completed_steps: result.completed_steps,
      });
      if (result.is_complete) {
        setShowConfetti(true);
        if (confettiTimeoutRef.current) clearTimeout(confettiTimeoutRef.current);
        confettiTimeoutRef.current = setTimeout(() => setShowConfetti(false), 5000);
      }
    } catch (e: any) {
      toast.error(e.message || "Erro ao salvar progresso");
    }
  }

  const steps = onboarding ? parseOnboardingSteps(onboarding.content) : [];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-6 w-6 animate-spin text-accent" />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto p-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Link
          href="/dashboard"
          className="p-2 rounded-lg hover:bg-hover text-muted hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">Documentacao — {repoName}</h1>
          <p className="text-sm text-muted mt-0.5">
            {status.readme?.generated_at
              ? `README gerado em ${new Date(status.readme.generated_at).toLocaleDateString("pt-BR")}`
              : "Nenhum documento gerado ainda"}
          </p>
        </div>
        {canManage && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleGenerate("all")}
              disabled={!!generating}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-dark transition-colors disabled:opacity-50"
            >
              {generating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Gerando...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4" />
                  Regenerar tudo
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 rounded-lg bg-hover mb-6">
        <button
          onClick={() => setTab("readme")}
          className={cn(
            "flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors",
            tab === "readme" ? "bg-card-bg text-foreground shadow-sm" : "text-muted hover:text-foreground",
          )}
        >
          <FileText className="h-4 w-4" />
          README
        </button>
        <button
          onClick={() => setTab("onboarding")}
          className={cn(
            "flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors",
            tab === "onboarding" ? "bg-card-bg text-foreground shadow-sm" : "text-muted hover:text-foreground",
          )}
        >
          <GraduationCap className="h-4 w-4" />
          Onboarding
          {progress && progress.started && (
            <span className="text-xs bg-accent text-white rounded-full px-1.5 py-0.5">
              {progress.steps_completed}/{progress.steps_total}
            </span>
          )}
        </button>
      </div>

      {/* Content */}
      {tab === "readme" && (
        <div>
          {generating === "readme" || generating === "all" ? (
            <GeneratingState type="README" />
          ) : readme ? (
            <div>
              {/* Toolbar */}
              <div className="flex items-center gap-2 mb-4">
                <button
                  onClick={handleCopy}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-xs font-medium text-muted hover:text-foreground hover:bg-hover transition-colors"
                >
                  {copied ? <Check className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5" />}
                  {copied ? "Copiado!" : "Copiar markdown"}
                </button>
                {isAdmin && (
                  <button
                    onClick={handlePush}
                    disabled={pushing}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-xs font-medium text-muted hover:text-foreground hover:bg-hover transition-colors disabled:opacity-50"
                  >
                    {pushing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Upload className="h-3.5 w-3.5" />}
                    Push para GitHub
                  </button>
                )}
                {status.readme?.pushed_to_github && (
                  <span className="text-xs text-success">
                    Enviado em {status.readme.pushed_at ? new Date(status.readme.pushed_at).toLocaleDateString("pt-BR") : "—"}
                  </span>
                )}
                {canManage && (
                  <button
                    onClick={() => handleGenerate("readme")}
                    disabled={!!generating}
                    className="ml-auto inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-accent hover:bg-accent-surface transition-colors"
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                    Regenerar README
                  </button>
                )}
              </div>

              {/* Markdown content */}
              <div className="prose prose-sm max-w-none bg-card-bg border border-border rounded-xl p-6">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{readme.content}</ReactMarkdown>
              </div>
            </div>
          ) : (
            <EmptyState
              icon={FileText}
              title="README nao gerado"
              description="O Memora vai analisar o codigo e gerar um README completo automaticamente."
              actionLabel="Gerar README"
              onAction={() => handleGenerate("readme")}
              canAction={canManage}
              generating={!!generating}
            />
          )}
        </div>
      )}

      {tab === "onboarding" && (
        <div>
          {generating === "onboarding_guide" || generating === "all" ? (
            <GeneratingState type="Guia de Onboarding" />
          ) : onboarding && steps.length > 0 ? (
            <div>
              {/* Progress bar */}
              <div className="mb-6 p-4 rounded-xl bg-card-bg border border-border">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-medium">
                    {progress?.steps_completed ?? 0} de {steps.length} passos concluidos
                  </p>
                  {canManage && (
                    <button
                      onClick={() => handleGenerate("onboarding_guide")}
                      disabled={!!generating}
                      className="inline-flex items-center gap-1.5 text-xs text-accent hover:text-accent-dark transition-colors"
                    >
                      <RefreshCw className="h-3 w-3" />
                      Regenerar
                    </button>
                  )}
                </div>
                <div className="w-full h-2 bg-border/50 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-accent to-accent-light rounded-full transition-all duration-500"
                    style={{ width: `${steps.length > 0 ? ((progress?.steps_completed ?? 0) / steps.length) * 100 : 0}%` }}
                  />
                </div>
              </div>

              {/* Confetti */}
              {showConfetti && (
                <div className="mb-6 p-6 rounded-xl bg-success-surface border border-success/30 text-center">
                  <PartyPopper className="h-10 w-10 text-success mx-auto mb-2" />
                  <p className="text-lg font-bold text-success">Onboarding concluido!</p>
                  <p className="text-sm text-muted mt-1">Voce esta pronto para contribuir.</p>
                </div>
              )}

              {/* Steps */}
              <div className="space-y-2">
                {steps.map((step) => {
                  const isCompleted = progress?.completed_steps?.includes(step.id) ?? false;
                  const isExpanded = expandedSteps.has(step.id);

                  return (
                    <div
                      key={step.id}
                      className={cn(
                        "rounded-xl border transition-colors",
                        isCompleted ? "border-success/30 bg-success-surface/50" : "border-border bg-card-bg",
                      )}
                    >
                      <button
                        onClick={() => handleToggleStep(step.id)}
                        className="w-full flex items-center gap-3 px-4 py-3 text-left"
                      >
                        <div
                          className={cn(
                            "h-6 w-6 rounded-full flex items-center justify-center shrink-0 text-xs font-bold",
                            isCompleted ? "bg-success text-white" : "bg-hover text-muted",
                          )}
                        >
                          {isCompleted ? <Check className="h-3.5 w-3.5" /> : step.id.replace("step-", "")}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className={cn("text-sm font-medium", isCompleted && "line-through text-muted")}>
                            {step.title}
                          </p>
                          <p className="text-xs text-muted">
                            {step.file && <span className="font-mono">{step.file}</span>}
                            {step.file && step.time && " · "}
                            {step.time && <span>~{step.time}</span>}
                          </p>
                        </div>
                        {isExpanded ? (
                          <ChevronDown className="h-4 w-4 text-muted shrink-0" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-muted shrink-0" />
                        )}
                      </button>

                      {isExpanded && (
                        <div className="px-4 pb-4 border-t border-border/50">
                          <div className="prose prose-sm max-w-none mt-3 text-sm text-muted">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{step.content}</ReactMarkdown>
                          </div>
                          {!isCompleted && (
                            <button
                              onClick={() => handleCompleteStep(step.id)}
                              className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent text-white text-xs font-medium hover:bg-accent-dark transition-colors"
                            >
                              <Check className="h-3.5 w-3.5" />
                              Marcar como concluido
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <EmptyState
              icon={GraduationCap}
              title="Guia de onboarding nao gerado"
              description="O Memora vai criar um guia de leitura personalizado indicando o que ler primeiro e em qual ordem."
              actionLabel="Gerar Guia de Onboarding"
              onAction={() => handleGenerate("onboarding_guide")}
              canAction={canManage}
              generating={!!generating}
            />
          )}
        </div>
      )}
    </div>
  );
}

function GeneratingState({ type }: { type: string }) {
  const steps = [
    "Analisando estrutura do projeto...",
    "Identificando tecnologias...",
    "Gerando documentacao...",
  ];
  const [step, setStep] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setStep((prev) => (prev < steps.length - 1 ? prev + 1 : prev));
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center py-16">
      <Sparkles className="h-12 w-12 text-accent mb-4 animate-pulse" />
      <p className="text-lg font-medium mb-4">Gerando {type}...</p>
      <div className="space-y-2 w-64">
        {steps.map((s, i) => (
          <div key={i} className="flex items-center gap-2 text-sm">
            {i < step ? (
              <Check className="h-4 w-4 text-success shrink-0" />
            ) : i === step ? (
              <Loader2 className="h-4 w-4 text-accent animate-spin shrink-0" />
            ) : (
              <div className="h-4 w-4 rounded-full border border-border shrink-0" />
            )}
            <span className={cn(i <= step ? "text-foreground" : "text-muted")}>{s}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  canAction,
  generating,
}: {
  icon: any;
  title: string;
  description: string;
  actionLabel: string;
  onAction: () => void;
  canAction: boolean;
  generating: boolean;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="h-16 w-16 rounded-2xl bg-accent-surface flex items-center justify-center mb-4">
        <Icon className="h-8 w-8 text-accent" />
      </div>
      <p className="text-lg font-medium mb-2">{title}</p>
      <p className="text-sm text-muted max-w-md mb-6">{description}</p>
      {canAction && (
        <button
          onClick={onAction}
          disabled={generating}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-dark transition-colors disabled:opacity-50"
        >
          {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          {actionLabel}
        </button>
      )}
    </div>
  );
}
