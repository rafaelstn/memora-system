"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Database,
  Brain,
  Mail,
  Globe,
  Zap,
  Loader2,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  HardDrive,
  Cpu,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { getHealthAdmin } from "@/lib/api";
import type { HealthAdminResponse, HealthLLMProvider } from "@/lib/api";

function statusIcon(status: string) {
  if (status === "ok") return <CheckCircle2 size={18} className="text-green-500" />;
  if (status === "degraded" || status === "not_configured") return <AlertTriangle size={18} className="text-yellow-500" />;
  return <XCircle size={18} className="text-red-500" />;
}

function statusBorder(status: string) {
  if (status === "ok") return "border-green-500/20";
  if (status === "degraded" || status === "not_configured") return "border-yellow-500/20";
  if (status === "down" || status === "error") return "border-red-500/20";
  return "border-border";
}

function statusBg(status: string) {
  if (status === "ok") return "bg-green-500/5";
  if (status === "degraded" || status === "not_configured") return "bg-yellow-500/5";
  if (status === "down" || status === "error") return "bg-red-500/5";
  return "bg-card-bg";
}

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "Nunca";
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "Agora";
  if (diffMin < 60) return `ha ${diffMin} min`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `ha ${diffH}h`;
  const diffD = Math.floor(diffH / 24);
  return `ha ${diffD} dia${diffD > 1 ? "s" : ""}`;
}

export default function SystemTab() {
  const [data, setData] = useState<HealthAdminResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastCheck, setLastCheck] = useState<Date | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchHealth = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true);
    else setLoading(true);
    try {
      const res = await getHealthAdmin();
      setData(res);
      setLastCheck(new Date());
    } catch {
      // keep old data
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(() => fetchHealth(true), 60000);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 size={24} className="animate-spin text-muted" />
      </div>
    );
  }

  if (!data) return null;

  // Overall status
  const criticalDown =
    data.database.status === "down" || data.embeddings.status === "down";
  const anyDown =
    criticalDown ||
    data.email.status === "error" ||
    data.github_webhook.status === "error" ||
    data.background_workers.status === "down" ||
    data.llm_providers.some((p) => p.status === "down");
  const anyDegraded =
    data.database.status === "degraded" ||
    data.embeddings.status === "degraded" ||
    data.email.status === "not_configured" ||
    data.github_webhook.status === "not_configured" ||
    data.background_workers.status === "degraded" ||
    data.llm_providers.some((p) => p.status === "degraded");

  const overallStatus = criticalDown
    ? "down"
    : anyDown
      ? "down"
      : anyDegraded
        ? "degraded"
        : "ok";

  const overallMessage = overallStatus === "ok"
    ? "Todos os sistemas operacionais"
    : overallStatus === "degraded"
      ? "Atencao — servicos precisam de configuracao"
      : "Problema — servicos fora do ar";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">Status do Sistema</h2>
          <p className="text-sm text-muted">
            Ultima verificacao: {lastCheck ? timeAgo(lastCheck.toISOString()) : "—"}
          </p>
        </div>
        <button
          onClick={() => fetchHealth(true)}
          disabled={refreshing}
          className="inline-flex items-center gap-2 px-3 py-2 text-sm border border-border rounded-lg hover:bg-muted/10 transition-colors disabled:opacity-50"
        >
          <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />
          Verificar agora
        </button>
      </div>

      {/* Overall status banner */}
      <div className={cn(
        "rounded-xl border p-5 flex items-center gap-3",
        statusBorder(overallStatus),
        statusBg(overallStatus),
      )}>
        {statusIcon(overallStatus)}
        <span className="font-medium">{overallMessage}</span>
      </div>

      {/* Grid of cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Database */}
        <div className={cn("rounded-xl border p-6 space-y-2", statusBorder(data.database.status), statusBg(data.database.status))}>
          <div className="flex items-center gap-2">
            {statusIcon(data.database.status)}
            <span className="font-semibold">Banco de Dados</span>
          </div>
          <p className="text-sm text-muted">{data.database.detail}</p>
          {data.database.latency_ms !== undefined && (
            <p className="text-sm text-muted">Latencia: {data.database.latency_ms}ms</p>
          )}
        </div>

        {/* Embeddings */}
        <div className={cn("rounded-xl border p-6 space-y-2", statusBorder(data.embeddings.status), statusBg(data.embeddings.status))}>
          <div className="flex items-center gap-2">
            {statusIcon(data.embeddings.status)}
            <span className="font-semibold">Embeddings</span>
          </div>
          <p className="text-sm text-muted">{data.embeddings.detail}</p>
          {data.embeddings.latency_ms !== undefined && (
            <p className="text-sm text-muted">Latencia: {data.embeddings.latency_ms}ms</p>
          )}
        </div>

        {/* LLM Providers */}
        {data.llm_providers.map((p: HealthLLMProvider, i: number) => (
          <div key={i} className={cn("rounded-xl border p-6 space-y-2", statusBorder(p.status), statusBg(p.status))}>
            <div className="flex items-center gap-2">
              {statusIcon(p.status)}
              <span className="font-semibold">
                IA — {p.name} {p.is_default ? "(padrao)" : ""}
              </span>
            </div>
            <p className="text-sm text-muted">Latencia: {p.latency_ms}ms</p>
          </div>
        ))}
        {data.llm_providers.length === 0 && (
          <div className={cn("rounded-xl border p-6 space-y-2", statusBorder("not_configured"), statusBg("not_configured"))}>
            <div className="flex items-center gap-2">
              {statusIcon("not_configured")}
              <span className="font-semibold">IA — Nenhum provedor</span>
            </div>
            <p className="text-sm text-muted">Configure um provedor em Configuracoes</p>
          </div>
        )}

        {/* GitHub Webhook */}
        <div className={cn("rounded-xl border p-6 space-y-2", statusBorder(data.github_webhook.status), statusBg(data.github_webhook.status))}>
          <div className="flex items-center gap-2">
            {statusIcon(data.github_webhook.status)}
            <span className="font-semibold">GitHub Webhook</span>
          </div>
          <p className="text-sm text-muted">{data.github_webhook.detail}</p>
          {data.github_webhook.last_received_at && (
            <p className="text-sm text-muted">
              Ultimo recebido: {timeAgo(data.github_webhook.last_received_at)}
            </p>
          )}
        </div>

        {/* Background Workers */}
        <div className={cn("rounded-xl border p-6 space-y-2", statusBorder(data.background_workers.status), statusBg(data.background_workers.status))}>
          <div className="flex items-center gap-2">
            {statusIcon(data.background_workers.status)}
            <span className="font-semibold">Workers em Background</span>
          </div>
          <p className="text-sm text-muted">
            {data.background_workers.active_jobs} jobs ativos — {data.background_workers.failed_jobs_last_hour} falhas na ultima hora
          </p>
        </div>

        {/* Email */}
        <div className={cn("rounded-xl border p-6 space-y-2", statusBorder(data.email.status), statusBg(data.email.status))}>
          <div className="flex items-center gap-2">
            {statusIcon(data.email.status)}
            <span className="font-semibold">Email</span>
          </div>
          <p className="text-sm text-muted">
            {data.email.status === "ok"
              ? `${data.email.provider} configurado`
              : data.email.status === "not_configured"
                ? "Nao configurado"
                : "Erro na configuracao"}
          </p>
        </div>

        {/* Storage */}
        <div className={cn("rounded-xl border p-6 space-y-2", statusBorder("ok"), statusBg("ok"))}>
          <div className="flex items-center gap-2">
            <HardDrive size={18} className="text-accent" />
            <span className="font-semibold">Repositorios</span>
          </div>
          <p className="text-sm text-muted">
            {data.storage.repos_indexed} repos indexados
          </p>
          <p className="text-sm text-muted">
            {data.storage.chunks_total.toLocaleString()} chunks armazenados
          </p>
          {data.storage.last_indexed_at && (
            <p className="text-sm text-muted">
              Ultima indexacao: {timeAgo(data.storage.last_indexed_at)}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
