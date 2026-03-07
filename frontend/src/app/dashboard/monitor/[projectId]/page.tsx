"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  AlertTriangle,
  ScrollText,
  Settings2,
  RotateCcw,
  Copy,
  Eye,
  EyeOff,
  Check,
  CheckCheck,
  Loader2,
  ChevronDown,
} from "lucide-react";
import toast from "react-hot-toast";
import { cn } from "@/lib/utils";
import { Modal } from "@/components/ui/modal";
import {
  getMonitorProject,
  listMonitorAlerts,
  listMonitorLogs,
  rotateProjectToken,
  updateAlertStatus,
  getMonitorAlert,
} from "@/lib/api";
import type {
  MonitoredProjectDetail,
  ErrorAlertSummary,
  ErrorAlertDetail,
  LogEntry,
  AlertSeverity,
  AlertStatus,
} from "@/lib/types";

const severityColors: Record<AlertSeverity, string> = {
  low: "bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300",
  medium: "bg-yellow-100 text-yellow-700 dark:bg-yellow-500/15 dark:text-yellow-300",
  high: "bg-orange-100 text-orange-700 dark:bg-orange-500/15 dark:text-orange-300",
  critical: "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300",
};

const levelColors: Record<string, string> = {
  debug: "text-muted",
  info: "text-blue-500",
  warning: "text-yellow-500",
  error: "text-orange-500",
  critical: "text-red-500",
};

const statusLabels: Record<AlertStatus, string> = {
  open: "Aberto",
  acknowledged: "Reconhecido",
  resolved: "Resolvido",
};

type Tab = "alerts" | "logs" | "config";

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  const [project, setProject] = useState<MonitoredProjectDetail | null>(null);
  const [alerts, setAlerts] = useState<ErrorAlertSummary[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [tab, setTab] = useState<Tab>("alerts");
  const [loading, setLoading] = useState(true);
  const [alertFilter, setAlertFilter] = useState<AlertStatus | "all">("all");
  const [logLevelFilter, setLogLevelFilter] = useState<string>("all");

  // Alert detail drawer
  const [selectedAlert, setSelectedAlert] = useState<ErrorAlertDetail | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerLoading, setDrawerLoading] = useState(false);

  // Token visibility
  const [tokenRevealed, setTokenRevealed] = useState(false);
  const [fullToken, setFullToken] = useState<string | null>(null);

  // Instructions modal
  const [instructionsOpen, setInstructionsOpen] = useState(false);
  const [instructionsTab, setInstructionsTab] = useState<"http" | "agent" | "libs">("http");

  // Rotate token
  const [rotateConfirm, setRotateConfirm] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [proj, alertsData, logsData] = await Promise.all([
        getMonitorProject(projectId),
        listMonitorAlerts({ project_id: projectId }),
        listMonitorLogs({ project_id: projectId }),
      ]);
      setProject(proj);
      setAlerts(alertsData);
      setLogs(logsData);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao carregar projeto");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Poll logs every 5s on logs tab
  useEffect(() => {
    if (tab !== "logs") return;
    const interval = setInterval(async () => {
      try {
        const data = await listMonitorLogs({ project_id: projectId, level: logLevelFilter !== "all" ? logLevelFilter : undefined });
        setLogs(data);
      } catch { /* silent */ }
    }, 5000);
    return () => clearInterval(interval);
  }, [tab, projectId, logLevelFilter]);

  async function handleOpenAlert(alertId: string) {
    setDrawerLoading(true);
    setDrawerOpen(true);
    try {
      const detail = await getMonitorAlert(alertId);
      setSelectedAlert(detail);
    } catch (err) {
      toast.error("Erro ao carregar alerta");
    } finally {
      setDrawerLoading(false);
    }
  }

  async function handleAlertAction(alertId: string, status: "acknowledged" | "resolved") {
    try {
      await updateAlertStatus(alertId, status);
      setAlerts((prev) => prev.map((a) => (a.id === alertId ? { ...a, status } : a)));
      if (selectedAlert?.id === alertId) {
        setSelectedAlert({ ...selectedAlert, status });
      }
      toast.success(status === "acknowledged" ? "Alerta reconhecido" : "Alerta resolvido");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro");
    }
  }

  async function handleRotateToken() {
    try {
      const result = await rotateProjectToken(projectId);
      setFullToken(result.token);
      setTokenRevealed(true);
      setProject((prev) => prev ? { ...prev, token_preview: result.token_preview } : prev);
      setRotateConfirm(false);
      toast.success("Token rotacionado! O anterior foi invalidado.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao rotacionar token");
    }
  }

  const filteredAlerts = alertFilter === "all" ? alerts : alerts.filter((a) => a.status === alertFilter);

  const apiBase = typeof window !== "undefined" ? window.location.origin : "https://seu-memora.com";

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted">
        <Loader2 size={20} className="animate-spin mr-2" />
        Carregando...
      </div>
    );
  }

  if (!project) {
    return <div className="p-8 text-center text-muted">Projeto não encontrado</div>;
  }

  return (
    <div className="p-5 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={() => router.push("/dashboard/monitor")} className="p-1.5 rounded-lg hover:bg-hover text-muted">
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1">
          <h1 className="text-xl font-semibold">{project.name}</h1>
          {project.description && <p className="text-sm text-muted">{project.description}</p>}
        </div>
        <button
          onClick={() => setInstructionsOpen(true)}
          className="px-3 py-1.5 text-xs rounded-lg border border-border hover:bg-hover transition-colors"
        >
          Ver instruções
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {([
          { key: "alerts" as Tab, label: "Alertas", icon: AlertTriangle },
          { key: "logs" as Tab, label: "Logs", icon: ScrollText },
          { key: "config" as Tab, label: "Configuração", icon: Settings2 },
        ]).map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={cn(
              "inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px",
              tab === t.key
                ? "border-accent text-accent"
                : "border-transparent text-muted hover:text-foreground"
            )}
          >
            <t.icon size={16} />
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab: Alerts */}
      {tab === "alerts" && (
        <div className="space-y-4">
          <div className="flex gap-2">
            {(["all", "open", "acknowledged", "resolved"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setAlertFilter(f)}
                className={cn(
                  "px-3 py-1.5 text-xs rounded-lg border transition-colors",
                  alertFilter === f
                    ? "border-accent bg-accent-surface text-accent-text"
                    : "border-border hover:bg-hover"
                )}
              >
                {f === "all" ? "Todos" : statusLabels[f]}
              </button>
            ))}
          </div>

          <div className="rounded-xl border border-border bg-card-bg divide-y divide-border">
            {filteredAlerts.length === 0 && (
              <div className="px-6 py-12 text-center text-sm text-muted">Nenhum alerta encontrado.</div>
            )}
            {filteredAlerts.map((alert) => (
              <button
                key={alert.id}
                onClick={() => handleOpenAlert(alert.id)}
                className="w-full flex items-center gap-4 px-6 py-4 text-left hover:bg-hover transition-colors"
              >
                <span className={cn("px-2 py-0.5 rounded-full text-[11px] font-semibold shrink-0", severityColors[alert.severity])}>
                  {alert.severity}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{alert.title}</p>
                  <p className="text-xs text-muted">{alert.affected_component || "—"}</p>
                </div>
                <span className="text-xs text-muted shrink-0">
                  {new Date(alert.created_at).toLocaleString("pt-BR")}
                </span>
                <span className={cn(
                  "px-2 py-0.5 rounded-full text-[11px] font-semibold shrink-0",
                  alert.status === "open" ? "bg-danger-surface text-danger" :
                  alert.status === "acknowledged" ? "bg-warning-surface text-warning" :
                  "bg-success-surface text-success"
                )}>
                  {statusLabels[alert.status]}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Tab: Logs */}
      {tab === "logs" && (
        <div className="space-y-4">
          <div className="flex gap-2">
            <select
              value={logLevelFilter}
              onChange={(e) => setLogLevelFilter(e.target.value)}
              className="px-3 py-1.5 text-xs rounded-lg border border-border bg-card-bg"
            >
              <option value="all">Todos os níveis</option>
              <option value="debug">Debug</option>
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="error">Error</option>
              <option value="critical">Critical</option>
            </select>
            <span className="text-xs text-muted self-center">Atualiza a cada 5s</span>
          </div>

          <div className="rounded-xl border border-border bg-card-bg divide-y divide-border font-mono text-xs">
            {logs.length === 0 && (
              <div className="px-6 py-12 text-center text-sm text-muted font-sans">Nenhum log recebido.</div>
            )}
            {logs.map((log) => (
              <details key={log.id} className="group">
                <summary className="flex items-center gap-3 px-4 py-2.5 cursor-pointer hover:bg-hover transition-colors list-none">
                  <span className="text-muted shrink-0 w-36">
                    {new Date(log.received_at).toLocaleString("pt-BR")}
                  </span>
                  <span className={cn("font-semibold uppercase w-16 shrink-0", levelColors[log.level] || "text-muted")}>
                    {log.level}
                  </span>
                  <span className="text-muted shrink-0 w-40 truncate">{log.source || "—"}</span>
                  <span className="flex-1 truncate">{log.message}</span>
                  <ChevronDown size={14} className="text-muted group-open:rotate-180 transition-transform shrink-0" />
                </summary>
                <div className="px-4 pb-3 pt-1 space-y-2 bg-hover/50">
                  {log.stack_trace && (
                    <div>
                      <p className="text-muted mb-1 font-sans text-[11px]">Stack trace:</p>
                      <pre className="whitespace-pre-wrap text-[11px] bg-card-bg p-2 rounded border border-border overflow-x-auto">
                        {log.stack_trace}
                      </pre>
                    </div>
                  )}
                  {log.metadata && (
                    <div>
                      <p className="text-muted mb-1 font-sans text-[11px]">Metadata:</p>
                      <pre className="whitespace-pre-wrap text-[11px] bg-card-bg p-2 rounded border border-border">
                        {JSON.stringify(log.metadata, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </details>
            ))}
          </div>
        </div>
      )}

      {/* Tab: Config */}
      {tab === "config" && (
        <div className="space-y-6 max-w-lg">
          <div>
            <label className="block text-sm font-medium mb-2">Token do projeto</label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                readOnly
                value={tokenRevealed && fullToken ? fullToken : `${project.token_preview}${"•".repeat(24)}`}
                className="flex-1 px-3 py-2 text-sm rounded-lg border border-border bg-card-bg font-mono text-xs"
              />
              <button
                onClick={() => setTokenRevealed(!tokenRevealed)}
                className="p-2 rounded-lg border border-border hover:bg-hover transition-colors"
                title={tokenRevealed ? "Esconder" : "Revelar"}
              >
                {tokenRevealed ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
              <button
                onClick={() => {
                  if (fullToken) {
                    navigator.clipboard.writeText(fullToken);
                    toast.success("Token copiado!");
                  } else {
                    toast("Gire o token primeiro para obter o valor completo", { icon: "ℹ️" });
                  }
                }}
                className="p-2 rounded-lg border border-border hover:bg-hover transition-colors"
                title="Copiar"
              >
                <Copy size={16} />
              </button>
            </div>
          </div>

          <div>
            <button
              onClick={() => setRotateConfirm(true)}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm rounded-lg border border-danger text-danger hover:bg-danger-surface transition-colors"
            >
              <RotateCcw size={14} />
              Girar token
            </button>
            <p className="text-xs text-muted mt-1">Gera um novo token e invalida o anterior imediatamente.</p>
          </div>

          <div>
            <button
              onClick={() => setInstructionsOpen(true)}
              className="px-4 py-2 text-sm rounded-lg border border-border hover:bg-hover transition-colors"
            >
              Ver instruções de integração
            </button>
          </div>
        </div>
      )}

      {/* Alert Drawer */}
      {drawerOpen && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/50" onClick={() => setDrawerOpen(false)} />
          <div className="relative w-full max-w-lg bg-card-bg border-l border-border h-full overflow-y-auto p-6 space-y-4">
            <button onClick={() => setDrawerOpen(false)} className="text-muted hover:text-foreground text-sm">
              ← Voltar
            </button>
            {drawerLoading && (
              <div className="flex items-center gap-2 text-muted"><Loader2 size={16} className="animate-spin" /> Carregando...</div>
            )}
            {selectedAlert && !drawerLoading && (
              <>
                <div className="flex items-center gap-2">
                  <span className={cn("px-2 py-0.5 rounded-full text-xs font-semibold", severityColors[selectedAlert.severity])}>
                    {selectedAlert.severity}
                  </span>
                  <span className={cn(
                    "px-2 py-0.5 rounded-full text-xs font-semibold",
                    selectedAlert.status === "open" ? "bg-danger-surface text-danger" :
                    selectedAlert.status === "acknowledged" ? "bg-warning-surface text-warning" :
                    "bg-success-surface text-success"
                  )}>
                    {statusLabels[selectedAlert.status]}
                  </span>
                </div>

                <h2 className="text-lg font-semibold">{selectedAlert.title}</h2>
                <p className="text-xs text-muted">
                  {selectedAlert.affected_component && `Componente: ${selectedAlert.affected_component} · `}
                  {new Date(selectedAlert.created_at).toLocaleString("pt-BR")}
                </p>

                <div className="text-sm whitespace-pre-wrap">{selectedAlert.explanation}</div>

                {selectedAlert.suggested_actions && selectedAlert.suggested_actions.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold mb-2">Ações sugeridas:</h3>
                    <ol className="list-decimal list-inside text-sm space-y-1 text-muted">
                      {selectedAlert.suggested_actions.map((action, i) => (
                        <li key={i}>{action}</li>
                      ))}
                    </ol>
                  </div>
                )}

                {selectedAlert.log_entry && (
                  <div>
                    <h3 className="text-sm font-semibold mb-2">Log original:</h3>
                    <div className="rounded-lg border border-border bg-hover p-3 text-xs font-mono space-y-1">
                      <p><span className="text-muted">Level:</span> {selectedAlert.log_entry.level}</p>
                      <p><span className="text-muted">Source:</span> {selectedAlert.log_entry.source || "—"}</p>
                      <p><span className="text-muted">Message:</span> {selectedAlert.log_entry.message}</p>
                      {selectedAlert.log_entry.stack_trace && (
                        <pre className="whitespace-pre-wrap mt-2 text-[11px]">{selectedAlert.log_entry.stack_trace}</pre>
                      )}
                    </div>
                  </div>
                )}

                {selectedAlert.status !== "resolved" && (
                  <div className="flex gap-2 pt-4 border-t border-border">
                    {selectedAlert.status === "open" && (
                      <button
                        onClick={() => handleAlertAction(selectedAlert.id, "acknowledged")}
                        className="inline-flex items-center gap-2 px-4 py-2 text-sm rounded-lg bg-warning-surface text-warning hover:opacity-80 transition"
                      >
                        <Check size={14} />
                        Reconhecer
                      </button>
                    )}
                    <button
                      onClick={() => handleAlertAction(selectedAlert.id, "resolved")}
                      className="inline-flex items-center gap-2 px-4 py-2 text-sm rounded-lg bg-success-surface text-success hover:opacity-80 transition"
                    >
                      <CheckCheck size={14} />
                      Marcar como resolvido
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* Rotate Token Confirm */}
      <Modal open={rotateConfirm} onClose={() => setRotateConfirm(false)} title="Girar token">
        <div className="space-y-4">
          <p className="text-sm text-muted">
            Isso vai gerar um novo token e <strong>invalidar o anterior imediatamente</strong>.
            Todos os sistemas que usam o token atual vão parar de enviar logs.
          </p>
          <div className="flex justify-end gap-2">
            <button onClick={() => setRotateConfirm(false)} className="px-4 py-2 text-sm rounded-lg border border-border hover:bg-hover">
              Cancelar
            </button>
            <button onClick={handleRotateToken} className="px-4 py-2 text-sm rounded-lg bg-danger text-white hover:opacity-80">
              Confirmar rotação
            </button>
          </div>
        </div>
      </Modal>

      {/* Instructions Modal */}
      <Modal open={instructionsOpen} onClose={() => setInstructionsOpen(false)} title="Instruções de Integração">
        <div className="space-y-4">
          <div className="flex gap-1 border-b border-border">
            {([
              { key: "http" as const, label: "HTTP (curl/código)" },
              { key: "agent" as const, label: "Agente (servidor)" },
              { key: "libs" as const, label: "Bibliotecas" },
            ]).map((t) => (
              <button
                key={t.key}
                onClick={() => setInstructionsTab(t.key)}
                className={cn(
                  "px-3 py-2 text-xs font-medium border-b-2 -mb-px",
                  instructionsTab === t.key ? "border-accent text-accent" : "border-transparent text-muted"
                )}
              >
                {t.label}
              </button>
            ))}
          </div>

          {instructionsTab === "http" && (
            <div className="space-y-3 text-xs">
              <p className="font-medium text-sm">cURL</p>
              <pre className="bg-hover p-3 rounded-lg overflow-x-auto whitespace-pre-wrap font-mono">
{`curl -X POST ${apiBase}/api/logs/ingest \\
  -H "Authorization: Bearer {token}" \\
  -H "Content-Type: application/json" \\
  -d '{"level": "error", "message": "Descricao do erro", "source": "arquivo.py"}'`}
              </pre>
              <p className="font-medium text-sm mt-3">Python</p>
              <pre className="bg-hover p-3 rounded-lg overflow-x-auto whitespace-pre-wrap font-mono">
{`import requests
import traceback

try:
    # seu codigo
    pass
except Exception as e:
    requests.post(
        "${apiBase}/api/logs/ingest",
        headers={"Authorization": "Bearer {token}"},
        json={
            "level": "error",
            "message": str(e),
            "stack_trace": traceback.format_exc(),
            "source": __file__,
        }
    )`}
              </pre>
            </div>
          )}

          {instructionsTab === "agent" && (
            <div className="space-y-3 text-xs">
              <p className="text-sm">Instale o agente Memora no servidor do cliente:</p>
              <ol className="list-decimal list-inside space-y-2 text-muted">
                <li>Baixe o agente: <code className="bg-hover px-1 rounded">curl -O {apiBase}/agent/memora_agent.py</code></li>
                <li>Configure <code className="bg-hover px-1 rounded">config.yaml</code> com seu token e caminhos de log</li>
                <li>Instale: <code className="bg-hover px-1 rounded">sudo bash install.sh</code></li>
              </ol>
              <p className="text-muted mt-2">O agente monitora arquivos de log em tempo real e envia automaticamente para o Memora.</p>
            </div>
          )}

          {instructionsTab === "libs" && (
            <div className="space-y-3 text-xs">
              <p className="font-medium text-sm">Python (logging handler)</p>
              <pre className="bg-hover p-3 rounded-lg overflow-x-auto whitespace-pre-wrap font-mono">
{`import logging
import requests

class MemoraHandler(logging.Handler):
    def __init__(self, url, token):
        super().__init__()
        self.url = url + "/api/logs/ingest"
        self.token = token

    def emit(self, record):
        requests.post(self.url, headers={
            "Authorization": f"Bearer {self.token}"
        }, json={
            "level": record.levelname.lower(),
            "message": self.format(record),
            "source": f"{record.pathname}:{record.lineno}",
        })

handler = MemoraHandler("${apiBase}", "{token}")
handler.setLevel(logging.WARNING)
logging.getLogger().addHandler(handler)`}
              </pre>

              <p className="font-medium text-sm mt-3">Node.js (winston transport)</p>
              <pre className="bg-hover p-3 rounded-lg overflow-x-auto whitespace-pre-wrap font-mono">
{`const Transport = require("winston-transport");

class MemoraTransport extends Transport {
  constructor(opts) {
    super(opts);
    this.url = opts.url + "/api/logs/ingest";
    this.token = opts.token;
  }
  log(info, callback) {
    fetch(this.url, {
      method: "POST",
      headers: {
        "Authorization": \`Bearer \${this.token}\`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        level: info.level,
        message: info.message,
      }),
    }).finally(callback);
  }
}

logger.add(new MemoraTransport({
  url: "${apiBase}",
  token: "{token}",
  level: "warn",
}));`}
              </pre>
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
}
