"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  ShieldAlert,
  Plus,
  Activity,
  AlertTriangle,
  Clock,
  Loader2,
  Copy,
  ExternalLink,
  Trash2,
} from "lucide-react";
import toast from "react-hot-toast";
import { cn } from "@/lib/utils";
import { Modal } from "@/components/ui/modal";
import {
  listMonitorProjects,
  createMonitorProject,
  deleteMonitorProject,
} from "@/lib/api";
import type { MonitoredProject } from "@/lib/types";

function timeAgo(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "agora";
  if (mins < 60) return `há ${mins}min`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `há ${hours}h`;
  const days = Math.floor(hours / 24);
  return `há ${days}d`;
}

function projectStatus(lastLogAt: string | null | undefined): { label: string; color: string } {
  if (!lastLogAt) return { label: "Sem dados", color: "text-muted" };
  const diff = Date.now() - new Date(lastLogAt).getTime();
  const mins = diff / 60000;
  if (mins < 5) return { label: "Online", color: "text-success" };
  if (mins < 60) return { label: "Idle", color: "text-warning" };
  return { label: "Offline", color: "text-danger" };
}

export default function MonitorPage() {
  const [projects, setProjects] = useState<MonitoredProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [creating, setCreating] = useState(false);
  const [createdToken, setCreatedToken] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<MonitoredProject | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchProjects = useCallback(async () => {
    try {
      const data = await listMonitorProjects();
      setProjects(data);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao carregar projetos");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const totalAlerts = projects.reduce((sum, p) => sum + p.open_alerts, 0);
  const totalLogsToday = projects.reduce((sum, p) => sum + p.logs_today, 0);
  const criticalAlerts = projects.filter((p) => p.open_alerts > 0).length;
  const lastProject = projects.reduce<MonitoredProject | null>((best, p) => {
    if (!p.last_log_at) return best;
    if (!best?.last_log_at) return p;
    return new Date(p.last_log_at) > new Date(best.last_log_at) ? p : best;
  }, null);

  async function handleCreate() {
    if (!newName.trim()) {
      toast.error("Nome do projeto obrigatório");
      return;
    }
    setCreating(true);
    try {
      const result = await createMonitorProject({ name: newName, description: newDesc || undefined });
      setCreatedToken(result.token);
      setProjects((prev) => [
        {
          id: result.id,
          name: result.name,
          description: result.description,
          token_preview: result.token_preview,
          is_active: true,
          logs_today: 0,
          open_alerts: 0,
          last_log_at: undefined,
          created_at: new Date().toISOString(),
        },
        ...prev,
      ]);
      toast.success("Projeto criado!");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao criar projeto");
    } finally {
      setCreating(false);
    }
  }

  function closeModal() {
    setCreateOpen(false);
    setNewName("");
    setNewDesc("");
    setCreatedToken(null);
  }

  return (
    <div className="p-5 lg:p-8 space-y-8">
      <div className="flex items-center justify-between pt-2">
        <div className="flex items-center gap-3">
          <ShieldAlert size={24} className="text-accent" />
          <h1 className="text-xl font-semibold">Monitor de Erros</h1>
        </div>
        <button
          onClick={() => setCreateOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors"
        >
          <Plus size={16} />
          Adicionar Projeto
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl border border-border bg-card-bg p-5">
          <div className="flex items-center gap-3 mb-2">
            <Activity size={18} className="text-accent" />
            <span className="text-sm text-muted">Projetos Monitorados</span>
          </div>
          <p className="text-2xl font-bold">{projects.length}</p>
        </div>
        <div className="rounded-xl border border-border bg-card-bg p-5">
          <div className="flex items-center gap-3 mb-2">
            <AlertTriangle size={18} className="text-warning" />
            <span className="text-sm text-muted">Alertas Abertos</span>
          </div>
          <p className="text-2xl font-bold">{totalAlerts}</p>
        </div>
        <div className="rounded-xl border border-border bg-card-bg p-5">
          <div className="flex items-center gap-3 mb-2">
            <ShieldAlert size={18} className="text-danger" />
            <span className="text-sm text-muted">Projetos com Alertas</span>
          </div>
          <p className="text-2xl font-bold">{criticalAlerts}</p>
        </div>
        <div className="rounded-xl border border-border bg-card-bg p-5">
          <div className="flex items-center gap-3 mb-2">
            <Clock size={18} className="text-muted" />
            <span className="text-sm text-muted">Último Erro</span>
          </div>
          <p className="text-2xl font-bold">{lastProject ? timeAgo(lastProject.last_log_at) : "—"}</p>
        </div>
      </div>

      {/* Projects List */}
      <div className="rounded-xl border border-border bg-card-bg divide-y divide-border">
        {loading && (
          <div className="flex items-center justify-center gap-2 px-6 py-12 text-muted text-sm">
            <Loader2 size={16} className="animate-spin" />
            Carregando...
          </div>
        )}
        {!loading && projects.length === 0 && (
          <div className="px-6 py-12 text-center text-muted text-sm">
            Nenhum projeto monitorado. Clique em &ldquo;Adicionar Projeto&rdquo; para começar.
          </div>
        )}
        {!loading &&
          projects.map((project) => {
            const status = projectStatus(project.last_log_at);
            return (
              <Link
                key={project.id}
                href={`/dashboard/monitor/${project.id}`}
                className="group flex items-center gap-4 px-6 py-4 hover:bg-hover transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">{project.name}</span>
                    <span className={cn("text-xs font-medium", status.color)}>
                      ● {status.label}
                    </span>
                  </div>
                  {project.description && (
                    <p className="text-xs text-muted mt-0.5 truncate">{project.description}</p>
                  )}
                </div>
                <div className="flex items-center gap-6 text-sm text-muted shrink-0">
                  <div className="text-center">
                    <p className="font-medium text-foreground">{project.logs_today}</p>
                    <p className="text-xs">Logs hoje</p>
                  </div>
                  <div className="text-center">
                    <p className={cn("font-medium", project.open_alerts > 0 ? "text-danger" : "text-foreground")}>
                      {project.open_alerts}
                    </p>
                    <p className="text-xs">Alertas</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs">{timeAgo(project.last_log_at)}</p>
                    <p className="text-xs">Último log</p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setDeleteTarget(project);
                    }}
                    className="p-1.5 rounded-lg border border-border hover:bg-hover transition-colors text-danger opacity-0 group-hover:opacity-100"
                    title="Excluir projeto"
                  >
                    <Trash2 size={14} />
                  </button>
                  <ExternalLink size={14} className="text-muted" />
                </div>
              </Link>
            );
          })}
      </div>

      {/* Alerts link */}
      {totalAlerts > 0 && (
        <Link
          href="/dashboard/monitor/alerts"
          className="inline-flex items-center gap-2 text-sm text-accent hover:underline"
        >
          Ver todos os alertas ({totalAlerts})
          <ExternalLink size={14} />
        </Link>
      )}

      {/* Delete Confirmation Modal */}
      <Modal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Excluir Projeto"
      >
        <div className="space-y-4">
          <p className="text-sm text-muted">
            Tem certeza que deseja excluir o projeto{" "}
            <strong className="text-foreground">{deleteTarget?.name}</strong>?
            Todos os logs e alertas associados serão removidos.
          </p>
          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={() => setDeleteTarget(null)}
              className="px-4 py-2 text-sm rounded-lg border border-border hover:bg-hover transition-colors"
            >
              Cancelar
            </button>
            <button
              onClick={async () => {
                if (!deleteTarget) return;
                setDeleting(true);
                try {
                  await deleteMonitorProject(deleteTarget.id);
                  setProjects((prev) => prev.filter((p) => p.id !== deleteTarget.id));
                  toast.success("Projeto excluído");
                  setDeleteTarget(null);
                } catch (err) {
                  toast.error(err instanceof Error ? err.message : "Erro ao excluir");
                } finally {
                  setDeleting(false);
                }
              }}
              disabled={deleting}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-danger hover:bg-danger/80 text-white transition-colors disabled:opacity-50"
            >
              {deleting && <Loader2 size={14} className="animate-spin" />}
              Excluir
            </button>
          </div>
        </div>
      </Modal>

      {/* Create Project Modal */}
      <Modal open={createOpen} onClose={closeModal} title="Adicionar Projeto">
        {!createdToken ? (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Nome do projeto *</label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder='Ex: "CEBI ERP", "Portal do Cliente"'
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground placeholder:text-muted"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Descrição (opcional)</label>
              <input
                type="text"
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                placeholder="Breve descrição do sistema"
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground placeholder:text-muted"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={closeModal}
                className="px-4 py-2 text-sm rounded-lg border border-border hover:bg-hover transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleCreate}
                disabled={creating}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors disabled:opacity-50"
              >
                {creating && <Loader2 size={14} className="animate-spin" />}
                Criar projeto
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-muted">
              Projeto criado! Use este token para enviar logs. Ele só será exibido esta vez.
            </p>
            <div className="flex items-center gap-2">
              <input
                type="text"
                readOnly
                value={createdToken}
                className="flex-1 px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground font-mono text-xs"
              />
              <button
                onClick={() => {
                  navigator.clipboard.writeText(createdToken);
                  toast.success("Token copiado!");
                }}
                className="p-2 rounded-lg border border-border hover:bg-hover transition-colors"
                title="Copiar"
              >
                <Copy size={16} />
              </button>
            </div>
            <div className="rounded-lg bg-hover p-3 text-xs font-mono text-muted whitespace-pre-wrap">
{`curl -X POST ${typeof window !== "undefined" ? window.location.origin : ""}/api/logs/ingest \\
  -H "Authorization: Bearer ${createdToken}" \\
  -H "Content-Type: application/json" \\
  -d '{"level": "error", "message": "Teste"}'`}
            </div>
            <div className="flex justify-end pt-2">
              <button
                onClick={closeModal}
                className="px-4 py-2 text-sm font-medium rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors"
              >
                Fechar
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
