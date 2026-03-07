"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Copy, Check } from "lucide-react";
import { useAuth } from "@/lib/hooks/useAuth";
import { getIncident } from "@/lib/api";
import type { Incident } from "@/lib/types";
import ReactMarkdown from "react-markdown";

export default function PostmortemPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!id) return;
    getIncident(id)
      .then(setIncident)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  if (!user || !["admin", "dev"].includes(user.role)) {
    return <div className="p-8 text-muted">Acesso restrito.</div>;
  }
  if (loading) return <div className="p-8 text-muted">Carregando...</div>;
  if (!incident) return <div className="p-8 text-muted">Incidente nao encontrado.</div>;
  if (!incident.postmortem) {
    return (
      <div className="p-8 text-center">
        <p className="text-muted mb-4">Post-mortem ainda nao foi gerado.</p>
        <p className="text-sm text-muted">O post-mortem e gerado automaticamente quando o incidente e resolvido.</p>
        <Link href={`/dashboard/monitor/incidents/${id}`} className="text-sm text-accent-text hover:underline mt-4 inline-block">
          Voltar ao war room
        </Link>
      </div>
    );
  }

  function handleCopy() {
    if (!incident?.postmortem) return;
    navigator.clipboard.writeText(incident.postmortem);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <Link
          href={`/dashboard/monitor/incidents/${id}`}
          className="flex items-center gap-2 text-sm text-muted hover:text-foreground"
        >
          <ArrowLeft size={16} />
          Voltar ao war room
        </Link>
        <button
          onClick={handleCopy}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border text-sm hover:bg-hover"
        >
          {copied ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
          {copied ? "Copiado!" : "Copiar markdown"}
        </button>
      </div>

      <div className="rounded-xl border border-border bg-card p-8 prose prose-sm dark:prose-invert max-w-none">
        <ReactMarkdown>{incident.postmortem}</ReactMarkdown>
      </div>

      {incident.postmortem_generated_at && (
        <p className="text-xs text-muted text-center">
          Gerado automaticamente em {new Date(incident.postmortem_generated_at).toLocaleString("pt-BR")}
        </p>
      )}
    </div>
  );
}
