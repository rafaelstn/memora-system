"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  AlertTriangle,
  Download,
  Loader2,
} from "lucide-react";
import toast from "react-hot-toast";
import { cn } from "@/lib/utils";
import {
  listMonitorAlerts,
  listMonitorProjects,
  getMonitorAlert,
  updateAlertStatus,
  declareIncident,
} from "@/lib/api";
import { useAuth } from "@/lib/hooks/useAuth";
import type { ErrorAlertSummary, ErrorAlertDetail, MonitoredProject, AlertSeverity, AlertStatus } from "@/lib/types";

const severityColors: Record<AlertSeverity, string> = {
  low: "bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300",
  medium: "bg-yellow-100 text-yellow-700 dark:bg-yellow-500/15 dark:text-yellow-300",
  high: "bg-orange-100 text-orange-700 dark:bg-orange-500/15 dark:text-orange-300",
  critical: "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300",
};

const statusLabels: Record<AlertStatus, string> = {
  open: "Aberto",
  acknowledged: "Reconhecido",
  resolved: "Resolvido",
};

export default function AlertsGlobalPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [alerts, setAlerts] = useState<ErrorAlertSummary[]>([]);
  const [projects, setProjects] = useState<MonitoredProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [projectFilter, setProjectFilter] = useState<string>("all");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  // Drawer
  const [selectedAlert, setSelectedAlert] = useState<ErrorAlertDetail | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Incident modal
  const [showIncidentModal, setShowIncidentModal] = useState(false);
  const [incidentTitle, setIncidentTitle] = useState("");
  const [incidentSeverity, setIncidentSeverity] = useState("high");
  const [declaringIncident, setDeclaringIncident] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const params: Record<string, string> = {};
      if (projectFilter !== "all") params.project_id = projectFilter;
      if (severityFilter !== "all") params.severity = severityFilter;
      if (statusFilter !== "all") params.status = statusFilter;

      const [alertsData, projectsData] = await Promise.all([
        listMonitorAlerts(params),
        listMonitorProjects(),
      ]);
      setAlerts(alertsData);
      setProjects(projectsData);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao carregar alertas");
    } finally {
      setLoading(false);
    }
  }, [projectFilter, severityFilter, statusFilter]);

  useEffect(() => {
    setLoading(true);
    fetchData();
  }, [fetchData]);

  async function openAlert(alertId: string) {
    setDrawerOpen(true);
    try {
      const detail = await getMonitorAlert(alertId);
      setSelectedAlert(detail);
    } catch {
      toast.error("Erro ao carregar alerta");
    }
  }

  async function handleAction(alertId: string, status: "acknowledged" | "resolved") {
    try {
      await updateAlertStatus(alertId, status);
      setAlerts((prev) => prev.map((a) => (a.id === alertId ? { ...a, status } : a)));
      if (selectedAlert?.id === alertId) {
        setSelectedAlert({ ...selectedAlert, status });
      }
      toast.success(status === "acknowledged" ? "Reconhecido" : "Resolvido");
    } catch (err) {
      toast.error("Erro");
    }
  }

  function openIncidentModal(alert: ErrorAlertDetail) {
    setIncidentTitle(alert.title);
    setIncidentSeverity(alert.severity === "critical" ? "critical" : "high");
    setShowIncidentModal(true);
  }

  async function handleDeclareIncident() {
    if (!selectedAlert) return;
    setDeclaringIncident(true);
    try {
      const result = await declareIncident({
        alert_id: selectedAlert.id,
        project_id: selectedAlert.project_id,
        title: incidentTitle,
        severity: incidentSeverity,
      });
      toast.success("Incidente declarado");
      setShowIncidentModal(false);
      setDrawerOpen(false);
      router.push(`/dashboard/monitor/incidents/${result.id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao declarar incidente");
    } finally {
      setDeclaringIncident(false);
    }
  }

  function exportCSV() {
    const header = "ID,Projeto,Título,Severidade,Status,Data\n";
    const rows = alerts.map((a) =>
      `"${a.id}","${a.project_name}","${a.title}","${a.severity}","${a.status}","${a.created_at}"`
    ).join("\n");
    const blob = new Blob([header + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `memora-alertas-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="p-5 lg:p-8 space-y-6">
      <div className="flex items-center gap-3">
        <button onClick={() => router.push("/dashboard/monitor")} className="p-1.5 rounded-lg hover:bg-hover text-muted">
          <ArrowLeft size={18} />
        </button>
        <AlertTriangle size={22} className="text-warning" />
        <h1 className="text-xl font-semibold flex-1">Todos os Alertas</h1>
        <button
          onClick={exportCSV}
          className="inline-flex items-center gap-2 px-3 py-1.5 text-xs rounded-lg border border-border hover:bg-hover transition-colors"
        >
          <Download size={14} />
          Exportar CSV
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={projectFilter}
          onChange={(e) => setProjectFilter(e.target.value)}
          className="px-3 py-2 text-sm rounded-lg border border-border bg-card-bg"
        >
          <option value="all">Todos os projetos</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="px-3 py-2 text-sm rounded-lg border border-border bg-card-bg"
        >
          <option value="all">Todas severidades</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 text-sm rounded-lg border border-border bg-card-bg"
        >
          <option value="all">Todos status</option>
          <option value="open">Aberto</option>
          <option value="acknowledged">Reconhecido</option>
          <option value="resolved">Resolvido</option>
        </select>
      </div>

      {/* Alerts Table */}
      <div className="rounded-lg border border-border bg-card-bg overflow-hidden">
        <table className="w-full">
          <thead className="border-b border-border bg-hover">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">Severidade</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">Título</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">Projeto</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">Componente</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">Status</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">Data</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {loading && (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-sm text-muted">
                  <Loader2 size={16} className="animate-spin inline mr-2" />Carregando...
                </td>
              </tr>
            )}
            {!loading && alerts.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-sm text-muted">
                  Nenhum alerta encontrado.
                </td>
              </tr>
            )}
            {!loading && alerts.map((alert) => (
              <tr
                key={alert.id}
                onClick={() => openAlert(alert.id)}
                className="hover:bg-hover cursor-pointer"
              >
                <td className="px-4 py-3">
                  <span className={cn("px-2 py-0.5 rounded-full text-[11px] font-semibold", severityColors[alert.severity])}>
                    {alert.severity}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm font-medium max-w-xs truncate">{alert.title}</td>
                <td className="px-4 py-3 text-sm text-muted">{alert.project_name}</td>
                <td className="px-4 py-3 text-sm text-muted">{alert.affected_component || "—"}</td>
                <td className="px-4 py-3">
                  <span className={cn(
                    "px-2 py-0.5 rounded-full text-[11px] font-semibold",
                    alert.status === "open" ? "bg-danger-surface text-danger" :
                    alert.status === "acknowledged" ? "bg-warning-surface text-warning" :
                    "bg-success-surface text-success"
                  )}>
                    {statusLabels[alert.status]}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs text-muted">
                  {new Date(alert.created_at).toLocaleString("pt-BR")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Incident Declaration Modal */}
      {showIncidentModal && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50">
          <div className="bg-card-bg rounded-xl border border-border p-6 w-full max-w-md space-y-4">
            <h3 className="text-lg font-bold">Declarar Incidente</h3>
            <p className="text-sm text-muted">Declarar este alerta como incidente ativo?</p>
            <div>
              <label className="text-sm text-muted block mb-1">Titulo</label>
              <input
                type="text"
                value={incidentTitle}
                onChange={(e) => setIncidentTitle(e.target.value)}
                className="w-full text-sm border border-border rounded-lg px-3 py-2 bg-card-bg"
              />
            </div>
            <div>
              <label className="text-sm text-muted block mb-1">Severidade</label>
              <select
                value={incidentSeverity}
                onChange={(e) => setIncidentSeverity(e.target.value)}
                className="w-full text-sm border border-border rounded-lg px-3 py-2 bg-card-bg"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowIncidentModal(false)}
                className="px-4 py-2 rounded-lg text-sm border border-border hover:bg-hover"
              >
                Cancelar
              </button>
              <button
                onClick={handleDeclareIncident}
                disabled={declaringIncident || !incidentTitle.trim()}
                className="px-4 py-2 rounded-lg text-sm bg-red-600 text-white hover:bg-red-700 disabled:opacity-40"
              >
                {declaringIncident ? "Declarando..." : "Declarar Incidente"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Drawer */}
      {drawerOpen && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/50" onClick={() => { setDrawerOpen(false); setSelectedAlert(null); }} />
          <div className="relative w-full max-w-lg bg-card-bg border-l border-border h-full overflow-y-auto p-6 space-y-4">
            <button onClick={() => { setDrawerOpen(false); setSelectedAlert(null); }} className="text-muted hover:text-foreground text-sm">
              ← Voltar
            </button>
            {!selectedAlert ? (
              <div className="flex items-center gap-2 text-muted"><Loader2 size={16} className="animate-spin" /> Carregando...</div>
            ) : (
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
                  Projeto: {selectedAlert.project_name}
                  {selectedAlert.affected_component && ` · Componente: ${selectedAlert.affected_component}`}
                </p>
                <div className="text-sm whitespace-pre-wrap">{selectedAlert.explanation}</div>

                {selectedAlert.suggested_actions && selectedAlert.suggested_actions.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold mb-2">Ações sugeridas:</h3>
                    <ol className="list-decimal list-inside text-sm space-y-1 text-muted">
                      {selectedAlert.suggested_actions.map((a, i) => <li key={i}>{a}</li>)}
                    </ol>
                  </div>
                )}

                {selectedAlert.status !== "resolved" && (
                  <div className="flex flex-wrap gap-2 pt-4 border-t border-border">
                    {selectedAlert.status === "open" && (
                      <button
                        onClick={() => handleAction(selectedAlert.id, "acknowledged")}
                        className="px-4 py-2 text-sm rounded-lg bg-warning-surface text-warning"
                      >
                        Reconhecer
                      </button>
                    )}
                    <button
                      onClick={() => handleAction(selectedAlert.id, "resolved")}
                      className="px-4 py-2 text-sm rounded-lg bg-success-surface text-success"
                    >
                      Resolver
                    </button>
                    {["high", "critical"].includes(selectedAlert.severity) &&
                      user && ["admin", "dev"].includes(user.role) && (
                      <button
                        onClick={() => openIncidentModal(selectedAlert)}
                        className="px-4 py-2 text-sm rounded-lg bg-red-600 text-white hover:bg-red-700"
                      >
                        Declarar Incidente
                      </button>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
