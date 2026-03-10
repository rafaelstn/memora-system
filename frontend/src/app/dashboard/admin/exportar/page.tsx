"use client";

import { useState, useEffect, useCallback } from "react";
import {
  FileJson,
  FileSpreadsheet,
  Download,
  Loader2,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";
import toast from "react-hot-toast";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ExportRecord {
  id: string;
  format: "json" | "csv_zip";
  period_label: string;
  status: "pending" | "processing" | "ready" | "failed" | "expired";
  created_at: string;
  file_size?: number;
}

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-gray-100 text-gray-600 dark:bg-gray-500/15 dark:text-gray-400",
  processing: "bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300",
  ready: "bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-300",
  failed: "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300",
  expired: "bg-gray-50 text-gray-400 dark:bg-gray-500/10 dark:text-gray-500",
};

const STATUS_LABELS: Record<string, string> = {
  pending: "Aguardando",
  processing: "Processando",
  ready: "Pronto",
  failed: "Falhou",
  expired: "Expirado",
};

const PERIOD_OPTIONS = [
  { label: "Todos os dados", value: "" },
  { label: "Ultimos 30 dias", value: "30d" },
  { label: "Ultimos 90 dias", value: "90d" },
  { label: "Ultimos 12 meses", value: "12m" },
];

function getPeriodDates(value: string): { period_start?: string; period_end?: string } {
  if (!value) return {};
  const now = new Date();
  const end = now.toISOString();
  let start: Date;
  switch (value) {
    case "30d":
      start = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      break;
    case "90d":
      start = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
      break;
    case "12m":
      start = new Date(now);
      start.setFullYear(start.getFullYear() - 1);
      break;
    default:
      return {};
  }
  return { period_start: start.toISOString(), period_end: end };
}

function formatFileSize(bytes?: number): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  const { getAccessToken } = await import("@/lib/auth");
  const token = await getAccessToken();
  const headers: Record<string, string> = { "ngrok-skip-browser-warning": "true" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

async function apiFetchLocal<T>(path: string, options?: RequestInit): Promise<T> {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `API error: ${res.status}`);
  }
  return res.json();
}

async function downloadExportFile(exportId: string, format: string): Promise<void> {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/api/admin/exports/${exportId}/download`, {
    headers: authHeaders,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Erro ${res.status}`);
  }
  const blob = await res.blob();
  const ext = format === "json" ? "json" : "zip";
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `memora-export-${exportId.slice(0, 8)}.${ext}`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default function ExportarPage() {
  const [history, setHistory] = useState<ExportRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState<"json" | "csv_zip" | null>(null);
  const [period, setPeriod] = useState("");
  const [downloading, setDownloading] = useState<string | null>(null);

  const fetchHistory = useCallback(async () => {
    try {
      const data = await apiFetchLocal<ExportRecord[]>("/api/admin/exports");
      setHistory(data);
    } catch {
      // silently fail on poll
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  // Poll every 10s while any export is pending/processing
  useEffect(() => {
    const hasPending = history.some(
      (e) => e.status === "pending" || e.status === "processing",
    );
    if (!hasPending) return;

    const interval = setInterval(fetchHistory, 10_000);
    return () => clearInterval(interval);
  }, [history, fetchHistory]);

  async function handleExport(format: "json" | "csv_zip") {
    setExporting(format);
    try {
      const periodDates = getPeriodDates(period);
      const body: Record<string, string> = { format };
      if (periodDates.period_start) body.period_start = periodDates.period_start;
      if (periodDates.period_end) body.period_end = periodDates.period_end;

      await apiFetchLocal<ExportRecord>("/api/admin/exports", {
        method: "POST",
        body: JSON.stringify(body),
      });

      toast.success(
        format === "json"
          ? "Exportacao JSON iniciada"
          : "Exportacao CSV iniciada",
      );
      await fetchHistory();
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Erro ao iniciar exportacao",
      );
    } finally {
      setExporting(null);
    }
  }

  async function handleDownload(record: ExportRecord) {
    setDownloading(record.id);
    try {
      await downloadExportFile(record.id, record.format);
      toast.success("Download iniciado");
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Erro ao baixar arquivo",
      );
    } finally {
      setDownloading(null);
    }
  }

  return (
    <div className="p-5 lg:p-8 space-y-8">
      <div className="pt-2">
        <h1 className="text-xl font-semibold">Exportar dados da organizacao</h1>
      </div>

      {/* Warning */}
      <div className="flex items-start gap-3 rounded-xl border border-warning/30 bg-warning-surface p-4">
        <AlertTriangle size={18} className="text-warning shrink-0 mt-0.5" />
        <p className="text-sm text-foreground">
          A exportacao pode levar alguns minutos dependendo do volume de dados.
        </p>
      </div>

      {/* Period Selector */}
      <div>
        <label className="block text-sm font-medium mb-2">
          Periodo (opcional)
        </label>
        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          className="px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground max-w-xs w-full"
        >
          {PERIOD_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Export Buttons */}
      <div className="flex flex-col sm:flex-row gap-4">
        <button
          onClick={() => handleExport("json")}
          disabled={!!exporting}
          className="inline-flex items-center justify-center gap-3 px-6 py-4 text-sm font-medium rounded-xl border border-border bg-card-bg hover:bg-hover transition-colors disabled:opacity-50 flex-1"
        >
          {exporting === "json" ? (
            <Loader2 size={20} className="animate-spin text-accent" />
          ) : (
            <FileJson size={20} className="text-accent" />
          )}
          <div className="text-left">
            <p className="font-semibold">Exportar tudo em JSON</p>
            <p className="text-xs text-muted mt-0.5">
              Arquivo unico com todos os dados
            </p>
          </div>
        </button>

        <button
          onClick={() => handleExport("csv_zip")}
          disabled={!!exporting}
          className="inline-flex items-center justify-center gap-3 px-6 py-4 text-sm font-medium rounded-xl border border-border bg-card-bg hover:bg-hover transition-colors disabled:opacity-50 flex-1"
        >
          {exporting === "csv_zip" ? (
            <Loader2 size={20} className="animate-spin text-accent" />
          ) : (
            <FileSpreadsheet size={20} className="text-accent" />
          )}
          <div className="text-left">
            <p className="font-semibold">Exportar por tabela em CSV</p>
            <p className="text-xs text-muted mt-0.5">
              Arquivo ZIP com um CSV por tabela
            </p>
          </div>
        </button>
      </div>

      {/* Export History */}
      <div className="rounded-lg border border-border bg-card-bg overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-lg font-semibold">Historico de exportacoes</h2>
          <button
            onClick={fetchHistory}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg border border-border hover:bg-hover text-muted hover:text-foreground transition-colors"
          >
            <RefreshCw size={14} />
            Atualizar
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center gap-2 px-6 py-12 text-muted text-sm">
            <Loader2 size={16} className="animate-spin" />
            Carregando...
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-border bg-hover">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">
                    Data
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">
                    Formato
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">
                    Periodo
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">
                    Tamanho
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">
                    Acao
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {history.length === 0 && (
                  <tr>
                    <td
                      colSpan={6}
                      className="px-4 py-8 text-center text-sm text-muted"
                    >
                      Nenhuma exportacao realizada ainda.
                    </td>
                  </tr>
                )}
                {history.map((record) => (
                  <tr key={record.id} className="hover:bg-hover">
                    <td className="px-4 py-3 text-sm">
                      {new Date(record.created_at).toLocaleDateString("pt-BR", {
                        day: "2-digit",
                        month: "2-digit",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </td>
                    <td className="px-4 py-3 text-sm font-mono">
                      {record.format === "json" ? "JSON" : "CSV (ZIP)"}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted">
                      {record.period_label || "Todos os dados"}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted">
                      {formatFileSize(record.file_size)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          "px-2 py-0.5 rounded-full text-[11px] font-semibold",
                          STATUS_STYLES[record.status] || STATUS_STYLES.pending,
                        )}
                      >
                        {STATUS_LABELS[record.status] || record.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleDownload(record)}
                        disabled={
                          record.status !== "ready" ||
                          downloading === record.id
                        }
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                      >
                        {downloading === record.id ? (
                          <Loader2 size={12} className="animate-spin" />
                        ) : (
                          <Download size={12} />
                        )}
                        Baixar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
