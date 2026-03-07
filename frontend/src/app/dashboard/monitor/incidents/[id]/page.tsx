"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  AlertTriangle, Bot, Zap, MessageSquare, CheckCircle, Clock,
  ChevronDown, ChevronUp, Send, FileText, Share2, Copy, Check, Link2, ExternalLink,
} from "lucide-react";
import toast from "react-hot-toast";
import { useAuth } from "@/lib/hooks/useAuth";
import {
  getIncident, updateIncidentStatus, addTimelineEvent, updateHypothesis,
  getSimilarIncidents, createShareToken, revokeShareToken,
} from "@/lib/api";
import type { Incident, IncidentTimelineEvent, IncidentHypothesis, SimilarIncident } from "@/lib/types";
import { ExportPDFButton } from "@/components/ui/export-pdf-button";

const statusColors: Record<string, string> = {
  open: "bg-red-500",
  investigating: "bg-yellow-500",
  mitigated: "bg-blue-500",
  resolved: "bg-green-500",
};

const statusLabels: Record<string, string> = {
  open: "Aberto",
  investigating: "Investigando",
  mitigated: "Mitigado",
  resolved: "Resolvido",
};

const eventIcons: Record<string, typeof AlertTriangle> = {
  declared: AlertTriangle,
  hypothesis: Bot,
  action: Zap,
  comment: MessageSquare,
  update: FileText,
  mitigated: CheckCircle,
  resolved: CheckCircle,
  investigating: Clock,
};

function timeAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "agora";
  if (mins < 60) return `ha ${mins}min`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `ha ${hours}h`;
  return `ha ${Math.floor(hours / 24)}d`;
}

function elapsedTime(start: string) {
  const diff = Date.now() - new Date(start).getTime();
  const mins = Math.floor(diff / 60000);
  const hours = Math.floor(mins / 60);
  const remMins = mins % 60;
  if (hours > 0) return `${hours}h ${remMins}min`;
  return `${mins}min`;
}

export default function WarRoomPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const router = useRouter();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);
  const [elapsed, setElapsed] = useState("");

  // Timeline input
  const [eventContent, setEventContent] = useState("");
  const [eventType, setEventType] = useState("comment");
  const [sending, setSending] = useState(false);

  // Hypothesis expand
  const [expandedHyp, setExpandedHyp] = useState<string | null>(null);

  // Resolution modal
  const [showResolveModal, setShowResolveModal] = useState(false);
  const [resolutionSummary, setResolutionSummary] = useState("");

  // Similar incidents
  const [similarIncidents, setSimilarIncidents] = useState<SimilarIncident[]>([]);
  const [similarLoading, setSimilarLoading] = useState(true);

  // Share
  const [shareUrl, setShareUrl] = useState("");
  const [shareCopied, setShareCopied] = useState(false);
  const [sharing, setSharing] = useState(false);

  const loadIncident = useCallback(async () => {
    if (!id) return;
    try {
      const data = await getIncident(id);
      setIncident(data);
    } catch {
      /* */
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadIncident();
    const interval = setInterval(loadIncident, 10000);
    return () => clearInterval(interval);
  }, [loadIncident]);

  useEffect(() => {
    if (!id) return;
    getSimilarIncidents(id)
      .then((data) => setSimilarIncidents(data.similar || []))
      .catch(() => {})
      .finally(() => setSimilarLoading(false));
  }, [id]);

  // Elapsed timer
  useEffect(() => {
    if (!incident || incident.status === "resolved") return;
    const tick = () => setElapsed(elapsedTime(incident.declared_at));
    tick();
    const interval = setInterval(tick, 60000);
    return () => clearInterval(interval);
  }, [incident]);

  if (!user || !["admin", "dev"].includes(user.role)) {
    return <div className="p-8 text-muted">Acesso restrito.</div>;
  }
  if (loading) return <div className="p-8 text-muted">Carregando...</div>;
  if (!incident) return <div className="p-8 text-muted">Incidente nao encontrado.</div>;

  const timeline = incident.timeline || [];
  const hypotheses = incident.hypotheses || [];

  async function handleStatusChange(newStatus: string) {
    if (newStatus === "resolved") {
      setShowResolveModal(true);
      return;
    }
    try {
      await updateIncidentStatus(id, { status: newStatus });
      await loadIncident();
    } catch {
      /* */
    }
  }

  async function handleResolve() {
    try {
      await updateIncidentStatus(id, {
        status: "resolved",
        resolution_summary: resolutionSummary || undefined,
      });
      setShowResolveModal(false);
      await loadIncident();
    } catch {
      /* */
    }
  }

  async function handleAddEvent() {
    if (!eventContent.trim()) return;
    setSending(true);
    try {
      await addTimelineEvent(id, { content: eventContent, event_type: eventType });
      setEventContent("");
      await loadIncident();
    } catch {
      /* */
    } finally {
      setSending(false);
    }
  }

  async function handleHypothesisAction(hypId: string, status: "confirmed" | "discarded") {
    try {
      await updateHypothesis(id, hypId, { status });
      await loadIncident();
    } catch {
      /* */
    }
  }

  async function handleShare() {
    setSharing(true);
    try {
      const result = await createShareToken(id);
      setShareUrl(result.public_url);
      navigator.clipboard.writeText(result.public_url);
      setShareCopied(true);
      setTimeout(() => setShareCopied(false), 2000);
      toast.success("Link copiado!");
    } catch {
      toast.error("Erro ao gerar link");
    } finally {
      setSharing(false);
    }
  }

  async function handleRevokeShare() {
    try {
      await revokeShareToken(id);
      setShareUrl("");
      toast.success("Link revogado");
    } catch {
      toast.error("Erro ao revogar");
    }
  }

  const confirmedHyp = hypotheses.find((h) => h.status === "confirmed");

  return (
    <div className="h-[calc(100vh-3.5rem)] flex overflow-hidden">
      {/* Left: Control Panel */}
      <div className="w-[260px] shrink-0 border-r border-border p-5 overflow-y-auto space-y-5">
        <div>
          <p className="text-xs text-muted uppercase tracking-wider mb-2">Status</p>
          <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-white text-sm font-medium ${statusColors[incident.status]}`}>
            <span className="w-2 h-2 rounded-full bg-white/60 animate-pulse" />
            {statusLabels[incident.status]}
          </div>
        </div>

        {incident.status !== "resolved" && (
          <div className="space-y-2">
            <p className="text-xs text-muted uppercase tracking-wider">Acoes</p>
            {incident.status === "open" && (
              <button
                onClick={() => handleStatusChange("investigating")}
                className="w-full text-left px-3 py-2 rounded-lg text-sm bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300 hover:opacity-80"
              >
                Iniciar investigacao
              </button>
            )}
            {incident.status === "investigating" && (
              <>
                <button
                  onClick={() => handleStatusChange("mitigated")}
                  className="w-full text-left px-3 py-2 rounded-lg text-sm bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300 hover:opacity-80"
                >
                  Marcar como mitigado
                </button>
                <button
                  onClick={() => handleStatusChange("resolved")}
                  className="w-full text-left px-3 py-2 rounded-lg text-sm bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300 hover:opacity-80"
                >
                  Resolver incidente
                </button>
              </>
            )}
            {incident.status === "mitigated" && (
              <button
                onClick={() => handleStatusChange("resolved")}
                className="w-full text-left px-3 py-2 rounded-lg text-sm bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300 hover:opacity-80"
              >
                Resolver incidente
              </button>
            )}
          </div>
        )}

        <div className="space-y-3 text-sm">
          <div>
            <p className="text-xs text-muted">Tempo decorrido</p>
            <p className="font-mono font-medium">{incident.status === "resolved" ? "Resolvido" : elapsed}</p>
          </div>
          <div>
            <p className="text-xs text-muted">Projeto</p>
            <p className="font-medium">{incident.project_name}</p>
          </div>
          <div>
            <p className="text-xs text-muted">Severidade</p>
            <p className="font-medium uppercase">{incident.severity}</p>
          </div>
          <div>
            <p className="text-xs text-muted">Declarado por</p>
            <p>{incident.declared_by_name}</p>
          </div>
        </div>

        {incident.alert_id && (
          <Link
            href={`/dashboard/monitor/alerts`}
            className="text-sm text-accent-text hover:underline"
          >
            Ver alerta original
          </Link>
        )}
        {incident.postmortem && (
          <div className="space-y-2">
            <Link
              href={`/dashboard/monitor/incidents/${id}/postmortem`}
              className="flex items-center gap-2 text-sm text-accent-text hover:underline"
            >
              <FileText size={14} />
              Ver post-mortem
            </Link>
            <ExportPDFButton
              endpoint={`/api/incidents/${id}/postmortem/pdf`}
              filename={`postmortem-${id}.pdf`}
              label="Exportar PDF"
              size="sm"
            />
            <button
              onClick={handleShare}
              disabled={sharing}
              className="flex items-center gap-2 text-sm text-muted hover:text-foreground transition-colors"
            >
              <Share2 size={14} />
              {shareCopied ? "Link copiado!" : "Compartilhar post-mortem"}
            </button>
            {shareUrl && (
              <div className="space-y-1">
                <div className="flex items-center gap-1">
                  <Link2 size={10} className="text-muted shrink-0" />
                  <span className="text-[10px] text-muted font-mono truncate">{shareUrl}</span>
                </div>
                <button
                  onClick={handleRevokeShare}
                  className="text-[10px] text-danger hover:underline"
                >
                  Revogar link
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Center: Timeline */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="px-5 py-4 border-b border-border">
          <h1 className="text-lg font-bold truncate">{incident.title}</h1>
          {incident.description && (
            <p className="text-sm text-muted mt-1">{incident.description}</p>
          )}
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          {[...timeline].reverse().map((evt) => {
            const Icon = eventIcons[evt.event_type] || MessageSquare;
            return (
              <div key={evt.id} className="flex gap-3">
                <div className={`mt-0.5 p-1.5 rounded-lg shrink-0 ${
                  evt.is_ai_generated
                    ? "bg-purple-100 dark:bg-purple-900/30"
                    : "bg-hover"
                }`}>
                  <Icon size={14} className={evt.is_ai_generated ? "text-purple-600 dark:text-purple-400" : "text-muted"} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm">{evt.content}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-muted">
                      {evt.is_ai_generated ? "IA" : evt.author_name || "Sistema"}
                    </span>
                    <span className="text-xs text-muted">{timeAgo(evt.created_at)}</span>
                  </div>
                </div>
              </div>
            );
          })}
          {timeline.length === 0 && (
            <p className="text-sm text-muted text-center py-8">Nenhum evento na timeline.</p>
          )}
        </div>

        {/* Input */}
        {incident.status !== "resolved" && (
          <div className="border-t border-border px-5 py-3 flex gap-2">
            <select
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              className="text-sm border border-border rounded-lg px-2 py-1.5 bg-card shrink-0"
            >
              <option value="action">Acao tomada</option>
              <option value="comment">Comentario</option>
              <option value="update">Atualizacao</option>
            </select>
            <input
              type="text"
              value={eventContent}
              onChange={(e) => setEventContent(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAddEvent()}
              placeholder="Descreva o que foi feito ou observado..."
              className="flex-1 text-sm border border-border rounded-lg px-3 py-1.5 bg-card"
            />
            <button
              onClick={handleAddEvent}
              disabled={sending || !eventContent.trim()}
              className="px-3 py-1.5 rounded-lg bg-accent-surface text-accent-text text-sm font-medium disabled:opacity-40"
            >
              <Send size={16} />
            </button>
          </div>
        )}
      </div>

      {/* Right: Hypotheses + Similar */}
      <div className="w-[300px] shrink-0 border-l border-border overflow-y-auto p-5 space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted">
          Hipoteses da IA
        </h2>

        {hypotheses.length === 0 && (
          <div className="text-sm text-muted flex items-center gap-2">
            <div className="w-4 h-4 border-2 border-muted border-t-transparent rounded-full animate-spin" />
            Gerando hipoteses...
          </div>
        )}

        {hypotheses.map((hyp) => {
          const isExpanded = expandedHyp === hyp.id;
          const opacity = confirmedHyp && confirmedHyp.id !== hyp.id && hyp.status !== "confirmed"
            ? "opacity-40"
            : "";

          return (
            <div
              key={hyp.id}
              className={`rounded-xl border border-border p-4 space-y-3 transition-opacity ${opacity}`}
            >
              {/* Confidence bar */}
              <div className="flex items-center gap-2">
                <div className="flex-1 h-2 rounded-full bg-hover overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      hyp.confidence >= 0.7 ? "bg-red-500" :
                      hyp.confidence >= 0.4 ? "bg-yellow-500" : "bg-green-500"
                    }`}
                    style={{ width: `${Math.round(hyp.confidence * 100)}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-muted">{Math.round(hyp.confidence * 100)}%</span>
              </div>

              <p className="text-sm">{hyp.hypothesis}</p>

              {hyp.status !== "open" && (
                <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full ${
                  hyp.status === "confirmed"
                    ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                    : "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400"
                }`}>
                  {hyp.status === "confirmed" ? "Confirmada" : "Descartada"}
                </span>
              )}

              <button
                onClick={() => setExpandedHyp(isExpanded ? null : hyp.id)}
                className="flex items-center gap-1 text-xs text-muted hover:text-foreground"
              >
                {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                {isExpanded ? "Recolher" : "Ver raciocinio"}
              </button>

              {isExpanded && (
                <div className="text-xs text-muted bg-hover/50 rounded-lg p-3 space-y-2">
                  <p><strong>Raciocinio:</strong> {hyp.reasoning}</p>
                </div>
              )}

              {hyp.status === "open" && (
                <div className="flex gap-2">
                  <button
                    onClick={() => handleHypothesisAction(hyp.id, "confirmed")}
                    className="flex-1 text-xs px-2 py-1.5 rounded-lg bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 hover:opacity-80"
                  >
                    Confirmar causa
                  </button>
                  <button
                    onClick={() => handleHypothesisAction(hyp.id, "discarded")}
                    className="flex-1 text-xs px-2 py-1.5 rounded-lg bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400 hover:opacity-80"
                  >
                    Descartar
                  </button>
                </div>
              )}
            </div>
          );
        })}

        {/* Similar Incidents */}
        <div className="border-t border-border pt-4 mt-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted mb-3">
            Incidentes similares
          </h2>

          {similarLoading ? (
            <p className="text-xs text-muted">Buscando...</p>
          ) : similarIncidents.length === 0 ? (
            <p className="text-xs text-muted">Nenhum incidente similar encontrado.</p>
          ) : (
            <div className="space-y-2">
              {similarIncidents.map((sim) => (
                <Link
                  key={sim.similar_incident_id}
                  href={`/dashboard/monitor/incidents/${sim.similar_incident_id}`}
                  className="block p-3 rounded-lg border border-border hover:bg-hover transition-colors"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full uppercase ${
                      sim.severity === "critical" ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" :
                      sim.severity === "high" ? "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400" :
                      "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                    }`}>{sim.severity}</span>
                    <span className="text-[10px] text-muted font-mono">
                      {Math.round(sim.similarity_score * 100)}% similar
                    </span>
                  </div>
                  <p className="text-xs font-medium truncate">{sim.title}</p>
                  {sim.resolution_summary && (
                    <p className="text-[10px] text-muted mt-1 line-clamp-2">{sim.resolution_summary}</p>
                  )}
                  <div className="flex items-center gap-1 mt-1">
                    <span className="text-[10px] text-muted">{sim.project_name}</span>
                    <ExternalLink size={8} className="text-muted" />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Resolve modal */}
      {showResolveModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-card rounded-xl border border-border p-6 w-full max-w-md space-y-4">
            <h3 className="text-lg font-bold">Resolver incidente</h3>
            <div>
              <label className="text-sm text-muted block mb-1">Resumo da resolucao</label>
              <textarea
                value={resolutionSummary}
                onChange={(e) => setResolutionSummary(e.target.value)}
                rows={4}
                className="w-full text-sm border border-border rounded-lg px-3 py-2 bg-card"
                placeholder="O que foi feito para resolver..."
              />
            </div>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowResolveModal(false)}
                className="px-4 py-2 rounded-lg text-sm border border-border hover:bg-hover"
              >
                Cancelar
              </button>
              <button
                onClick={handleResolve}
                className="px-4 py-2 rounded-lg text-sm bg-green-600 text-white hover:bg-green-700"
              >
                Resolver
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
