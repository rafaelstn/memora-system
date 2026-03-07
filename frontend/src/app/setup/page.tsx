"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  Brain,
  CheckCircle2,
  ChevronRight,
  Database,
  Globe,
  Loader2,
  Mail,
  Building2,
  Sparkles,
  Zap,
  AlertCircle,
  SkipForward,
  ExternalLink,
  Github,
} from "lucide-react";
import toast from "react-hot-toast";
import { useAuth } from "@/lib/hooks/useAuth";
import {
  updateOnboardingStep,
  updateOrgName,
  testLLMConnection,
  createLLMProvider,
  setDefaultLLMProvider,
  ingestRepositoryStream,
  getSMTPStatus,
  testSMTP,
  getGitHubStatus,
  listGitHubRepos,
} from "@/lib/api";
import type { LLMProviderType } from "@/lib/types";
import { cn } from "@/lib/utils";

const STEPS = [
  { id: 0, label: "Bem-vindo", icon: Sparkles },
  { id: 1, label: "Organizacao", icon: Building2 },
  { id: 2, label: "Provedor de IA", icon: Brain },
  { id: 3, label: "Email", icon: Mail, optional: true },
  { id: 4, label: "Repositorio", icon: Database },
];

const PROVIDER_CARDS: {
  value: LLMProviderType;
  label: string;
  subtitle: string;
  badge?: string;
}[] = [
  { value: "openai", label: "OpenAI", subtitle: "GPT-4o", badge: "Recomendado" },
  { value: "anthropic", label: "Anthropic", subtitle: "Claude", badge: undefined },
  { value: "groq", label: "Groq", subtitle: "Llama", badge: "Gratuito" },
];

const PROVIDER_MODELS: Record<string, { id: string; label: string }[]> = {
  openai: [
    { id: "gpt-4o", label: "GPT-4o" },
    { id: "gpt-4o-mini", label: "GPT-4o Mini" },
    { id: "gpt-4.1", label: "GPT-4.1" },
    { id: "gpt-4.1-mini", label: "GPT-4.1 Mini" },
  ],
  anthropic: [
    { id: "claude-sonnet-4-6", label: "Claude Sonnet 4.6" },
    { id: "claude-haiku-4-5-20251001", label: "Claude Haiku 4.5" },
    { id: "claude-opus-4-5-20250514", label: "Claude Opus 4.5" },
  ],
  groq: [
    { id: "llama-3.1-70b-versatile", label: "Llama 3.1 70B" },
    { id: "llama-3.1-8b-instant", label: "Llama 3.1 8B" },
    { id: "mixtral-8x7b-32768", label: "Mixtral 8x7B" },
  ],
};

export default function SetupPage() {
  const { user, isLoading: authLoading, refreshUser } = useAuth();
  const router = useRouter();

  const [currentStep, setCurrentStep] = useState(0);
  const [saving, setSaving] = useState(false);

  // Step 1 — Org name
  const [orgName, setOrgName] = useState("");
  const [appUrl, setAppUrl] = useState("");

  // Step 2 — LLM provider
  const [selectedProvider, setSelectedProvider] = useState<LLMProviderType | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [modelId, setModelId] = useState("");
  const [testingConnection, setTestingConnection] = useState(false);
  const [connectionResult, setConnectionResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [providerSaved, setProviderSaved] = useState(false);

  // Step 3 — Email
  const [emailSkipped, setEmailSkipped] = useState(false);
  const [smtpConfigured, setSmtpConfigured] = useState(false);
  const [smtpLoading, setSmtpLoading] = useState(true);
  const [smtpTesting, setSmtpTesting] = useState(false);

  // Step 4 — Repository
  const [repoUrl, setRepoUrl] = useState("");
  const [repoBranch, setRepoBranch] = useState("main");
  const [repoToken, setRepoToken] = useState("");
  const [indexing, setIndexing] = useState(false);
  const [indexProgress, setIndexProgress] = useState<{ stage: string; percent: number; detail: string } | null>(null);
  const [indexResult, setIndexResult] = useState<{ chunks: number; repo: string } | null>(null);
  const [ghConnected, setGhConnected] = useState(false);
  const [ghRepos, setGhRepos] = useState<string[]>([]);
  const [selectedGhRepo, setSelectedGhRepo] = useState("");
  const [repoMode, setRepoMode] = useState<"url" | "github">("url");

  // Summary data for final step
  const [setupSummary, setSetupSummary] = useState({
    orgName: "",
    provider: "",
    model: "",
    emailConfigured: false,
    repoName: "",
    chunks: 0,
  });

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
      setCurrentStep(user.onboarding_step);
      if (user.org_name) setOrgName(user.org_name);
    }
  }, [authLoading, user, router]);

  // Load SMTP status when reaching email step
  useEffect(() => {
    if (currentStep === 3) {
      setSmtpLoading(true);
      getSMTPStatus()
        .then((s) => setSmtpConfigured(s.configured))
        .catch(() => {})
        .finally(() => setSmtpLoading(false));
    }
  }, [currentStep]);

  // Load GitHub status when reaching repo step
  useEffect(() => {
    if (currentStep === 4) {
      getGitHubStatus()
        .then((s) => {
          setGhConnected(s.connected);
          if (s.connected) {
            setRepoMode("github");
            listGitHubRepos().then((repos) => setGhRepos(repos.map((r: { full_name: string }) => r.full_name))).catch(() => {});
          }
        })
        .catch(() => {});
    }
  }, [currentStep]);

  const saveStep = useCallback(async (step: number, completed = false) => {
    try {
      await updateOnboardingStep(step, completed);
      if (completed) {
        await refreshUser();
      }
    } catch {
      // silently fail — step save is best-effort
    }
  }, [refreshUser]);

  async function goNext() {
    setSaving(true);
    try {
      const nextStep = currentStep + 1;
      await saveStep(nextStep);
      setCurrentStep(nextStep);
    } finally {
      setSaving(false);
    }
  }

  function goBack() {
    if (currentStep > 0) setCurrentStep(currentStep - 1);
  }

  // --- Step handlers ---

  async function handleOrgNameSave() {
    if (!orgName.trim()) {
      toast.error("Informe o nome da organizacao");
      return;
    }
    setSaving(true);
    try {
      await updateOrgName(orgName.trim(), appUrl.trim() || undefined);
      setSetupSummary((s) => ({ ...s, orgName: orgName.trim() }));
      await goNext();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  }

  async function handleTestConnection() {
    if (!selectedProvider || !apiKey.trim() || !modelId) return;
    setTestingConnection(true);
    setConnectionResult(null);
    try {
      const result = await testLLMConnection({
        provider: selectedProvider,
        model_id: modelId,
        api_key: apiKey.trim(),
      });
      if (result.status === "ok") {
        setConnectionResult({ ok: true, message: `Conexao funcionando (${result.latency_ms}ms)` });
      } else {
        setConnectionResult({ ok: false, message: result.error || "Erro desconhecido" });
      }
    } catch (e: unknown) {
      setConnectionResult({ ok: false, message: e instanceof Error ? e.message : "Erro ao testar" });
    } finally {
      setTestingConnection(false);
    }
  }

  async function handleProviderSave() {
    if (!connectionResult?.ok) {
      toast.error("Teste a conexao antes de continuar");
      return;
    }
    setSaving(true);
    try {
      const provider = await createLLMProvider({
        name: `${selectedProvider} (setup)`,
        provider: selectedProvider!,
        model_id: modelId,
        api_key: apiKey.trim(),
      });
      await setDefaultLLMProvider(provider.id);
      setProviderSaved(true);
      const modelLabel = PROVIDER_MODELS[selectedProvider!]?.find((m) => m.id === modelId)?.label || modelId;
      setSetupSummary((s) => ({
        ...s,
        provider: PROVIDER_CARDS.find((p) => p.value === selectedProvider)?.label || "",
        model: modelLabel,
      }));
      await goNext();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Erro ao salvar provedor");
    } finally {
      setSaving(false);
    }
  }

  async function handleSkipEmail() {
    setEmailSkipped(true);
    setSetupSummary((s) => ({ ...s, emailConfigured: false }));
    await goNext();
  }

  async function handleTestSmtp() {
    setSmtpTesting(true);
    try {
      const res = await testSMTP();
      if (res.status === "ok") {
        toast.success("Email de teste enviado com sucesso!");
        setSmtpConfigured(true);
        setSetupSummary((s) => ({ ...s, emailConfigured: true }));
      } else {
        toast.error(res.message || "Falha ao enviar email de teste");
      }
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Erro ao testar SMTP");
    } finally {
      setSmtpTesting(false);
    }
  }

  async function handleEmailContinue() {
    setSetupSummary((s) => ({ ...s, emailConfigured: smtpConfigured }));
    await goNext();
  }

  async function handleStartIndexing() {
    const repoPath = repoMode === "github" ? selectedGhRepo : repoUrl.trim();
    if (!repoPath) {
      toast.error("Informe o repositorio");
      return;
    }

    setIndexing(true);
    setIndexProgress(null);
    setIndexResult(null);

    const repoName = repoPath.split("/").pop()?.replace(".git", "") || repoPath;

    const fullPath = repoMode === "url"
      ? `${repoUrl.trim()}${repoToken ? `|||${repoToken}` : ""}${repoBranch !== "main" ? `@@@${repoBranch}` : ""}`
      : repoPath;

    await ingestRepositoryStream(
      fullPath,
      repoName,
      (stage, percent, detail) => {
        setIndexProgress({ stage, percent, detail });
      },
      (result) => {
        setIndexResult({ chunks: result.chunks_created, repo: result.repo_name });
        setSetupSummary((s) => ({ ...s, repoName: result.repo_name, chunks: result.chunks_created }));
        setIndexing(false);
      },
      (error) => {
        toast.error(error);
        setIndexing(false);
      },
    );
  }

  async function handleFinish() {
    setSaving(true);
    try {
      await saveStep(5, true);
      toast.success("Memora configurado com sucesso!");
      router.push("/dashboard");
    } catch {
      toast.error("Erro ao finalizar setup");
    } finally {
      setSaving(false);
    }
  }

  // --- Loading state ---
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

  // --- Render ---
  return (
    <div className="min-h-screen bg-background">
      {/* Progress bar */}
      {currentStep > 0 && currentStep <= 4 && (
        <div className="sticky top-0 z-10 bg-card-bg border-b border-border">
          <div className="max-w-3xl mx-auto px-6 py-4">
            <div className="flex items-center justify-between mb-3">
              {STEPS.map((step, i) => (
                <div key={step.id} className="flex items-center">
                  <div
                    className={cn(
                      "flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium transition-colors",
                      i < currentStep
                        ? "bg-accent text-white"
                        : i === currentStep
                          ? "bg-accent text-white ring-2 ring-accent/30"
                          : "bg-muted/20 text-muted",
                    )}
                  >
                    {i < currentStep ? <CheckCircle2 size={16} /> : i + 1}
                  </div>
                  {i < STEPS.length - 1 && (
                    <div
                      className={cn(
                        "w-12 sm:w-20 h-0.5 mx-1",
                        i < currentStep ? "bg-accent" : "bg-muted/20",
                      )}
                    />
                  )}
                </div>
              ))}
            </div>
            <div className="flex justify-between text-xs text-muted">
              {STEPS.map((step) => (
                <span key={step.id} className="w-16 text-center truncate">
                  {step.label}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="max-w-2xl mx-auto px-6 py-12">
        {/* STEP 0 — Bem-vindo */}
        {currentStep === 0 && (
          <div className="text-center space-y-8">
            <div className="flex justify-center">
              <div className="w-20 h-20 rounded-2xl bg-accent/10 flex items-center justify-center">
                <Brain size={40} className="text-accent" />
              </div>
            </div>
            <div className="space-y-3">
              <h1 className="text-3xl font-bold">Bem-vindo ao Memora</h1>
              <p className="text-lg text-muted max-w-md mx-auto">
                Vamos configurar seu sistema em menos de 10 minutos
              </p>
            </div>
            <div className="bg-card-bg rounded-xl border border-border p-6 text-left space-y-4">
              <h3 className="font-semibold text-sm text-muted uppercase tracking-wide">
                O que vamos configurar:
              </h3>
              <div className="space-y-3">
                {[
                  { icon: Building2, text: "Nome da sua organizacao" },
                  { icon: Brain, text: "Provedor de IA para analises" },
                  { icon: Mail, text: "Notificacoes por email (opcional)" },
                  { icon: Database, text: "Seu primeiro repositorio" },
                ].map(({ icon: Icon, text }) => (
                  <div key={text} className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center">
                      <Icon size={16} className="text-accent" />
                    </div>
                    <span className="text-sm">{text}</span>
                  </div>
                ))}
              </div>
            </div>
            <button
              onClick={goNext}
              disabled={saving}
              className="inline-flex items-center gap-2 px-6 py-3 bg-accent text-white rounded-lg font-medium hover:bg-accent/90 transition-colors disabled:opacity-50"
            >
              {saving ? <Loader2 size={18} className="animate-spin" /> : null}
              Comecar configuracao
              <ArrowRight size={18} />
            </button>
          </div>
        )}

        {/* STEP 1 — Nome da organizacao */}
        {currentStep === 1 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold">Como sua empresa se chama?</h2>
              <p className="text-muted mt-1">Esse nome aparecera no sistema para todos os usuarios</p>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1.5">Nome da organizacao</label>
                <input
                  type="text"
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  placeholder="Ex: Acme Tecnologia"
                  className="w-full px-3 py-2.5 rounded-lg border border-border bg-background text-foreground focus:ring-2 focus:ring-accent/50 focus:border-accent outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  URL do sistema <span className="text-muted">(opcional)</span>
                </label>
                <input
                  type="url"
                  value={appUrl}
                  onChange={(e) => setAppUrl(e.target.value)}
                  placeholder="Ex: https://app.acme.com.br"
                  className="w-full px-3 py-2.5 rounded-lg border border-border bg-background text-foreground focus:ring-2 focus:ring-accent/50 focus:border-accent outline-none"
                />
                <p className="text-xs text-muted mt-1">Usado para o Teste Ativo de Seguranca</p>
              </div>
            </div>
            <div className="flex justify-between pt-4">
              <button onClick={goBack} className="flex items-center gap-1 text-sm text-muted hover:text-foreground transition-colors">
                <ArrowLeft size={16} /> Voltar
              </button>
              <button
                onClick={handleOrgNameSave}
                disabled={saving || !orgName.trim()}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-accent text-white rounded-lg font-medium hover:bg-accent/90 transition-colors disabled:opacity-50"
              >
                {saving ? <Loader2 size={16} className="animate-spin" /> : null}
                Continuar <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* STEP 2 — Provedor de IA */}
        {currentStep === 2 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold">Configure o provedor de IA</h2>
              <p className="text-muted mt-1">O Memora precisa de ao menos um provedor para funcionar</p>
            </div>

            {/* Provider cards */}
            <div className="grid grid-cols-3 gap-3">
              {PROVIDER_CARDS.map((p) => (
                <button
                  key={p.value}
                  onClick={() => {
                    setSelectedProvider(p.value);
                    setModelId(PROVIDER_MODELS[p.value]?.[0]?.id || "");
                    setConnectionResult(null);
                    setApiKey("");
                  }}
                  className={cn(
                    "relative p-4 rounded-xl border-2 text-center transition-all hover:border-accent/50",
                    selectedProvider === p.value
                      ? "border-accent bg-accent/5"
                      : "border-border bg-card-bg",
                  )}
                >
                  {p.badge && (
                    <span className="absolute -top-2 left-1/2 -translate-x-1/2 px-2 py-0.5 text-[10px] font-semibold rounded-full bg-accent text-white">
                      {p.badge}
                    </span>
                  )}
                  <div className="flex justify-center mb-2">
                    {p.value === "openai" && <Zap size={24} className="text-green-500" />}
                    {p.value === "anthropic" && <Brain size={24} className="text-orange-500" />}
                    {p.value === "groq" && <Zap size={24} className="text-purple-500" />}
                  </div>
                  <div className="font-semibold">{p.label}</div>
                  <div className="text-xs text-muted">{p.subtitle}</div>
                </button>
              ))}
            </div>

            {/* Provider config form */}
            {selectedProvider && (
              <div className="bg-card-bg rounded-xl border border-border p-5 space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1.5">API Key</label>
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => {
                      setApiKey(e.target.value);
                      setConnectionResult(null);
                    }}
                    placeholder={`Insira sua chave ${selectedProvider}`}
                    className="w-full px-3 py-2.5 rounded-lg border border-border bg-background text-foreground focus:ring-2 focus:ring-accent/50 focus:border-accent outline-none font-mono text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1.5">Modelo padrao</label>
                  <select
                    value={modelId}
                    onChange={(e) => {
                      setModelId(e.target.value);
                      setConnectionResult(null);
                    }}
                    className="w-full px-3 py-2.5 rounded-lg border border-border bg-background text-foreground focus:ring-2 focus:ring-accent/50 focus:border-accent outline-none"
                  >
                    {(PROVIDER_MODELS[selectedProvider] || []).map((m) => (
                      <option key={m.id} value={m.id}>{m.label}</option>
                    ))}
                  </select>
                </div>

                {/* Test connection */}
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleTestConnection}
                    disabled={testingConnection || !apiKey.trim()}
                    className="inline-flex items-center gap-2 px-4 py-2 text-sm border border-border rounded-lg hover:bg-muted/10 transition-colors disabled:opacity-50"
                  >
                    {testingConnection ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
                    Testar conexao
                  </button>
                  {connectionResult && (
                    <div className={cn("flex items-center gap-1.5 text-sm", connectionResult.ok ? "text-green-500" : "text-red-500")}>
                      {connectionResult.ok ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
                      {connectionResult.message}
                    </div>
                  )}
                </div>
              </div>
            )}

            <div className="flex justify-between pt-4">
              <button onClick={goBack} className="flex items-center gap-1 text-sm text-muted hover:text-foreground transition-colors">
                <ArrowLeft size={16} /> Voltar
              </button>
              <button
                onClick={handleProviderSave}
                disabled={saving || !connectionResult?.ok}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-accent text-white rounded-lg font-medium hover:bg-accent/90 transition-colors disabled:opacity-50"
              >
                {saving ? <Loader2 size={16} className="animate-spin" /> : null}
                Continuar <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* STEP 3 — Email (opcional) */}
        {currentStep === 3 && (
          <div className="space-y-6">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-2xl font-bold">Configure notificacoes por email</h2>
                <p className="text-muted mt-1">Receba alertas de erros e incidentes por email</p>
              </div>
              <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-muted/20 text-muted">
                Opcional
              </span>
            </div>

            {smtpLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted p-8 justify-center">
                <Loader2 size={16} className="animate-spin" /> Verificando configuracao...
              </div>
            ) : smtpConfigured ? (
              <div className="bg-card-bg rounded-xl border border-border p-6 space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-green-500/10 flex items-center justify-center">
                    <CheckCircle2 size={20} className="text-green-500" />
                  </div>
                  <div>
                    <p className="font-medium">SMTP ja configurado</p>
                    <p className="text-sm text-muted">As variaveis de ambiente SMTP estao ativas</p>
                  </div>
                </div>
                <button
                  onClick={handleTestSmtp}
                  disabled={smtpTesting}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm border border-border rounded-lg hover:bg-muted/10 transition-colors disabled:opacity-50"
                >
                  {smtpTesting ? <Loader2 size={14} className="animate-spin" /> : <Mail size={14} />}
                  Enviar email de teste
                </button>
              </div>
            ) : (
              <div className="bg-card-bg rounded-xl border border-border p-6 space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-muted/10 flex items-center justify-center">
                    <Mail size={20} className="text-muted" />
                  </div>
                  <div>
                    <p className="font-medium">SMTP nao configurado</p>
                    <p className="text-sm text-muted">
                      Configure as variaveis de ambiente SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD e SMTP_FROM no .env para ativar notificacoes por email.
                    </p>
                  </div>
                </div>
                <p className="text-sm text-muted">
                  Voce pode configurar isso depois em <strong>Configuracoes</strong>.
                </p>
              </div>
            )}

            <div className="flex justify-between pt-4">
              <button onClick={goBack} className="flex items-center gap-1 text-sm text-muted hover:text-foreground transition-colors">
                <ArrowLeft size={16} /> Voltar
              </button>
              <div className="flex gap-3">
                <button
                  onClick={handleSkipEmail}
                  disabled={saving}
                  className="inline-flex items-center gap-2 px-4 py-2.5 text-sm text-muted border border-border rounded-lg hover:bg-muted/10 transition-colors disabled:opacity-50"
                >
                  <SkipForward size={14} /> Pular por agora
                </button>
                {smtpConfigured && (
                  <button
                    onClick={handleEmailContinue}
                    disabled={saving}
                    className="inline-flex items-center gap-2 px-5 py-2.5 bg-accent text-white rounded-lg font-medium hover:bg-accent/90 transition-colors disabled:opacity-50"
                  >
                    {saving ? <Loader2 size={16} className="animate-spin" /> : null}
                    Continuar <ArrowRight size={16} />
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* STEP 4 — Primeiro repositorio */}
        {currentStep === 4 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-2xl font-bold">Adicione seu primeiro repositorio</h2>
              <p className="text-muted mt-1">O Memora vai indexar o codigo para comecar a responder perguntas</p>
            </div>

            {/* Mode toggle */}
            {ghConnected && (
              <div className="flex gap-2">
                <button
                  onClick={() => setRepoMode("github")}
                  className={cn(
                    "flex-1 px-4 py-2.5 rounded-lg text-sm font-medium border-2 transition-all",
                    repoMode === "github" ? "border-accent bg-accent/5" : "border-border",
                  )}
                >
                  <Github size={14} className="inline mr-1.5" /> Repositorios GitHub
                </button>
                <button
                  onClick={() => setRepoMode("url")}
                  className={cn(
                    "flex-1 px-4 py-2.5 rounded-lg text-sm font-medium border-2 transition-all",
                    repoMode === "url" ? "border-accent bg-accent/5" : "border-border",
                  )}
                >
                  <Globe size={14} className="inline mr-1.5" /> URL do repositorio
                </button>
              </div>
            )}

            {/* GitHub repo selector */}
            {repoMode === "github" && ghConnected && (
              <div className="bg-card-bg rounded-xl border border-border p-5 space-y-3">
                <label className="block text-sm font-medium">Selecione um repositorio</label>
                {ghRepos.length > 0 ? (
                  <select
                    value={selectedGhRepo}
                    onChange={(e) => setSelectedGhRepo(e.target.value)}
                    className="w-full px-3 py-2.5 rounded-lg border border-border bg-background text-foreground outline-none"
                  >
                    <option value="">Selecione...</option>
                    {ghRepos.map((r) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                ) : (
                  <p className="text-sm text-muted">Carregando repositorios...</p>
                )}
              </div>
            )}

            {/* URL input */}
            {repoMode === "url" && (
              <div className="bg-card-bg rounded-xl border border-border p-5 space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1.5">URL do repositorio Git</label>
                  <input
                    type="text"
                    value={repoUrl}
                    onChange={(e) => setRepoUrl(e.target.value)}
                    placeholder="https://github.com/usuario/repositorio.git"
                    className="w-full px-3 py-2.5 rounded-lg border border-border bg-background text-foreground focus:ring-2 focus:ring-accent/50 focus:border-accent outline-none text-sm"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium mb-1.5">Branch</label>
                    <input
                      type="text"
                      value={repoBranch}
                      onChange={(e) => setRepoBranch(e.target.value)}
                      placeholder="main"
                      className="w-full px-3 py-2.5 rounded-lg border border-border bg-background text-foreground outline-none text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1.5">
                      Token <span className="text-muted">(se privado)</span>
                    </label>
                    <input
                      type="password"
                      value={repoToken}
                      onChange={(e) => setRepoToken(e.target.value)}
                      placeholder="ghp_..."
                      className="w-full px-3 py-2.5 rounded-lg border border-border bg-background text-foreground outline-none text-sm font-mono"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Indexing progress */}
            {indexing && indexProgress && (
              <div className="bg-card-bg rounded-xl border border-border p-5 space-y-3">
                <div className="flex items-center gap-2">
                  <Loader2 size={16} className="animate-spin text-accent" />
                  <span className="text-sm font-medium">{indexProgress.detail}</span>
                </div>
                <div className="w-full h-2 bg-muted/20 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-accent rounded-full transition-all duration-500"
                    style={{ width: `${indexProgress.percent}%` }}
                  />
                </div>
                <p className="text-xs text-muted">{indexProgress.stage} — {indexProgress.percent}%</p>
              </div>
            )}

            {/* Indexing result */}
            {indexResult && (
              <div className="bg-green-500/5 rounded-xl border border-green-500/20 p-5">
                <div className="flex items-center gap-3">
                  <CheckCircle2 size={24} className="text-green-500" />
                  <div>
                    <p className="font-medium text-green-600">Indexacao concluida</p>
                    <p className="text-sm text-muted">
                      {indexResult.repo} — {indexResult.chunks.toLocaleString()} chunks indexados
                    </p>
                  </div>
                </div>
              </div>
            )}

            <div className="flex justify-between pt-4">
              <button onClick={goBack} className="flex items-center gap-1 text-sm text-muted hover:text-foreground transition-colors">
                <ArrowLeft size={16} /> Voltar
              </button>
              {!indexResult ? (
                <button
                  onClick={handleStartIndexing}
                  disabled={indexing || (repoMode === "url" ? !repoUrl.trim() : !selectedGhRepo)}
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-accent text-white rounded-lg font-medium hover:bg-accent/90 transition-colors disabled:opacity-50"
                >
                  {indexing ? <Loader2 size={16} className="animate-spin" /> : <Database size={16} />}
                  {indexing ? "Indexando..." : "Indexar repositorio"}
                </button>
              ) : (
                <button
                  onClick={goNext}
                  disabled={saving}
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-accent text-white rounded-lg font-medium hover:bg-accent/90 transition-colors disabled:opacity-50"
                >
                  Continuar <ArrowRight size={16} />
                </button>
              )}
            </div>
          </div>
        )}

        {/* STEP 5 — Tudo pronto */}
        {currentStep === 5 && (
          <div className="text-center space-y-8">
            <div className="flex justify-center">
              <div className="w-20 h-20 rounded-2xl bg-green-500/10 flex items-center justify-center">
                <CheckCircle2 size={40} className="text-green-500" />
              </div>
            </div>
            <div className="space-y-2">
              <h1 className="text-3xl font-bold">O Memora esta pronto para uso!</h1>
            </div>

            {/* Summary */}
            <div className="bg-card-bg rounded-xl border border-border p-6 text-left space-y-3">
              {[
                { ok: true, text: `Organizacao: ${setupSummary.orgName || orgName}` },
                { ok: true, text: `IA: ${setupSummary.provider} ${setupSummary.model} configurado` },
                { ok: setupSummary.emailConfigured, text: setupSummary.emailConfigured ? "Email configurado" : "Email: nao configurado (pode configurar depois)" },
                { ok: !!setupSummary.repoName, text: setupSummary.repoName ? `Repositorio: ${setupSummary.repoName} indexado (${setupSummary.chunks.toLocaleString()} chunks)` : "Repositorio: indexado" },
              ].map(({ ok, text }) => (
                <div key={text} className="flex items-center gap-3">
                  <CheckCircle2 size={18} className={ok ? "text-green-500" : "text-muted"} />
                  <span className="text-sm">{text}</span>
                </div>
              ))}
            </div>

            {/* Next steps */}
            <div className="bg-card-bg rounded-xl border border-border p-6 text-left space-y-4">
              <h3 className="font-semibold text-sm text-muted uppercase tracking-wide">O que fazer agora:</h3>
              <div className="space-y-3">
                {[
                  { n: 1, text: "Convide seu time em Configuracoes > Usuarios" },
                  { n: 2, text: "Faca sua primeira pergunta no Assistente" },
                  { n: 3, text: "Configure o Monitor de Erros para seus projetos" },
                ].map(({ n, text }) => (
                  <div key={n} className="flex items-center gap-3">
                    <div className="w-6 h-6 rounded-full bg-accent/10 flex items-center justify-center text-xs font-bold text-accent">
                      {n}
                    </div>
                    <span className="text-sm">{text}</span>
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={handleFinish}
              disabled={saving}
              className="inline-flex items-center gap-2 px-6 py-3 bg-accent text-white rounded-lg font-medium hover:bg-accent/90 transition-colors disabled:opacity-50"
            >
              {saving ? <Loader2 size={18} className="animate-spin" /> : null}
              Ir para o Dashboard
              <ChevronRight size={18} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
