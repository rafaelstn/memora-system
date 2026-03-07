"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, Clock, CheckCircle, Filter, TrendingUp, TrendingDown, Target } from "lucide-react";
import { useAuth } from "@/lib/hooks/useAuth";
import { listIncidents, getIncidentStats } from "@/lib/api";
import type { Incident, IncidentStats, IncidentStatus, IncidentSeverity } from "@/lib/types";

const statusLabels: Record<IncidentStatus, string> = {
  open: "Aberto",
  investigating: "Investigando",
  mitigated: "Mitigado",
  resolved: "Resolvido",
};

const statusColors: Record<IncidentStatus, string> = {
  open: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  investigating: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  mitigated: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  resolved: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
};

const severityColors: Record<IncidentSeverity, string> = {
  low: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  medium: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  high: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  critical: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
};

function timeAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}min`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h`;
  return `${Math.floor(hours / 24)}d`;
}

export default function IncidentsPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [stats, setStats] = useState<IncidentStats | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    if (!user || !["admin", "dev"].includes(user.role)) return;
    loadData();
  }, [user, statusFilter, page]);

  async function loadData() {
    try {
      const [list, st] = await Promise.all([
        listIncidents({ status: statusFilter || undefined, page }),
        getIncidentStats(),
      ]);
      setIncidents(list.incidents);
      setTotal(list.total);
      setStats(st);
    } catch {
      /* silently fail */
    }
  }

  if (!user || !["admin", "dev"].includes(user.role)) {
    return <div className="p-8 text-muted">Acesso restrito.</div>;
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Incidentes</h1>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <div className="rounded-xl border border-border bg-card p-5">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-red-100 dark:bg-red-900/30">
                <AlertTriangle size={20} className="text-red-600 dark:text-red-400" />
              </div>
              <div>
                <p className="text-xs text-muted">Abertos agora</p>
                <p className="text-2xl font-bold">{stats.active}</p>
              </div>
            </div>
          </div>
          <div className="rounded-xl border border-border bg-card p-5">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-100 dark:bg-green-900/30">
                <CheckCircle size={20} className="text-green-600 dark:text-green-400" />
              </div>
              <div>
                <p className="text-xs text-muted">Resolvidos este mes</p>
                <p className="text-2xl font-bold">{stats.resolved_month}</p>
              </div>
            </div>
          </div>
          <div className="rounded-xl border border-border bg-card p-5">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
                <Clock size={20} className="text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-xs text-muted">MTTR (geral)</p>
                <p className="text-2xl font-bold">
                  {stats.avg_resolution_hours != null
                    ? `${stats.avg_resolution_hours}h`
                    : "N/A"}
                </p>
                {stats.mttr_trend != null && (
                  <p className={`text-[10px] flex items-center gap-0.5 ${stats.mttr_trend <= 0 ? "text-green-600" : "text-red-600"}`}>
                    {stats.mttr_trend <= 0 ? <TrendingDown size={10} /> : <TrendingUp size={10} />}
                    {Math.abs(stats.mttr_trend)}% vs semana anterior
                  </p>
                )}
              </div>
            </div>
          </div>
          {stats.most_affected_project && (
            <div className="rounded-xl border border-border bg-card p-5">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-orange-100 dark:bg-orange-900/30">
                  <Target size={20} className="text-orange-600 dark:text-orange-400" />
                </div>
                <div>
                  <p className="text-xs text-muted">Mais afetado (30d)</p>
                  <p className="text-sm font-bold truncate">{stats.most_affected_project}</p>
                  <p className="text-xs text-muted">{stats.most_affected_count} incidentes</p>
                </div>
              </div>
            </div>
          )}
          <div className="rounded-xl border border-border bg-card p-5">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
                <TrendingUp size={20} className="text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <p className="text-xs text-muted">Total historico</p>
                <p className="text-2xl font-bold">{stats.total}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3">
        <Filter size={16} className="text-muted" />
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="text-sm border border-border rounded-lg px-3 py-1.5 bg-card"
        >
          <option value="">Todos os status</option>
          <option value="open">Aberto</option>
          <option value="investigating">Investigando</option>
          <option value="mitigated">Mitigado</option>
          <option value="resolved">Resolvido</option>
        </select>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-hover/50">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-muted">Status</th>
              <th className="text-left px-4 py-3 font-medium text-muted">Titulo</th>
              <th className="text-left px-4 py-3 font-medium text-muted">Projeto</th>
              <th className="text-left px-4 py-3 font-medium text-muted">Severidade</th>
              <th className="text-left px-4 py-3 font-medium text-muted">Declarado</th>
              <th className="text-left px-4 py-3 font-medium text-muted">Por</th>
            </tr>
          </thead>
          <tbody>
            {incidents.map((inc) => (
              <tr
                key={inc.id}
                onClick={() => router.push(`/dashboard/monitor/incidents/${inc.id}`)}
                className="border-t border-border hover:bg-hover/30 cursor-pointer transition-colors"
              >
                <td className="px-4 py-3">
                  <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[inc.status]}`}>
                    {statusLabels[inc.status]}
                  </span>
                </td>
                <td className="px-4 py-3 font-medium">{inc.title}</td>
                <td className="px-4 py-3 text-muted">{inc.project_name}</td>
                <td className="px-4 py-3">
                  <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-medium ${severityColors[inc.severity]}`}>
                    {inc.severity.toUpperCase()}
                  </span>
                </td>
                <td className="px-4 py-3 text-muted">{timeAgo(inc.declared_at)}</td>
                <td className="px-4 py-3 text-muted">{inc.declared_by_name}</td>
              </tr>
            ))}
            {incidents.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-muted">
                  Nenhum incidente encontrado.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {total > 20 && (
        <div className="flex justify-center gap-2">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="px-3 py-1 rounded border border-border text-sm disabled:opacity-40"
          >
            Anterior
          </button>
          <span className="px-3 py-1 text-sm text-muted">
            Pagina {page} de {Math.ceil(total / 20)}
          </span>
          <button
            onClick={() => setPage(page + 1)}
            disabled={page * 20 >= total}
            className="px-3 py-1 rounded border border-border text-sm disabled:opacity-40"
          >
            Proxima
          </button>
        </div>
      )}
    </div>
  );
}
