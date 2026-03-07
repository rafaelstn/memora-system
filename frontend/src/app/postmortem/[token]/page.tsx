"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AlertTriangle, Copy, Check } from "lucide-react";
import { getPublicPostmortem } from "@/lib/api";
import type { PublicPostmortem } from "@/lib/types";
import ReactMarkdown from "react-markdown";

const severityColors: Record<string, string> = {
  low: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  medium: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  high: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  critical: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
};

export default function PublicPostmortemPage() {
  const { token } = useParams<{ token: string }>();
  const [data, setData] = useState<PublicPostmortem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!token) return;
    getPublicPostmortem(token)
      .then(setData)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-muted">Carregando post-mortem...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center space-y-3">
          <AlertTriangle size={32} className="text-muted mx-auto" />
          <p className="text-muted">Post-mortem nao encontrado ou link expirado.</p>
        </div>
      </div>
    );
  }

  function handleCopy() {
    if (!data?.postmortem) return;
    navigator.clipboard.writeText(data.postmortem);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b border-border bg-card">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-lg font-bold">Memora</span>
              <span className="text-xs text-muted px-2 py-0.5 rounded-full bg-hover">Post-mortem publico</span>
            </div>
            <button
              onClick={handleCopy}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border text-sm hover:bg-hover"
            >
              {copied ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
              {copied ? "Copiado!" : "Copiar markdown"}
            </button>
          </div>
        </div>
      </div>

      {/* Metadata */}
      <div className="max-w-4xl mx-auto px-6 py-6">
        <div className="flex flex-wrap items-center gap-3 mb-6">
          <h1 className="text-xl font-bold">{data.title}</h1>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full uppercase ${severityColors[data.severity] || "bg-gray-100 text-gray-600"}`}>
            {data.severity}
          </span>
        </div>

        <div className="flex flex-wrap gap-6 text-sm text-muted mb-8">
          <div>
            <span className="font-medium text-foreground">Projeto:</span> {data.project_name}
          </div>
          {data.declared_at && (
            <div>
              <span className="font-medium text-foreground">Declarado:</span>{" "}
              {new Date(data.declared_at).toLocaleString("pt-BR")}
            </div>
          )}
          {data.resolved_at && (
            <div>
              <span className="font-medium text-foreground">Resolvido:</span>{" "}
              {new Date(data.resolved_at).toLocaleString("pt-BR")}
            </div>
          )}
        </div>

        {/* Markdown content */}
        <div className="rounded-xl border border-border bg-card p-8 prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown>{data.postmortem}</ReactMarkdown>
        </div>

        {data.postmortem_generated_at && (
          <p className="text-xs text-muted text-center mt-6">
            Gerado automaticamente em {new Date(data.postmortem_generated_at).toLocaleString("pt-BR")} — Memora
          </p>
        )}
      </div>
    </div>
  );
}
