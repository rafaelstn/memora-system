"use client";

import { useEffect, useState } from "react";
import {
  Save, Copy, DollarSign, Globe, ShieldCheck, Github, Bell, Brain, Terminal, Mail,
  Loader2, ExternalLink, Unplug, CheckCircle2, RefreshCw, ChevronDown, ChevronUp,
  Plus, Trash2, Zap, Key, Trash, Check,
} from "lucide-react";
import toast from "react-hot-toast";
import {
  connectGitHub, getGitHubStatus, disconnectGitHub,
  listAlertWebhooks, createAlertWebhook, deleteAlertWebhook, testAlertWebhook,
  getKnowledgeSettings, updateKnowledgeSettings,
  getMcpTokenStatus, generateMcpToken, revokeMcpToken,
  getNotificationPreferences, updateNotificationPreferences, getSMTPStatus, testSMTP,
} from "@/lib/api";
import type { NotificationPreferences, SMTPStatus } from "@/lib/api";
import type { AlertWebhook } from "@/lib/types";
import { Modal } from "@/components/ui/modal";
import { LLMProvidersSection } from "@/components/settings/llm-providers-section";

export default function SettingsPage() {
  const [exchangeRate, setExchangeRate] = useState(5.7);
  const [fetchingRate, setFetchingRate] = useState(false);
  const [lastRateUpdate, setLastRateUpdate] = useState("");
  const [maxQuestions, setMaxQuestions] = useState(0);
  const [showWebhookGuide, setShowWebhookGuide] = useState(false);
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const webhookUrl = `${apiBase}/api/webhooks/github`;

  // GitHub integration state
  const [ghConnected, setGhConnected] = useState(false);
  const [ghLogin, setGhLogin] = useState("");
  const [ghAvatar, setGhAvatar] = useState("");
  const [ghScopes, setGhScopes] = useState("");
  const [ghConnectedAt, setGhConnectedAt] = useState("");
  const [ghToken, setGhToken] = useState("");
  const [ghLoading, setGhLoading] = useState(false);
  const [ghFetching, setGhFetching] = useState(true);
  const [showDisconnectModal, setShowDisconnectModal] = useState(false);

  // Alert webhooks state
  const [webhooks, setWebhooks] = useState<AlertWebhook[]>([]);
  const [webhooksLoading, setWebhooksLoading] = useState(true);
  const [newWhName, setNewWhName] = useState("");
  const [newWhUrl, setNewWhUrl] = useState("");
  const [addingWh, setAddingWh] = useState(false);

  // Knowledge settings state
  const [autoWiki, setAutoWiki] = useState(false);
  const [autoSync, setAutoSync] = useState(false);
  const [knowledgeLoading, setKnowledgeLoading] = useState(true);
  const [knowledgeSaving, setKnowledgeSaving] = useState(false);

  // MCP token state
  const [mcpHasToken, setMcpHasToken] = useState(false);
  const [mcpCreatedAt, setMcpCreatedAt] = useState("");
  const [mcpLoading, setMcpLoading] = useState(true);
  const [mcpGenerating, setMcpGenerating] = useState(false);
  const [mcpNewToken, setMcpNewToken] = useState("");
  const [mcpCopied, setMcpCopied] = useState(false);
  const [showMcpInstructions, setShowMcpInstructions] = useState(false);

  // SMTP / Notification preferences state
  const [smtpStatus, setSmtpStatus] = useState<SMTPStatus | null>(null);
  const [smtpLoading, setSmtpLoading] = useState(true);
  const [smtpTesting, setSmtpTesting] = useState(false);
  const [notifPrefs, setNotifPrefs] = useState<NotificationPreferences>({
    email_enabled: true,
    alert_email: true,
    incident_email: true,
    review_email: true,
    security_email: true,
    executive_email: true,
  });
  const [notifLoading, setNotifLoading] = useState(true);
  const [notifSaving, setNotifSaving] = useState(false);

  async function fetchExchangeRate() {
    setFetchingRate(true);
    try {
      const res = await fetch("https://economia.awesomeapi.com.br/json/last/USD-BRL");
      const data = await res.json();
      const rate = parseFloat(data.USDBRL.bid);
      setExchangeRate(rate);
      setLastRateUpdate(new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }));
      toast.success(`Câmbio atualizado: R$ ${rate.toFixed(2)}`);
    } catch {
      toast.error("Erro ao buscar câmbio. Tente novamente.");
    } finally {
      setFetchingRate(false);
    }
  }

  useEffect(() => {
    // Auto-fetch exchange rate on mount
    fetch("https://economia.awesomeapi.com.br/json/last/USD-BRL")
      .then((r) => r.json())
      .then((data) => {
        const rate = parseFloat(data.USDBRL.bid);
        setExchangeRate(rate);
        setLastRateUpdate(new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }));
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    listAlertWebhooks()
      .then(setWebhooks)
      .catch(() => {})
      .finally(() => setWebhooksLoading(false));
  }, []);

  useEffect(() => {
    getGitHubStatus()
      .then((data) => {
        setGhConnected(data.connected);
        setGhLogin(data.github_login || "");
        setGhAvatar(data.github_avatar_url || "");
        setGhScopes(data.scopes || "");
        setGhConnectedAt(data.connected_at || "");
      })
      .catch(() => {})
      .finally(() => setGhFetching(false));
  }, []);

  useEffect(() => {
    getKnowledgeSettings()
      .then((data) => {
        setAutoWiki(data.auto_wiki);
        setAutoSync(data.auto_sync);
      })
      .catch(() => {})
      .finally(() => setKnowledgeLoading(false));
  }, []);

  useEffect(() => {
    getMcpTokenStatus()
      .then((data) => {
        setMcpHasToken(data.has_token);
        setMcpCreatedAt(data.created_at || "");
      })
      .catch(() => {})
      .finally(() => setMcpLoading(false));
  }, []);

  useEffect(() => {
    getSMTPStatus()
      .then(setSmtpStatus)
      .catch(() => {})
      .finally(() => setSmtpLoading(false));
  }, []);

  useEffect(() => {
    getNotificationPreferences()
      .then(setNotifPrefs)
      .catch(() => {})
      .finally(() => setNotifLoading(false));
  }, []);

  async function saveKnowledgeSettings() {
    setKnowledgeSaving(true);
    try {
      await updateKnowledgeSettings({ auto_wiki: autoWiki, auto_sync: autoSync });
      const msg = (autoSync || autoWiki)
        ? "Salvo! Primeira execucao automatica iniciada em background."
        : "Configuracoes da Memoria Tecnica salvas";
      toast.success(msg);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao salvar");
    } finally {
      setKnowledgeSaving(false);
    }
  }

  function saveExchangeRate() {
    toast.success(`Câmbio atualizado para R$ ${exchangeRate.toFixed(2)}`);
  }

  function copyWebhook() {
    navigator.clipboard.writeText(webhookUrl);
    toast.success("URL copiada para a área de transferência");
  }

  function saveMaxQuestions() {
    toast.success(
      maxQuestions === 0
        ? "Limite removido (ilimitado)"
        : `Limite definido para ${maxQuestions} perguntas/dia`,
    );
  }

  async function handleConnectGitHub() {
    if (!ghToken.trim()) {
      toast.error("Cole seu Personal Access Token");
      return;
    }
    setGhLoading(true);
    try {
      const result = await connectGitHub(ghToken);
      setGhConnected(true);
      setGhLogin(result.github_login);
      setGhAvatar(result.github_avatar_url);
      setGhScopes(result.scopes);
      setGhConnectedAt(new Date().toISOString());
      setGhToken("");
      toast.success(`GitHub conectado como ${result.github_login}`);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Erro ao conectar");
    } finally {
      setGhLoading(false);
    }
  }

  async function handleDisconnectGitHub() {
    setGhLoading(true);
    try {
      await disconnectGitHub();
      setGhConnected(false);
      setGhLogin("");
      setGhAvatar("");
      setGhScopes("");
      setGhConnectedAt("");
      setShowDisconnectModal(false);
      toast.success("Integração GitHub desconectada");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Erro ao desconectar");
    } finally {
      setGhLoading(false);
    }
  }

  return (
    <div className="p-5 lg:p-8 space-y-8 max-w-2xl">
      <div className="pt-2">
        <h1 className="text-xl font-semibold">Configurações</h1>
      </div>

      {/* LLM Providers */}
      <LLMProvidersSection />

      {/* GitHub Integration */}
      <div className="rounded-xl border border-border bg-card-bg p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-hover">
            <Github size={18} className="text-muted" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold">Integração GitHub</h2>
          </div>
          {ghConnected && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-success-surface text-success">
              <CheckCircle2 size={12} />
              Conectado
            </span>
          )}
        </div>

        {ghFetching ? (
          <div className="flex items-center gap-2 text-sm text-muted">
            <Loader2 size={16} className="animate-spin" />
            Carregando...
          </div>
        ) : ghConnected ? (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              {ghAvatar && (
                <img
                  src={ghAvatar}
                  alt={ghLogin}
                  className="w-10 h-10 rounded-full"
                />
              )}
              <div>
                <p className="text-sm font-medium">{ghLogin}</p>
                {ghConnectedAt && (
                  <p className="text-xs text-muted">
                    Conectado em{" "}
                    {new Date(ghConnectedAt).toLocaleDateString("pt-BR")}
                  </p>
                )}
              </div>
            </div>
            {ghScopes && (
              <div>
                <p className="text-xs font-medium text-muted mb-1">Escopos ativos</p>
                <div className="flex flex-wrap gap-1">
                  {ghScopes.split(",").map((s) => (
                    <span
                      key={s.trim()}
                      className="px-2 py-0.5 text-xs rounded bg-border/50 text-muted"
                    >
                      {s.trim()}
                    </span>
                  ))}
                </div>
              </div>
            )}
            <button
              onClick={() => setShowDisconnectModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-danger/30 text-danger hover:bg-danger-surface transition-colors"
            >
              <Unplug size={14} />
              Desconectar
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-muted">
              Conecte uma conta GitHub para indexar repositórios privados.
            </p>
            <div>
              <label className="block text-sm font-medium mb-1">
                Personal Access Token
              </label>
              <input
                type="password"
                value={ghToken}
                onChange={(e) => setGhToken(e.target.value)}
                placeholder="ghp_..."
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground font-mono"
              />
              <div className="flex items-center gap-4 mt-2">
                <p className="text-xs text-muted">
                  Escopos necessários: <code className="text-foreground">repo</code>,{" "}
                  <code className="text-foreground">read:org</code>
                </p>
                <a
                  href="https://github.com/settings/tokens"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-accent hover:text-accent-light inline-flex items-center gap-1"
                >
                  Como gerar um token
                  <ExternalLink size={10} />
                </a>
              </div>
            </div>
            <button
              onClick={handleConnectGitHub}
              disabled={ghLoading || !ghToken.trim()}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-foreground text-background hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {ghLoading ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Github size={14} />
              )}
              Conectar GitHub
            </button>
          </div>
        )}
      </div>

      {/* Knowledge / Technical Memory Settings */}
      <div className="rounded-xl border border-border bg-card-bg p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-accent-surface">
            <Brain size={18} className="text-accent" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold">Memoria Tecnica</h2>
            <p className="text-sm text-muted">
              Configuracoes de automacao da Memoria Tecnica (wikis, sync GitHub).
            </p>
          </div>
        </div>

        {knowledgeLoading ? (
          <div className="flex items-center gap-2 text-sm text-muted">
            <Loader2 size={16} className="animate-spin" />
            Carregando...
          </div>
        ) : (
          <div className="space-y-4">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={autoSync}
                onChange={(e) => setAutoSync(e.target.checked)}
                className="w-4 h-4 rounded border-border accent-accent"
              />
              <div>
                <p className="text-sm font-medium">Sincronizar automaticamente</p>
                <p className="text-xs text-muted">
                  Ao receber webhooks do GitHub, extrair PRs/commits/issues automaticamente
                </p>
              </div>
            </label>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={autoWiki}
                onChange={(e) => setAutoWiki(e.target.checked)}
                className="w-4 h-4 rounded border-border accent-accent"
              />
              <div>
                <p className="text-sm font-medium">Gerar wikis automaticamente</p>
                <p className="text-xs text-muted">
                  Apos sincronizacao ou indexacao, gerar/atualizar wikis dos componentes afetados
                </p>
              </div>
            </label>

            <button
              onClick={saveKnowledgeSettings}
              disabled={knowledgeSaving}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors disabled:opacity-50"
            >
              {knowledgeSaving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
              Salvar
            </button>
          </div>
        )}
      </div>

      {/* Claude Code (MCP) */}
      <div className="rounded-xl border border-border bg-card-bg p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-accent-surface">
            <Terminal size={18} className="text-accent" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold">Claude Code (MCP)</h2>
            <p className="text-sm text-muted">
              Conecte o Memora ao Claude Code para injetar contexto automaticamente enquanto voce programa.
            </p>
          </div>
          {mcpHasToken && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-success-surface text-success">
              <CheckCircle2 size={12} />
              Conectado
            </span>
          )}
        </div>

        {mcpLoading ? (
          <div className="flex items-center gap-2 text-sm text-muted">
            <Loader2 size={16} className="animate-spin" />
            Carregando...
          </div>
        ) : (
          <div className="space-y-4">
            {mcpNewToken ? (
              <div className="p-4 rounded-lg bg-accent-surface/50 border border-accent/30">
                <p className="text-sm font-medium mb-2 flex items-center gap-2">
                  <Key size={14} className="text-accent" />
                  Token gerado
                </p>
                <div className="flex items-center gap-2 mb-2">
                  <code className="flex-1 px-3 py-2 text-xs font-mono rounded-lg bg-card-bg border border-border break-all">
                    {mcpNewToken}
                  </code>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(mcpNewToken);
                      setMcpCopied(true);
                      setTimeout(() => setMcpCopied(false), 2000);
                      toast.success("Token copiado");
                    }}
                    className="p-2 rounded-lg border border-border hover:bg-hover transition-colors shrink-0"
                  >
                    {mcpCopied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
                  </button>
                </div>
                <p className="text-xs text-warning">
                  Guarde este token — ele nao sera exibido novamente.
                </p>
              </div>
            ) : mcpHasToken ? (
              <div className="flex items-center gap-3">
                <p className="text-sm text-muted">
                  Token ativo{mcpCreatedAt && ` desde ${new Date(mcpCreatedAt).toLocaleDateString("pt-BR")}`}
                </p>
                <button
                  onClick={async () => {
                    setMcpGenerating(true);
                    try {
                      await revokeMcpToken();
                      setMcpHasToken(false);
                      toast.success("Token revogado");
                    } catch (err) {
                      toast.error(err instanceof Error ? err.message : "Erro ao revogar");
                    } finally {
                      setMcpGenerating(false);
                    }
                  }}
                  disabled={mcpGenerating}
                  className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg border border-danger/30 text-danger hover:bg-danger-surface transition-colors"
                >
                  <Trash size={12} /> Revogar
                </button>
              </div>
            ) : (
              <button
                onClick={async () => {
                  setMcpGenerating(true);
                  try {
                    const result = await generateMcpToken();
                    setMcpNewToken(result.token);
                    setMcpHasToken(true);
                    setMcpCreatedAt(new Date().toISOString());
                    toast.success("Token MCP gerado");
                  } catch (err) {
                    toast.error(err instanceof Error ? err.message : "Erro ao gerar token");
                  } finally {
                    setMcpGenerating(false);
                  }
                }}
                disabled={mcpGenerating}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors disabled:opacity-50"
              >
                {mcpGenerating ? <Loader2 size={14} className="animate-spin" /> : <Key size={14} />}
                Gerar token MCP
              </button>
            )}

            <div>
              <button
                onClick={() => setShowMcpInstructions(!showMcpInstructions)}
                className="inline-flex items-center gap-1 text-xs text-accent hover:text-accent-light transition-colors"
              >
                {showMcpInstructions ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                Tutorial: Como configurar no Claude Code
              </button>

              {showMcpInstructions && (
                <div className="mt-3 p-5 rounded-lg bg-background border border-border text-sm space-y-5">

                  {/* Passo 1 */}
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <span className="flex items-center justify-center h-6 w-6 rounded-full bg-accent text-white text-xs font-bold shrink-0">1</span>
                      <p className="font-semibold">Gere seu token MCP</p>
                    </div>
                    <p className="text-xs text-muted ml-8">
                      Clique no botao <span className="text-foreground font-medium">&quot;Gerar token MCP&quot;</span> acima.
                      O token sera exibido apenas uma vez — copie e guarde em local seguro.
                    </p>
                  </div>

                  {/* Passo 2 */}
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <span className="flex items-center justify-center h-6 w-6 rounded-full bg-accent text-white text-xs font-bold shrink-0">2</span>
                      <p className="font-semibold">Instale o Claude Code (se ainda nao tem)</p>
                    </div>
                    <div className="ml-8 space-y-2">
                      <p className="text-xs text-muted">
                        O Claude Code e a CLI oficial da Anthropic para programar com Claude.
                      </p>
                      <pre className="p-3 rounded-lg bg-card-bg border border-border text-xs font-mono overflow-x-auto">
{`npm install -g @anthropic-ai/claude-code`}
                      </pre>
                      <p className="text-xs text-muted">
                        Apos instalar, rode <code className="px-1 py-0.5 rounded bg-border/50 text-foreground">claude</code> no terminal para iniciar.
                      </p>
                    </div>
                  </div>

                  {/* Passo 3 */}
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <span className="flex items-center justify-center h-6 w-6 rounded-full bg-accent text-white text-xs font-bold shrink-0">3</span>
                      <p className="font-semibold">Configure o arquivo MCP</p>
                    </div>
                    <div className="ml-8 space-y-2">
                      <p className="text-xs text-muted">
                        Crie ou edite o arquivo <code className="px-1 py-0.5 rounded bg-border/50 text-accent">~/.claude/mcp_servers.json</code> e
                        adicione a configuracao abaixo:
                      </p>
                      <pre className="p-3 rounded-lg bg-card-bg border border-border text-xs font-mono overflow-x-auto">
{`{
  "memora": {
    "url": "${apiBase}/mcp",
    "headers": {
      "Authorization": "Bearer ${mcpNewToken || "SEU_TOKEN_AQUI"}"
    }
  }
}`}
                      </pre>
                      <p className="text-xs text-muted">
                        Substitua <code className="text-foreground">SEU_TOKEN_AQUI</code> pelo token gerado no passo 1.
                      </p>
                    </div>
                  </div>

                  {/* Passo 4 */}
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <span className="flex items-center justify-center h-6 w-6 rounded-full bg-accent text-white text-xs font-bold shrink-0">4</span>
                      <p className="font-semibold">Verifique a conexao</p>
                    </div>
                    <div className="ml-8 space-y-2">
                      <p className="text-xs text-muted">
                        Reinicie o Claude Code e rode:
                      </p>
                      <pre className="p-3 rounded-lg bg-card-bg border border-border text-xs font-mono overflow-x-auto">
{`/mcp status`}
                      </pre>
                      <p className="text-xs text-muted">
                        Voce deve ver: <span className="text-success font-medium">memora: connected</span>
                      </p>
                    </div>
                  </div>

                  {/* Divider */}
                  <div className="border-t border-border" />

                  {/* Tools disponiveis */}
                  <div>
                    <p className="font-semibold mb-3">Tools disponiveis</p>
                    <p className="text-xs text-muted mb-3">
                      O Memora expoe 5 ferramentas que o Claude Code usa automaticamente:
                    </p>
                    <div className="space-y-2">
                      {[
                        { name: "search_similar_code", desc: "Busca codigo similar no sistema para evitar duplicacao" },
                        { name: "get_business_rules", desc: "Busca regras de negocio relevantes para o contexto" },
                        { name: "get_team_patterns", desc: "Identifica padroes e convencoes de codigo do time" },
                        { name: "get_architecture_decisions", desc: "Busca decisoes arquiteturais anteriores (ADRs, PRs)" },
                        { name: "get_environment_context", desc: "Lista variaveis de ambiente necessarias" },
                      ].map((tool) => (
                        <div key={tool.name} className="flex items-start gap-2 p-2 rounded-lg bg-card-bg border border-border">
                          <code className="text-[10px] font-mono text-accent bg-accent-surface px-1.5 py-0.5 rounded shrink-0 mt-0.5">
                            {tool.name}
                          </code>
                          <span className="text-xs text-muted">{tool.desc}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Divider */}
                  <div className="border-t border-border" />

                  {/* Exemplos de uso */}
                  <div>
                    <p className="font-semibold mb-3">Exemplos de uso</p>
                    <p className="text-xs text-muted mb-3">
                      O Claude Code consulta o Memora automaticamente ao detectar que voce esta implementando algo.
                      Voce tambem pode pedir explicitamente:
                    </p>
                    <div className="space-y-2">
                      {[
                        "Implemente um endpoint de desconto seguindo os padroes do nosso sistema",
                        "Crie uma funcao de validacao de CPF — verifique se ja temos algo similar",
                        "Qual e a regra de comissao antes de eu implementar esse calculo?",
                        "Implemente o servico de notificacao respeitando as decisoes arquiteturais do time",
                      ].map((example, i) => (
                        <div key={i} className="p-2.5 rounded-lg bg-card-bg border border-border">
                          <p className="text-xs text-foreground italic">&quot;{example}&quot;</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Divider */}
                  <div className="border-t border-border" />

                  {/* Como funciona */}
                  <div>
                    <p className="font-semibold mb-3">Como funciona por baixo</p>
                    <div className="space-y-2 text-xs text-muted">
                      <p>
                        Quando voce pede algo ao Claude Code, ele detecta automaticamente que precisa de contexto e
                        chama as tools do Memora em background:
                      </p>
                      <ol className="list-decimal list-inside space-y-1.5 ml-1">
                        <li>Busca <span className="text-foreground font-medium">codigo similar</span> no seu codebase indexado via embeddings</li>
                        <li>Verifica se existem <span className="text-foreground font-medium">regras de negocio</span> que se aplicam ao contexto</li>
                        <li>Identifica <span className="text-foreground font-medium">padroes do time</span> (naming, estrutura, tratamento de erros)</li>
                        <li>Busca <span className="text-foreground font-medium">decisoes anteriores</span> em PRs, ADRs e issues</li>
                        <li>Lista <span className="text-foreground font-medium">variaveis de ambiente</span> relevantes</li>
                      </ol>
                      <p>
                        Todo esse contexto e injetado no prompt do Claude, que gera codigo
                        consistente com o sistema existente — sem duplicacao e respeitando as regras.
                      </p>
                    </div>
                  </div>

                  {/* Dica */}
                  <div className="p-3 rounded-lg bg-accent-surface/50 border border-accent/20">
                    <p className="text-xs text-accent font-medium mb-1">Dica</p>
                    <p className="text-xs text-muted">
                      Para melhores resultados, mantenha o repositorio indexado e atualizado no Memora.
                      Quanto mais codigo, regras e conhecimento indexados, mais preciso sera o contexto
                      injetado no Claude Code.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Exchange Rate */}
      <div className="rounded-xl border border-border bg-card-bg p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-accent-surface">
            <DollarSign size={18} className="text-accent" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold">Câmbio USD/BRL</h2>
            <p className="text-sm text-muted">
              Taxa de conversão usada para calcular custos em reais.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted">R$</span>
            <input
              type="number"
              step="0.01"
              min="0"
              value={exchangeRate}
              onChange={(e) => setExchangeRate(parseFloat(e.target.value) || 0)}
              className="w-36 pl-9 pr-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground"
            />
          </div>
          <button
            onClick={fetchExchangeRate}
            disabled={fetchingRate}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-border hover:bg-hover transition-colors disabled:opacity-50"
            title="Buscar cotação atual"
          >
            {fetchingRate ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <RefreshCw size={14} />
            )}
            Atualizar
          </button>
          <button
            onClick={saveExchangeRate}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors"
          >
            <Save size={14} />
            Salvar
          </button>
        </div>
        {lastRateUpdate && (
          <p className="text-xs text-muted mt-2">
            Cotação atualizada às {lastRateUpdate} — fonte: AwesomeAPI (BCB)
          </p>
        )}
      </div>

      {/* Webhook URL */}
      <div className="rounded-xl border border-border bg-card-bg p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-accent-surface">
            <Globe size={18} className="text-accent" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold">Webhook URL</h2>
            <p className="text-sm text-muted">
              Recebe eventos do GitHub para re-indexar automaticamente ao fazer push.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3 mb-3">
          <input
            type="text"
            readOnly
            value={webhookUrl}
            className="flex-1 px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-muted font-mono"
          />
          <button
            onClick={copyWebhook}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-border hover:bg-hover transition-colors"
          >
            <Copy size={14} />
            Copiar
          </button>
        </div>

        <button
          onClick={() => setShowWebhookGuide(!showWebhookGuide)}
          className="inline-flex items-center gap-1 text-xs text-accent hover:text-accent-light transition-colors"
        >
          {showWebhookGuide ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          Como configurar no GitHub
        </button>

        {showWebhookGuide && (
          <div className="mt-3 p-4 rounded-lg bg-background border border-border text-sm space-y-3">
            <p className="font-medium">Passo a passo:</p>
            <ol className="list-decimal list-inside space-y-2 text-muted">
              <li>
                Acesse seu repositório no GitHub e vá em{" "}
                <span className="text-foreground font-medium">Settings → Webhooks → Add webhook</span>
              </li>
              <li>
                Em <span className="text-foreground font-medium">Payload URL</span>, cole a URL acima
              </li>
              <li>
                Em <span className="text-foreground font-medium">Content type</span>, selecione{" "}
                <code className="px-1 py-0.5 rounded bg-border/50 text-foreground text-xs">application/json</code>
              </li>
              <li>
                Em <span className="text-foreground font-medium">Which events?</span>, selecione{" "}
                <span className="text-foreground font-medium">Just the push event</span>
              </li>
              <li>
                Clique em <span className="text-foreground font-medium">Add webhook</span>
              </li>
            </ol>
            <div className="pt-2 border-t border-border">
              <p className="text-xs text-muted">
                Após configurar, cada <code className="px-1 py-0.5 rounded bg-border/50 text-foreground">git push</code>{" "}
                vai re-indexar automaticamente os arquivos alterados no Memora.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Alert Notifications / Webhooks */}
      <div className="rounded-xl border border-border bg-card-bg p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-accent-surface">
            <Bell size={18} className="text-accent" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold">Notificações de Erros</h2>
            <p className="text-sm text-muted">
              Webhooks para receber alertas do Monitor de Erros em canais externos.
            </p>
          </div>
        </div>

        {/* Add webhook */}
        <div className="flex gap-2 mb-4">
          <input
            type="text"
            value={newWhName}
            onChange={(e) => setNewWhName(e.target.value)}
            placeholder="Nome (ex: Slack do time)"
            className="flex-1 px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground placeholder:text-muted"
          />
          <input
            type="url"
            value={newWhUrl}
            onChange={(e) => setNewWhUrl(e.target.value)}
            placeholder="URL do webhook"
            className="flex-1 px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground placeholder:text-muted font-mono text-xs"
          />
          <button
            onClick={async () => {
              if (!newWhName.trim() || !newWhUrl.trim()) {
                toast.error("Preencha nome e URL");
                return;
              }
              setAddingWh(true);
              try {
                const result = await createAlertWebhook({ name: newWhName, url: newWhUrl });
                setWebhooks((prev) => [
                  { id: result.id, name: result.name, url: result.url, is_active: true, created_at: new Date().toISOString() },
                  ...prev,
                ]);
                setNewWhName("");
                setNewWhUrl("");
                toast.success("Webhook adicionado");
              } catch (err) {
                toast.error(err instanceof Error ? err.message : "Erro");
              } finally {
                setAddingWh(false);
              }
            }}
            disabled={addingWh}
            className="inline-flex items-center gap-1 px-3 py-2 text-sm rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors disabled:opacity-50 shrink-0"
          >
            {addingWh ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
            Adicionar
          </button>
        </div>

        {/* Webhooks list */}
        {webhooksLoading ? (
          <div className="flex items-center gap-2 text-sm text-muted">
            <Loader2 size={14} className="animate-spin" /> Carregando...
          </div>
        ) : webhooks.length === 0 ? (
          <p className="text-sm text-muted">Nenhum webhook configurado.</p>
        ) : (
          <div className="space-y-2">
            {webhooks.map((wh) => (
              <div key={wh.id} className="flex items-center gap-3 px-3 py-2 rounded-lg border border-border">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{wh.name}</p>
                  <p className="text-xs text-muted font-mono truncate">{wh.url}</p>
                </div>
                <button
                  onClick={async () => {
                    try {
                      const result = await testAlertWebhook(wh.id);
                      if (result.status === "ok") {
                        toast.success(`Teste OK — HTTP ${result.http_status}`);
                      } else {
                        toast.error(`Erro: ${result.error}`);
                      }
                    } catch (err) {
                      toast.error("Erro ao testar");
                    }
                  }}
                  className="p-1.5 rounded-lg border border-border hover:bg-hover transition-colors text-muted"
                  title="Testar webhook"
                >
                  <Zap size={14} />
                </button>
                <button
                  onClick={async () => {
                    try {
                      await deleteAlertWebhook(wh.id);
                      setWebhooks((prev) => prev.filter((w) => w.id !== wh.id));
                      toast.success("Webhook removido");
                    } catch (err) {
                      toast.error("Erro ao remover");
                    }
                  }}
                  className="p-1.5 rounded-lg border border-border hover:bg-hover transition-colors text-danger"
                  title="Remover"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* SMTP Configuration */}
      <div className="rounded-xl border border-border bg-card-bg p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-accent-surface">
            <Mail size={18} className="text-accent" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold">Configuracao SMTP</h2>
            <p className="text-sm text-muted">
              Servidor de email para envio de notificacoes automaticas.
            </p>
          </div>
          {smtpStatus?.configured && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-success-surface text-success">
              <CheckCircle2 size={12} />
              Configurado
            </span>
          )}
        </div>

        {smtpLoading ? (
          <div className="flex items-center gap-2 text-sm text-muted">
            <Loader2 size={16} className="animate-spin" />
            Carregando...
          </div>
        ) : !smtpStatus?.configured ? (
          <div className="p-4 rounded-lg bg-background border border-border">
            <p className="text-sm text-muted mb-2">
              SMTP nao configurado. Defina as variaveis de ambiente no backend:
            </p>
            <div className="space-y-1 text-xs font-mono text-muted">
              <p><code className="text-foreground">SMTP_HOST</code> — Servidor SMTP (ex: smtp.gmail.com)</p>
              <p><code className="text-foreground">SMTP_PORT</code> — Porta (padrao: 587)</p>
              <p><code className="text-foreground">SMTP_USER</code> — Usuario/email de autenticacao</p>
              <p><code className="text-foreground">SMTP_PASSWORD</code> — Senha ou app password</p>
              <p><code className="text-foreground">SMTP_FROM</code> — Email remetente (opcional)</p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs font-medium text-muted mb-1">Servidor</p>
                <p className="text-sm font-mono">{smtpStatus.smtp_host}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-muted mb-1">Porta</p>
                <p className="text-sm font-mono">{smtpStatus.smtp_port}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-muted mb-1">Usuario</p>
                <p className="text-sm font-mono">{smtpStatus.smtp_user}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-muted mb-1">Senha</p>
                <p className="text-sm font-mono">{smtpStatus.smtp_password}</p>
              </div>
              <div className="col-span-2">
                <p className="text-xs font-medium text-muted mb-1">Remetente</p>
                <p className="text-sm font-mono">{smtpStatus.smtp_from}</p>
              </div>
            </div>

            <button
              onClick={async () => {
                setSmtpTesting(true);
                try {
                  const result = await testSMTP();
                  toast.success(result.message);
                } catch (err) {
                  toast.error(err instanceof Error ? err.message : "Erro ao enviar email de teste");
                } finally {
                  setSmtpTesting(false);
                }
              }}
              disabled={smtpTesting}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-border hover:bg-hover transition-colors disabled:opacity-50"
            >
              {smtpTesting ? <Loader2 size={14} className="animate-spin" /> : <Mail size={14} />}
              Enviar email de teste
            </button>
          </div>
        )}
      </div>

      {/* Notification Preferences */}
      <div className="rounded-xl border border-border bg-card-bg p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-accent-surface">
            <Bell size={18} className="text-accent" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold">Preferencias de Notificacao</h2>
            <p className="text-sm text-muted">
              Escolha quais notificacoes por email voce deseja receber.
            </p>
          </div>
        </div>

        {notifLoading ? (
          <div className="flex items-center gap-2 text-sm text-muted">
            <Loader2 size={16} className="animate-spin" />
            Carregando...
          </div>
        ) : (
          <div className="space-y-4">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={notifPrefs.email_enabled}
                onChange={(e) => setNotifPrefs((p) => ({ ...p, email_enabled: e.target.checked }))}
                className="w-4 h-4 rounded border-border accent-accent"
              />
              <div>
                <p className="text-sm font-medium">Emails habilitados</p>
                <p className="text-xs text-muted">Desative para pausar todas as notificacoes por email</p>
              </div>
            </label>

            {notifPrefs.email_enabled && (
              <div className="ml-7 space-y-3 border-l-2 border-border pl-4">
                {[
                  { key: "alert_email" as const, label: "Alertas de erro", desc: "Quando o Monitor detecta um erro critico" },
                  { key: "incident_email" as const, label: "Incidentes", desc: "Declaracao, atualizacao e resolucao de incidentes" },
                  { key: "security_email" as const, label: "Seguranca", desc: "Resultados de scans de seguranca e DAST" },
                  { key: "review_email" as const, label: "Revisoes de codigo", desc: "Quando uma revisao de codigo e concluida" },
                  { key: "executive_email" as const, label: "Relatorio executivo", desc: "Snapshots semanais/mensais da Visao Executiva" },
                ].map((item) => (
                  <label key={item.key} className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={notifPrefs[item.key]}
                      onChange={(e) => setNotifPrefs((p) => ({ ...p, [item.key]: e.target.checked }))}
                      className="w-4 h-4 rounded border-border accent-accent"
                    />
                    <div>
                      <p className="text-sm font-medium">{item.label}</p>
                      <p className="text-xs text-muted">{item.desc}</p>
                    </div>
                  </label>
                ))}
              </div>
            )}

            <button
              onClick={async () => {
                setNotifSaving(true);
                try {
                  await updateNotificationPreferences(notifPrefs);
                  toast.success("Preferencias de notificacao salvas");
                } catch (err) {
                  toast.error(err instanceof Error ? err.message : "Erro ao salvar");
                } finally {
                  setNotifSaving(false);
                }
              }}
              disabled={notifSaving}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors disabled:opacity-50"
            >
              {notifSaving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
              Salvar preferencias
            </button>
          </div>
        )}
      </div>

      {/* Usage Limits */}
      <div className="rounded-xl border border-border bg-card-bg p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-accent-surface">
            <ShieldCheck size={18} className="text-accent" />
          </div>
          <h2 className="text-lg font-semibold">Limites de Uso</h2>
        </div>
        <p className="text-sm text-muted mb-4">
          Defina o número máximo de perguntas que cada usuário pode fazer por dia.
        </p>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium mb-1">
              Máx. perguntas por usuário/dia
            </label>
            <input
              type="number"
              min="0"
              value={maxQuestions}
              onChange={(e) => setMaxQuestions(parseInt(e.target.value) || 0)}
              className="w-32 px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground"
            />
            <p className="text-xs text-muted mt-1">0 = ilimitado</p>
          </div>
          <button
            onClick={saveMaxQuestions}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors"
          >
            <Save size={14} />
            Salvar
          </button>
        </div>
      </div>

      {/* Disconnect confirmation modal */}
      <Modal
        open={showDisconnectModal}
        onClose={() => setShowDisconnectModal(false)}
        title="Desconectar GitHub"
      >
        <p className="text-sm text-muted mb-4">
          Isso impedirá a indexação de novos repositórios. Repos já indexados continuarão
          disponíveis, mas não receberão atualizações.
        </p>
        <div className="flex justify-end gap-3">
          <button
            onClick={() => setShowDisconnectModal(false)}
            className="px-4 py-2 text-sm rounded-lg border border-border hover:bg-hover transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={handleDisconnectGitHub}
            disabled={ghLoading}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-danger hover:opacity-90 text-white transition-opacity disabled:opacity-50"
          >
            {ghLoading && <Loader2 size={14} className="animate-spin" />}
            Desconectar
          </button>
        </div>
      </Modal>
    </div>
  );
}
