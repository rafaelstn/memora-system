"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  Brain,
  CheckCircle2,
  Database,
  Globe,
  Loader2,
  MessageSquare,
  Sparkles,
  Github,
  Send,
  ArrowLeft,
} from "lucide-react";
import toast from "react-hot-toast";
import { useAuth } from "@/lib/hooks/useAuth";
import {
  updateOnboardingStep,
  ingestRepositoryStream,
  getGitHubStatus,
  listGitHubRepos,
  askQuestionStream,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const STEPS = [
  { id: 0, label: "Bem-vindo", icon: Sparkles },
  { id: 1, label: "Repositorio", icon: Database },
  { id: 2, label: "Indexacao", icon: Database },
  { id: 3, label: "Primeira pergunta", icon: MessageSquare },
];

export default function SetupPage() {
  const { user, isLoading: authLoading, refreshUser } = useAuth();
  const router = useRouter();

  const [currentStep, setCurrentStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [skipConfirm, setSkipConfirm] = useState(false);

  // Step 1 - Repository
  const [repoUrl, setRepoUrl] = useState("");
  const [repoBranch, setRepoBranch] = useState("main");
  const [repoToken, setRepoToken] = useState("");
  const [ghConnected, setGhConnected] = useState(false);
  const [ghRepos, setGhRepos] = useState<string[]>([]);
  const [selectedGhRepo, setSelectedGhRepo] = useState("");
  const [repoMode, setRepoMode] = useState<"url" | "github">("url");
  const [ghLoading, setGhLoading] = useState(false);

  // Step 2 - Indexing
  const [indexing, setIndexing] = useState(false);
  const [indexProgress, setIndexProgress] = useState<{
    stage: string;
    percent: number;
    detail: string;
  } | null>(null);
  const [indexResult, setIndexResult] = useState<{
    chunks: number;
    files: number;
    repo: string;
  } | null>(null);
  const [indexError, setIndexError] = useState<string | null>(null);

  // Step 3 - First question
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [answer, setAnswer] = useState("");
  const [answerDone, setAnswerDone] = useState(false);
  const answerRef = useRef<HTMLDivElement>(null);

  // Computed repo name for display
  const repoName =
    repoMode === "github"
      ? selectedGhRepo.split("/").pop() || selectedGhRepo
      : repoUrl
          .trim()
          .split("/")
          .pop()
          ?.replace(".git", "") || "repositorio";

  // Load saved step on mount
  useEffect(() => {
    if (!authLoading && user) {
      if (user.onboarding_completed) {
        router.push("/dashboard");
        return;
      }
      if (user.role !== "admin") {
        router.push("/dashboard");
        return;
      }
      // Resume from saved step (but never past step 1 without repo selected)
      if (user.onboarding_step <= 1) {
        setCurrentStep(user.onboarding_step);
      }
    }
  }, [authLoading, user, router]);

  // Load GitHub status when reaching repo step
  useEffect(() => {
    if (currentStep === 1) {
      setGhLoading(true);
      getGitHubStatus()
        .then((s) => {
          setGhConnected(s.connected);
          if (s.connected) {
            setRepoMode("github");
            listGitHubRepos()
              .then((repos) =>
                setGhRepos(
                  repos.map((r: { full_name: string }) => r.full_name)
                )
              )
              .catch(() => {});
          }
        })
        .catch(() => {})
        .finally(() => setGhLoading(false));
    }
  }, [currentStep]);

  const saveStep = useCallback(
    async (step: number, completed = false) => {
      try {
        await updateOnboardingStep(step, completed);
        if (completed) {
          await refreshUser();
        }
      } catch {
        // silently fail
      }
    },
    [refreshUser]
  );

  async function goToStep(step: number) {
    setSaving(true);
    try {
      await saveStep(step);
      setCurrentStep(step);
    } finally {
      setSaving(false);
    }
  }

  // --- Step handlers ---

  function handleConnectGitHub() {
    const w = window.open("/api/integrations/github/connect", "_blank");
    // Poll for connection
    const interval = setInterval(async () => {
      try {
        const status = await getGitHubStatus();
        if (status.connected) {
          clearInterval(interval);
          setGhConnected(true);
          setRepoMode("github");
          const repos = await listGitHubRepos();
          setGhRepos(
            repos.map((r: { full_name: string }) => r.full_name)
          );
          w?.close();
        }
      } catch {
        /* noop */
      }
    }, 2000);
    // Stop polling after 2 minutes
    setTimeout(() => clearInterval(interval), 120000);
  }

  async function handleStartIndexing() {
    const repoPath =
      repoMode === "github" ? selectedGhRepo : repoUrl.trim();
    if (!repoPath) return;

    setIndexing(true);
    setIndexProgress(null);
    setIndexResult(null);
    setIndexError(null);

    const name =
      repoPath.split("/").pop()?.replace(".git", "") || repoPath;

    const fullPath =
      repoMode === "url"
        ? `${repoUrl.trim()}${repoToken ? `|||${repoToken}` : ""}${repoBranch !== "main" ? `@@@${repoBranch}` : ""}`
        : repoPath;

    await ingestRepositoryStream(
      fullPath,
      name,
      (stage, percent, detail) => {
        setIndexProgress({ stage, percent, detail });
      },
      (result) => {
        setIndexResult({
          chunks: result.chunks_created,
          files: result.files_processed,
          repo: result.repo_name,
        });
        setIndexing(false);
      },
      (error) => {
        setIndexError(error);
        setIndexing(false);
      }
    );
  }

  async function handleAsk() {
    if (!question.trim() || asking) return;
    setAsking(true);
    setAnswer("");
    setAnswerDone(false);

    const repo =
      indexResult?.repo ||
      (repoMode === "github"
        ? selectedGhRepo.split("/").pop() || ""
        : repoUrl
            .trim()
            .split("/")
            .pop()
            ?.replace(".git", "") || "");

    askQuestionStream(
      repo,
      question,
      (text) => {
        setAnswer((prev) => prev + text);
        // Auto-scroll
        if (answerRef.current) {
          answerRef.current.scrollTop =
            answerRef.current.scrollHeight;
        }
      },
      () => {
        /* sources - ignore in wizard */
      },
      () => {
        setAsking(false);
        setAnswerDone(true);
      },
      (error) => {
        setAnswer(`Erro: ${error}`);
        setAsking(false);
        setAnswerDone(true);
      }
    );
  }

  async function handleSkip() {
    if (!skipConfirm) {
      setSkipConfirm(true);
      return;
    }
    setSaving(true);
    try {
      await saveStep(4, true);
      toast.success("Voce pode configurar tudo depois nas configuracoes.");
      router.push("/dashboard");
    } catch {
      toast.error("Erro ao pular setup");
    } finally {
      setSaving(false);
    }
  }

  async function handleFinish() {
    setSaving(true);
    try {
      await saveStep(4, true);
      toast.success("Memora configurado com sucesso!");
      router.push("/dashboard");
    } catch {
      toast.error("Erro ao finalizar setup");
    } finally {
      setSaving(false);
    }
  }

  // --- Loading ---
  if (authLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <Loader2 size={32} className="animate-spin text-accent" />
      </div>
    );
  }

  if (!user) {
    router.push("/auth/signin");
    return null;
  }

  const selectedRepo =
    repoMode === "github" ? !!selectedGhRepo : !!repoUrl.trim();

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Progress bar */}
      <div className="sticky top-0 z-10 bg-card-bg border-b border-border">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex items-center justify-between">
            {STEPS.map((step, i) => (
              <div key={step.id} className="flex items-center">
                <div
                  className={cn(
                    "flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium transition-colors",
                    i < currentStep
                      ? "bg-accent text-white"
                      : i === currentStep
                        ? "bg-accent text-white ring-2 ring-accent/30"
                        : "bg-muted/20 text-muted"
                  )}
                >
                  {i < currentStep ? (
                    <CheckCircle2 size={16} />
                  ) : (
                    i + 1
                  )}
                </div>
                {i < STEPS.length - 1 && (
                  <div
                    className={cn(
                      "w-8 sm:w-16 md:w-24 h-0.5 mx-1",
                      i < currentStep ? "bg-accent" : "bg-muted/20"
                    )}
                  />
                )}
              </div>
            ))}
          </div>
          <div className="flex justify-between text-xs text-muted mt-2">
            {STEPS.map((step) => (
              <span
                key={step.id}
                className="w-16 text-center truncate hidden sm:block"
              >
                {step.label}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex flex-col">
        <div className="max-w-2xl w-full mx-auto px-4 sm:px-6 py-8 sm:py-12 flex-1">
          {/* STEP 0 - Bem-vindo */}
          {currentStep === 0 && (
            <div className="text-center space-y-8">
              <div className="flex justify-center">
                <div className="w-20 h-20 rounded-2xl bg-accent/10 flex items-center justify-center">
                  <Brain size={40} className="text-accent" />
                </div>
              </div>
              <div className="space-y-3">
                <h1 className="text-3xl font-bold">
                  Bem-vindo ao Memora
                </h1>
                <p className="text-lg text-muted max-w-md mx-auto">
                  Vamos configurar tudo em menos de 5 minutos.
                </p>
              </div>
              <p className="text-sm text-muted max-w-lg mx-auto">
                O Memora indexa o codigo-fonte da sua empresa e cria um
                assistente inteligente que responde perguntas tecnicas
                do seu time.
              </p>
              <button
                onClick={() => goToStep(1)}
                disabled={saving}
                className="inline-flex items-center gap-2 px-6 py-3 bg-accent text-white rounded-lg font-medium hover:bg-accent/90 transition-colors disabled:opacity-50"
              >
                {saving ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : null}
                Comecar configuracao
                <ArrowRight size={18} />
              </button>
              <div>
                {!skipConfirm ? (
                  <button
                    onClick={handleSkip}
                    className="text-sm text-muted hover:text-foreground transition-colors"
                  >
                    Pular e ir direto ao dashboard
                  </button>
                ) : (
                  <div className="space-y-2">
                    <p className="text-sm text-muted">
                      Tem certeza? Sem um repositorio indexado, o
                      Memora nao conseguira responder perguntas.
                    </p>
                    <div className="flex items-center justify-center gap-3">
                      <button
                        onClick={() => setSkipConfirm(false)}
                        className="text-sm text-muted hover:text-foreground"
                      >
                        Cancelar
                      </button>
                      <button
                        onClick={handleSkip}
                        disabled={saving}
                        className="text-sm text-red-500 hover:text-red-400 font-medium"
                      >
                        {saving ? "Pulando..." : "Sim, pular"}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* STEP 1 - Conectar repositorio */}
          {currentStep === 1 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold">
                  Conecte seu primeiro repositorio
                </h2>
                <p className="text-muted mt-1">
                  Escolha como voce quer conectar o codigo-fonte
                </p>
              </div>

              {/* Option cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <button
                  onClick={() => {
                    if (!ghConnected) {
                      handleConnectGitHub();
                    } else {
                      setRepoMode("github");
                    }
                  }}
                  className={cn(
                    "p-5 rounded-xl border-2 text-left transition-all",
                    repoMode === "github" && ghConnected
                      ? "border-accent bg-accent/5"
                      : "border-border bg-card-bg hover:border-accent/50"
                  )}
                >
                  <Github
                    size={24}
                    className="mb-3 text-foreground"
                  />
                  <div className="font-semibold">GitHub</div>
                  <p className="text-sm text-muted mt-1">
                    {ghConnected
                      ? "Conectado — selecione um repo"
                      : "Conectar via OAuth"}
                  </p>
                  {ghConnected && (
                    <div className="mt-2 flex items-center gap-1.5 text-xs text-green-500">
                      <CheckCircle2 size={12} /> Conectado
                    </div>
                  )}
                </button>
                <button
                  onClick={() => setRepoMode("url")}
                  className={cn(
                    "p-5 rounded-xl border-2 text-left transition-all",
                    repoMode === "url"
                      ? "border-accent bg-accent/5"
                      : "border-border bg-card-bg hover:border-accent/50"
                  )}
                >
                  <Globe
                    size={24}
                    className="mb-3 text-foreground"
                  />
                  <div className="font-semibold">URL direta</div>
                  <p className="text-sm text-muted mt-1">
                    Cole a URL de um repositorio Git
                  </p>
                </button>
              </div>

              {/* GitHub repo selector */}
              {repoMode === "github" && ghConnected && (
                <div className="bg-card-bg rounded-xl border border-border p-5 space-y-3">
                  <label className="block text-sm font-medium">
                    Selecione um repositorio
                  </label>
                  {ghLoading || ghRepos.length === 0 ? (
                    <div className="flex items-center gap-2 text-sm text-muted">
                      <Loader2
                        size={14}
                        className="animate-spin"
                      />
                      Carregando repositorios...
                    </div>
                  ) : (
                    <select
                      value={selectedGhRepo}
                      onChange={(e) =>
                        setSelectedGhRepo(e.target.value)
                      }
                      className="w-full px-3 py-2.5 rounded-lg border border-border bg-background text-foreground outline-none"
                    >
                      <option value="">Selecione...</option>
                      {ghRepos.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              )}

              {/* URL input */}
              {repoMode === "url" && (
                <div className="bg-card-bg rounded-xl border border-border p-5 space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1.5">
                      URL do repositorio Git
                    </label>
                    <input
                      type="text"
                      value={repoUrl}
                      onChange={(e) => setRepoUrl(e.target.value)}
                      placeholder="https://github.com/usuario/repositorio"
                      className="w-full px-3 py-2.5 rounded-lg border border-border bg-background text-foreground focus:ring-2 focus:ring-accent/50 focus:border-accent outline-none text-sm"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium mb-1.5">
                        Branch
                      </label>
                      <input
                        type="text"
                        value={repoBranch}
                        onChange={(e) =>
                          setRepoBranch(e.target.value)
                        }
                        placeholder="main"
                        className="w-full px-3 py-2.5 rounded-lg border border-border bg-background text-foreground outline-none text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1.5">
                        Token{" "}
                        <span className="text-muted">
                          (se privado)
                        </span>
                      </label>
                      <input
                        type="password"
                        value={repoToken}
                        onChange={(e) =>
                          setRepoToken(e.target.value)
                        }
                        placeholder="ghp_..."
                        className="w-full px-3 py-2.5 rounded-lg border border-border bg-background text-foreground outline-none text-sm font-mono"
                      />
                    </div>
                  </div>
                </div>
              )}

              <div className="flex justify-between pt-4">
                <button
                  onClick={() => setCurrentStep(0)}
                  className="flex items-center gap-1 text-sm text-muted hover:text-foreground transition-colors"
                >
                  <ArrowLeft size={16} /> Voltar
                </button>
                <button
                  onClick={() => {
                    setCurrentStep(2);
                    // Auto-start indexing when entering step 2
                    setTimeout(handleStartIndexing, 100);
                  }}
                  disabled={!selectedRepo || saving}
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-accent text-white rounded-lg font-medium hover:bg-accent/90 transition-colors disabled:opacity-50"
                >
                  Continuar <ArrowRight size={16} />
                </button>
              </div>

              {/* Skip link */}
              <div className="text-center">
                <button
                  onClick={handleSkip}
                  className="text-sm text-muted hover:text-foreground transition-colors"
                >
                  {skipConfirm
                    ? "Confirmar: pular setup"
                    : "Pular e ir direto ao dashboard"}
                </button>
              </div>
            </div>
          )}

          {/* STEP 2 - Indexando */}
          {currentStep === 2 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold">
                  Indexando {repoName}...
                </h2>
                <p className="text-muted mt-1">
                  Analisando o codigo-fonte e criando a base de
                  conhecimento
                </p>
              </div>

              {/* Progress */}
              {indexing && (
                <div className="bg-card-bg rounded-xl border border-border p-6 space-y-4">
                  <div className="flex items-center gap-3">
                    <Loader2
                      size={20}
                      className="animate-spin text-accent"
                    />
                    <span className="font-medium">
                      {indexProgress?.detail || "Preparando..."}
                    </span>
                  </div>
                  <div className="w-full h-3 bg-muted/20 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent rounded-full transition-all duration-500"
                      style={{
                        width: `${indexProgress?.percent || 0}%`,
                      }}
                    />
                  </div>
                  <p className="text-sm text-muted">
                    {indexProgress?.stage || "iniciando"} —{" "}
                    {indexProgress?.percent || 0}%
                  </p>
                </div>
              )}

              {/* Error */}
              {indexError && (
                <div className="bg-red-500/5 rounded-xl border border-red-500/20 p-6">
                  <p className="text-red-500 font-medium">
                    Erro na indexacao
                  </p>
                  <p className="text-sm text-muted mt-1">
                    {indexError}
                  </p>
                  <button
                    onClick={() => {
                      setIndexError(null);
                      handleStartIndexing();
                    }}
                    className="mt-3 text-sm text-accent hover:underline"
                  >
                    Tentar novamente
                  </button>
                </div>
              )}

              {/* Success */}
              {indexResult && (
                <div className="bg-green-500/5 rounded-xl border border-green-500/20 p-6 space-y-3">
                  <div className="flex items-center gap-3">
                    <CheckCircle2
                      size={28}
                      className="text-green-500"
                    />
                    <div>
                      <p className="font-semibold text-green-600 text-lg">
                        {indexResult.files.toLocaleString()} arquivos
                        indexados
                      </p>
                      <p className="text-sm text-muted">
                        {indexResult.chunks.toLocaleString()} chunks
                        de codigo criados. Seu Memora esta pronto.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              <div className="flex justify-between pt-4">
                <button
                  onClick={() => {
                    setCurrentStep(1);
                    setIndexResult(null);
                    setIndexError(null);
                    setIndexProgress(null);
                    setIndexing(false);
                  }}
                  className="flex items-center gap-1 text-sm text-muted hover:text-foreground transition-colors"
                >
                  <ArrowLeft size={16} /> Voltar
                </button>
                <button
                  onClick={() => goToStep(3)}
                  disabled={!indexResult || saving}
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-accent text-white rounded-lg font-medium hover:bg-accent/90 transition-colors disabled:opacity-50"
                >
                  {saving ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : null}
                  Continuar <ArrowRight size={16} />
                </button>
              </div>
            </div>
          )}

          {/* STEP 3 - Primeira pergunta */}
          {currentStep === 3 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold">
                  Faca sua primeira pergunta
                </h2>
                <p className="text-muted mt-1">
                  Experimente perguntar algo sobre o sistema que voce
                  acabou de indexar.
                </p>
              </div>

              {/* Question input */}
              <div className="bg-card-bg rounded-xl border border-border p-5 space-y-4">
                <textarea
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => {
                    if (
                      e.key === "Enter" &&
                      !e.shiftKey &&
                      !asking
                    ) {
                      e.preventDefault();
                      handleAsk();
                    }
                  }}
                  rows={3}
                  placeholder="Ex: Como funciona o processo de autenticacao neste sistema?"
                  className="w-full px-3 py-2.5 rounded-lg border border-border bg-background text-foreground focus:ring-2 focus:ring-accent/50 focus:border-accent outline-none text-sm resize-none"
                />
                <button
                  onClick={handleAsk}
                  disabled={asking || !question.trim()}
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-accent text-white rounded-lg font-medium hover:bg-accent/90 transition-colors disabled:opacity-50"
                >
                  {asking ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <Send size={16} />
                  )}
                  {asking ? "Pensando..." : "Perguntar"}
                </button>
              </div>

              {/* Answer */}
              {answer && (
                <div
                  ref={answerRef}
                  className="bg-card-bg rounded-xl border border-border p-5 max-h-96 overflow-y-auto"
                >
                  <div className="flex items-center gap-2 mb-3">
                    <Brain size={16} className="text-accent" />
                    <span className="text-sm font-medium text-accent">
                      Memora
                    </span>
                    {asking && (
                      <Loader2
                        size={12}
                        className="animate-spin text-muted"
                      />
                    )}
                  </div>
                  <div className="prose prose-sm prose-invert max-w-none text-foreground whitespace-pre-wrap text-sm leading-relaxed">
                    {answer}
                  </div>
                </div>
              )}

              {/* Finish button */}
              <div className="flex justify-between pt-4">
                <button
                  onClick={() => setCurrentStep(2)}
                  className="flex items-center gap-1 text-sm text-muted hover:text-foreground transition-colors"
                >
                  <ArrowLeft size={16} /> Voltar
                </button>
                {answerDone ? (
                  <button
                    onClick={handleFinish}
                    disabled={saving}
                    className="inline-flex items-center gap-2 px-6 py-3 bg-accent text-white rounded-lg font-medium hover:bg-accent/90 transition-colors disabled:opacity-50"
                  >
                    {saving ? (
                      <Loader2
                        size={16}
                        className="animate-spin"
                      />
                    ) : null}
                    Ir para o Dashboard
                    <ArrowRight size={18} />
                  </button>
                ) : (
                  <button
                    onClick={handleFinish}
                    disabled={saving}
                    className="text-sm text-muted hover:text-foreground transition-colors"
                  >
                    Pular e ir para o dashboard
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
