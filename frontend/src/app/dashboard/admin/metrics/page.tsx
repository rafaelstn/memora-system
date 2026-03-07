"use client";

import { useState, useMemo, useEffect } from "react";
import {
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import {
  MessageSquare,
  DollarSign,
  TrendingUp,
  Users,
  ArrowUpDown,
  Download,
  Loader2,
  Trash2,
} from "lucide-react";
import toast from "react-hot-toast";
import { cn, formatCurrency } from "@/lib/utils";
import { RoleBadge } from "@/components/ui/badge";
import { Modal } from "@/components/ui/modal";
import { getMetrics, getDailyUsage, getUserUsage, getModelUsage, listAdminRepos, deleteAdminRepo } from "@/lib/api";
import type { Role } from "@/lib/types";

interface MetricsSummary {
  total_questions: number;
  total_cost_brl: number;
  avg_cost_per_question_brl: number;
  active_users_7d: number;
}

interface DailyUsage {
  date: string;
  questions: number;
  cost_brl: number;
}

interface UserUsage {
  user_id: string;
  name: string;
  role: string;
  total_questions: number;
  total_cost_brl: number;
  last_activity: string | null;
}

interface ModelUsage {
  model: string;
  questions: number;
  cost_usd: number;
  percentage: number;
}

interface RepoUsage {
  name: string;
  chunks_count: number;
  last_indexed?: string;
  status: string;
}

type UserSortKey = keyof Pick<UserUsage, "name" | "role" | "total_questions" | "total_cost_brl" | "last_activity">;
type RepoSortKey = "name" | "chunks_count" | "last_indexed";

const PIE_COLORS = ["#6366f1", "#8b5cf6", "#a78bfa", "#c4b5fd"];

function SortHeader({ label, active, onClick }: { label: string; active: boolean; asc?: boolean; onClick: () => void }) {
  return (
    <th
      className="px-4 py-3 text-left text-xs font-medium text-muted uppercase cursor-pointer select-none hover:text-foreground"
      onClick={onClick}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        <ArrowUpDown size={12} className={cn(active && "text-accent")} />
      </span>
    </th>
  );
}

export default function MetricsPage() {
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [dailyUsage, setDailyUsage] = useState<DailyUsage[]>([]);
  const [userUsage, setUserUsage] = useState<UserUsage[]>([]);
  const [modelUsage, setModelUsage] = useState<ModelUsage[]>([]);
  const [repos, setRepos] = useState<RepoUsage[]>([]);
  const [loading, setLoading] = useState(true);

  const [userSort, setUserSort] = useState<{ key: UserSortKey; asc: boolean }>({ key: "total_questions", asc: false });
  const [repoSort, setRepoSort] = useState<{ key: RepoSortKey; asc: boolean }>({ key: "name", asc: true });
  const [deleteRepoName, setDeleteRepoName] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    Promise.all([
      getMetrics(),
      getDailyUsage(),
      getUserUsage(),
      getModelUsage(),
      listAdminRepos(),
    ])
      .then(([m, d, u, mo, r]) => {
        setMetrics(m);
        setDailyUsage(d);
        setUserUsage(u);
        setModelUsage(mo);
        setRepos(r);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const sortedUsers = useMemo(() => {
    return [...userUsage].sort((a, b) => {
      const va = a[userSort.key];
      const vb = b[userSort.key];
      if (typeof va === "string") return userSort.asc ? va.localeCompare(vb as string) : (vb as string).localeCompare(va);
      return userSort.asc ? (va as number) - (vb as number) : (vb as number) - (va as number);
    });
  }, [userUsage, userSort]);

  const sortedRepos = useMemo(() => {
    return [...repos].sort((a, b) => {
      const va = a[repoSort.key as keyof RepoUsage] ?? "";
      const vb = b[repoSort.key as keyof RepoUsage] ?? "";
      if (typeof va === "string") return repoSort.asc ? va.localeCompare(vb as string) : (vb as string).localeCompare(va);
      return repoSort.asc ? (va as number) - (vb as number) : (vb as number) - (va as number);
    });
  }, [repos, repoSort]);

  function toggleUserSort(key: UserSortKey) {
    setUserSort((prev) => ({ key, asc: prev.key === key ? !prev.asc : false }));
  }

  function toggleRepoSort(key: RepoSortKey) {
    setRepoSort((prev) => ({ key, asc: prev.key === key ? !prev.asc : false }));
  }

  function exportCSV() {
    const header = "Nome,Role,Perguntas,Custo (R$),Última Atividade\n";
    const rows = sortedUsers.map((u) =>
      `${u.name},${u.role},${u.total_questions},${u.total_cost_brl.toFixed(2)},${u.last_activity || ""}`
    ).join("\n");
    const blob = new Blob([header + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "uso-usuarios.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  async function handleDeleteRepo() {
    if (!deleteRepoName) return;
    setDeleting(true);
    try {
      const result = await deleteAdminRepo(deleteRepoName);
      toast.success(`Repositorio "${result.repo_name}" removido (${result.chunks_removed} chunks)`);
      setRepos((prev) => prev.filter((r) => r.name !== deleteRepoName));
      setDeleteRepoName(null);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao remover repositorio");
    } finally {
      setDeleting(false);
    }
  }

  if (loading) {
    return (
      <div className="p-5 lg:p-8 flex items-center justify-center gap-2 py-20 text-muted text-sm">
        <Loader2 size={16} className="animate-spin" />
        Carregando métricas...
      </div>
    );
  }

  const summaryCards = [
    {
      icon: MessageSquare,
      label: "Total de perguntas",
      value: (metrics?.total_questions ?? 0).toLocaleString("pt-BR"),
      sub: "Todas as conversas",
    },
    {
      icon: DollarSign,
      label: "Custo total",
      value: formatCurrency(metrics?.total_cost_brl ?? 0),
      sub: "Acumulado",
    },
    {
      icon: TrendingUp,
      label: "Custo médio/pergunta",
      value: formatCurrency(metrics?.avg_cost_per_question_brl ?? 0),
      sub: "Média geral",
    },
    {
      icon: Users,
      label: "Usuários ativos (7d)",
      value: (metrics?.active_users_7d ?? 0).toString(),
      sub: "Últimos 7 dias",
    },
  ];

  return (
    <div className="p-5 lg:p-8 space-y-8">
      <div className="pt-2">
        <h1 className="text-xl font-semibold">Métricas de Uso</h1>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {summaryCards.map((card) => (
          <div key={card.label} className="rounded-xl border border-border bg-card-bg p-5">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 rounded-lg bg-accent-surface">
                <card.icon size={18} className="text-accent" />
              </div>
              <span className="text-sm text-muted">{card.label}</span>
            </div>
            <p className="text-2xl font-bold">{card.value}</p>
            <p className="text-xs text-muted mt-1">{card.sub}</p>
          </div>
        ))}
      </div>

      {/* Daily Usage Chart */}
      <div className="rounded-xl border border-border bg-card-bg p-6">
        <h2 className="text-lg font-semibold mb-4">Uso diário — últimos 30 dias</h2>
        <div className="h-80">
          {dailyUsage.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted text-sm">
              Nenhum dado de uso disponível ainda.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={dailyUsage}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11, fill: "var(--muted)" }}
                  tickFormatter={(v: string) => v.slice(5)}
                />
                <YAxis yAxisId="left" tick={{ fontSize: 11, fill: "var(--muted)" }} />
                <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: "var(--muted)" }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "var(--card-bg)",
                    border: "1px solid var(--border)",
                    borderRadius: "10px",
                    fontSize: "13px",
                    color: "var(--foreground)",
                  }}
                  /* eslint-disable @typescript-eslint/no-explicit-any */
                  formatter={((value: any, name: any) => {
                    const v = Number(value) || 0;
                    if (name === "cost_brl") return [formatCurrency(v), "Custo (R$)"];
                    return [v, "Perguntas"];
                  }) as any}
                  labelFormatter={((label: any) => `Data: ${label}`) as any}
                />
                <Legend
                  formatter={((value: any) => (value === "questions" ? "Perguntas" : "Custo (R$)")) as any}
                  /* eslint-enable @typescript-eslint/no-explicit-any */
                />
                <Bar yAxisId="right" dataKey="cost_brl" fill="rgba(99,102,241,0.3)" radius={[4, 4, 0, 0]} />
                <Line yAxisId="left" type="monotone" dataKey="questions" stroke="#6366f1" strokeWidth={2} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* User Usage Table */}
      <div className="rounded-lg border border-border bg-card-bg overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-lg font-semibold">Uso por usuário</h2>
          <button
            onClick={exportCSV}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg border border-border hover:bg-hover text-muted hover:text-foreground transition-colors"
          >
            <Download size={14} />
            Exportar CSV
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="border-b border-border bg-hover">
              <tr>
                <SortHeader label="Nome" active={userSort.key === "name"} asc={userSort.asc} onClick={() => toggleUserSort("name")} />
                <SortHeader label="Role" active={userSort.key === "role"} asc={userSort.asc} onClick={() => toggleUserSort("role")} />
                <SortHeader label="Perguntas" active={userSort.key === "total_questions"} asc={userSort.asc} onClick={() => toggleUserSort("total_questions")} />
                <SortHeader label="Custo (R$)" active={userSort.key === "total_cost_brl"} asc={userSort.asc} onClick={() => toggleUserSort("total_cost_brl")} />
                <SortHeader label="Última atividade" active={userSort.key === "last_activity"} asc={userSort.asc} onClick={() => toggleUserSort("last_activity")} />
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {sortedUsers.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-sm text-muted">
                    Nenhum dado de uso disponível.
                  </td>
                </tr>
              )}
              {sortedUsers.map((u) => (
                <tr key={u.user_id} className="hover:bg-hover">
                  <td className="px-4 py-3 text-sm font-medium">{u.name}</td>
                  <td className="px-4 py-3"><RoleBadge role={u.role as Role} /></td>
                  <td className="px-4 py-3 text-sm">{u.total_questions}</td>
                  <td className="px-4 py-3 text-sm">{formatCurrency(u.total_cost_brl)}</td>
                  <td className="px-4 py-3 text-sm text-muted">
                    {u.last_activity ? new Date(u.last_activity).toLocaleDateString("pt-BR") : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Repository Usage Table */}
      <div className="rounded-lg border border-border bg-card-bg overflow-hidden">
        <div className="px-6 py-4 border-b border-border">
          <h2 className="text-lg font-semibold">Repositórios indexados</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="border-b border-border bg-hover">
              <tr>
                <SortHeader label="Repositório" active={repoSort.key === "name"} asc={repoSort.asc} onClick={() => toggleRepoSort("name")} />
                <SortHeader label="Chunks" active={repoSort.key === "chunks_count"} asc={repoSort.asc} onClick={() => toggleRepoSort("chunks_count")} />
                <SortHeader label="Última indexação" active={repoSort.key === "last_indexed"} asc={repoSort.asc} onClick={() => toggleRepoSort("last_indexed")} />
                <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase">Ação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {sortedRepos.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-sm text-muted">
                    Nenhum repositório indexado.
                  </td>
                </tr>
              )}
              {sortedRepos.map((r) => (
                <tr key={r.name} className="hover:bg-hover">
                  <td className="px-4 py-3 text-sm font-medium">{r.name}</td>
                  <td className="px-4 py-3 text-sm">{r.chunks_count}</td>
                  <td className="px-4 py-3 text-sm text-muted">
                    {r.last_indexed ? new Date(r.last_indexed).toLocaleDateString("pt-BR") : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => setDeleteRepoName(r.name)}
                      className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-lg text-danger hover:bg-danger-surface transition-colors"
                      title="Remover repositorio"
                    >
                      <Trash2 size={12} />
                      Remover
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Model Usage PieChart */}
      <div className="rounded-xl border border-border bg-card-bg p-6">
        <h2 className="text-lg font-semibold mb-4">Distribuição por modelo</h2>
        {modelUsage.length === 0 ? (
          <p className="text-sm text-muted">Nenhum dado de modelo disponível.</p>
        ) : (
          <div className="flex flex-col sm:flex-row items-center gap-8">
            <div className="h-64 w-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={modelUsage}
                    dataKey="questions"
                    nameKey="model"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    innerRadius={50}
                    strokeWidth={0}
                  >
                    {modelUsage.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--card-bg)",
                      border: "1px solid var(--border)",
                      borderRadius: "8px",
                      fontSize: "13px",
                      color: "var(--foreground)",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-3">
              {modelUsage.map((m, i) => (
                <div key={m.model} className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }} />
                  <span className="text-sm font-medium">{m.model}</span>
                  <span className="text-sm text-muted">{m.percentage}%</span>
                  <span className="text-xs text-muted">({m.questions} perguntas)</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
      {/* Delete Repo Confirmation Modal */}
      <Modal
        open={!!deleteRepoName}
        onClose={() => setDeleteRepoName(null)}
        title="Remover repositorio"
      >
        <p className="text-sm text-muted mb-4">
          Tem certeza que deseja remover <strong className="text-foreground">{deleteRepoName}</strong>?
          Todos os chunks, conversas e mensagens relacionadas serao apagados permanentemente.
        </p>
        <div className="flex justify-end gap-3">
          <button
            onClick={() => setDeleteRepoName(null)}
            className="px-4 py-2 text-sm rounded-lg border border-border hover:bg-hover transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={handleDeleteRepo}
            disabled={deleting}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-danger hover:bg-danger/80 text-white transition-colors disabled:opacity-50"
          >
            {deleting && <Loader2 size={14} className="animate-spin" />}
            Remover
          </button>
        </div>
      </Modal>
    </div>
  );
}
