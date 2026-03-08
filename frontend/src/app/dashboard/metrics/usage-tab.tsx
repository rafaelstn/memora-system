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
} from "lucide-react";
import { cn, formatCurrency } from "@/lib/utils";
import { RoleBadge } from "@/components/ui/badge";
import { getMetrics, getDailyUsage, getUserUsage, getModelUsage } from "@/lib/api";
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

type UserSortKey = keyof Pick<UserUsage, "name" | "role" | "total_questions" | "total_cost_brl" | "last_activity">;

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

export default function UsageTab() {
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [dailyUsage, setDailyUsage] = useState<DailyUsage[]>([]);
  const [userUsage, setUserUsage] = useState<UserUsage[]>([]);
  const [modelUsage, setModelUsage] = useState<ModelUsage[]>([]);
  const [loading, setLoading] = useState(true);
  const [userSort, setUserSort] = useState<{ key: UserSortKey; asc: boolean }>({ key: "total_questions", asc: false });

  useEffect(() => {
    Promise.all([getMetrics(), getDailyUsage(), getUserUsage(), getModelUsage()])
      .then(([m, d, u, mo]) => { setMetrics(m); setDailyUsage(d); setUserUsage(u); setModelUsage(mo); })
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

  function toggleUserSort(key: UserSortKey) {
    setUserSort((prev) => ({ key, asc: prev.key === key ? !prev.asc : false }));
  }

  function exportCSV() {
    const header = "Nome,Role,Perguntas,Custo (R$),Ultima Atividade\n";
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

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-20 text-muted text-sm">
        <Loader2 size={16} className="animate-spin" />
        Carregando metricas...
      </div>
    );
  }

  const summaryCards = [
    { icon: MessageSquare, label: "Total de perguntas", value: (metrics?.total_questions ?? 0).toLocaleString("pt-BR"), sub: "Todas as conversas" },
    { icon: DollarSign, label: "Custo total", value: formatCurrency(metrics?.total_cost_brl ?? 0), sub: "Acumulado" },
    { icon: TrendingUp, label: "Custo medio/pergunta", value: formatCurrency(metrics?.avg_cost_per_question_brl ?? 0), sub: "Media geral" },
    { icon: Users, label: "Usuarios ativos (7d)", value: (metrics?.active_users_7d ?? 0).toString(), sub: "Ultimos 7 dias" },
  ];

  return (
    <div className="space-y-8">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {summaryCards.map((card) => (
          <div key={card.label} className="rounded-xl border border-border bg-card-bg p-6">
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
        <h2 className="text-lg font-semibold mb-4">Uso diario — ultimos 30 dias</h2>
        <div className="h-80">
          {dailyUsage.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted text-sm">
              Nenhum dado de uso disponivel ainda.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={dailyUsage}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--muted)" }} tickFormatter={(v: string) => v.slice(5)} />
                <YAxis yAxisId="left" tick={{ fontSize: 11, fill: "var(--muted)" }} />
                <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: "var(--muted)" }} />
                <Tooltip
                  contentStyle={{ backgroundColor: "var(--card-bg)", border: "1px solid var(--border)", borderRadius: "10px", fontSize: "13px", color: "var(--foreground)" }}
                  /* eslint-disable @typescript-eslint/no-explicit-any */
                  formatter={((value: any, name: any) => {
                    const v = Number(value) || 0;
                    if (name === "cost_brl") return [formatCurrency(v), "Custo (R$)"];
                    return [v, "Perguntas"];
                  }) as any}
                  labelFormatter={((label: any) => `Data: ${label}`) as any}
                />
                <Legend formatter={((value: any) => (value === "questions" ? "Perguntas" : "Custo (R$)")) as any} />
                {/* eslint-enable @typescript-eslint/no-explicit-any */}
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
          <h2 className="text-lg font-semibold">Uso por usuario</h2>
          <button onClick={exportCSV} className="inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg border border-border hover:bg-hover text-muted hover:text-foreground transition-colors">
            <Download size={14} />
            Exportar CSV
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="border-b border-border bg-hover">
              <tr>
                <SortHeader label="Nome" active={userSort.key === "name"} onClick={() => toggleUserSort("name")} />
                <SortHeader label="Role" active={userSort.key === "role"} onClick={() => toggleUserSort("role")} />
                <SortHeader label="Perguntas" active={userSort.key === "total_questions"} onClick={() => toggleUserSort("total_questions")} />
                <SortHeader label="Custo (R$)" active={userSort.key === "total_cost_brl"} onClick={() => toggleUserSort("total_cost_brl")} />
                <SortHeader label="Ultima atividade" active={userSort.key === "last_activity"} onClick={() => toggleUserSort("last_activity")} />
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {sortedUsers.length === 0 && (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-sm text-muted">Nenhum dado de uso disponivel.</td></tr>
              )}
              {sortedUsers.map((u) => (
                <tr key={u.user_id} className="hover:bg-hover">
                  <td className="px-4 py-3 text-sm font-medium">{u.name}</td>
                  <td className="px-4 py-3"><RoleBadge role={u.role as Role} /></td>
                  <td className="px-4 py-3 text-sm">{u.total_questions}</td>
                  <td className="px-4 py-3 text-sm">{formatCurrency(u.total_cost_brl)}</td>
                  <td className="px-4 py-3 text-sm text-muted">{u.last_activity ? new Date(u.last_activity).toLocaleDateString("pt-BR") : "\u2014"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Model Usage PieChart */}
      <div className="rounded-xl border border-border bg-card-bg p-6">
        <h2 className="text-lg font-semibold mb-4">Distribuicao por modelo</h2>
        {modelUsage.length === 0 ? (
          <p className="text-sm text-muted">Nenhum dado de modelo disponivel.</p>
        ) : (
          <div className="flex flex-col sm:flex-row items-center gap-8">
            <div className="h-64 w-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={modelUsage} dataKey="questions" nameKey="model" cx="50%" cy="50%" outerRadius={100} innerRadius={50} strokeWidth={0}>
                    {modelUsage.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: "var(--card-bg)", border: "1px solid var(--border)", borderRadius: "8px", fontSize: "13px", color: "var(--foreground)" }} />
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
    </div>
  );
}
