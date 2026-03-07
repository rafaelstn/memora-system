"use client";

import { useState, useEffect } from "react";
import {
  Clock,
  GitPullRequest,
  GitCommit,
  AlertCircle,
  FileText,
  BookOpen,
  ExternalLink,
  Loader2,
  X,
} from "lucide-react";
import toast from "react-hot-toast";
import { cn } from "@/lib/utils";
import { getKnowledgeTimeline, getKnowledgeEntry, listRepos } from "@/lib/api";
import type { KnowledgeEntry, KnowledgeEntryDetail } from "@/lib/types";

const SOURCE_ICONS: Record<string, typeof GitPullRequest> = {
  pr: GitPullRequest,
  commit: GitCommit,
  issue: AlertCircle,
  document: FileText,
  adr: BookOpen,
};

const SOURCE_LABELS: Record<string, string> = {
  pr: "PR",
  commit: "Commit",
  issue: "Issue",
  document: "Doc",
  adr: "ADR",
};

function groupByMonth(entries: KnowledgeEntry[]): Record<string, KnowledgeEntry[]> {
  const groups: Record<string, KnowledgeEntry[]> = {};
  for (const entry of entries) {
    const date = entry.source_date || entry.created_at;
    const d = new Date(date);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    const label = d.toLocaleDateString("pt-BR", { month: "long", year: "numeric" });
    if (!groups[label]) groups[label] = [];
    groups[label].push(entry);
  }
  return groups;
}

export default function TimelinePage() {
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [repos, setRepos] = useState<{ name: string }[]>([]);
  const [repoFilter, setRepoFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [period, setPeriod] = useState("90d");
  const [fileFilter, setFileFilter] = useState("");
  const [selectedEntry, setSelectedEntry] = useState<KnowledgeEntryDetail | null>(null);

  useEffect(() => {
    listRepos().then(setRepos).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    getKnowledgeTimeline({
      repo_id: repoFilter || undefined,
      source_type: typeFilter || undefined,
      period,
      file_path: fileFilter || undefined,
    })
      .then(setEntries)
      .catch(() => toast.error("Erro ao carregar timeline"))
      .finally(() => setLoading(false));
  }, [repoFilter, typeFilter, period, fileFilter]);

  async function openEntry(id: string) {
    try {
      const entry = await getKnowledgeEntry(id);
      setSelectedEntry(entry);
    } catch {
      toast.error("Erro ao carregar");
    }
  }

  const grouped = groupByMonth(entries);

  return (
    <div className="flex flex-1 overflow-hidden">
      <div className={cn("flex-1 p-5 lg:p-8 space-y-6 overflow-y-auto", selectedEntry && "lg:mr-[420px]")}>
        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-3 py-2 text-sm rounded-lg border border-border bg-card-bg"
          >
            <option value="">Todos os tipos</option>
            <option value="pr">PRs</option>
            <option value="commit">Commits</option>
            <option value="issue">Issues</option>
            <option value="adr">ADRs</option>
            <option value="document">Documentos</option>
          </select>

          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="px-3 py-2 text-sm rounded-lg border border-border bg-card-bg"
          >
            <option value="30d">Ultimos 30 dias</option>
            <option value="90d">Ultimos 90 dias</option>
            <option value="1y">Ultimo ano</option>
            <option value="all">Tudo</option>
          </select>

          <input
            type="text"
            value={fileFilter}
            onChange={(e) => setFileFilter(e.target.value)}
            placeholder="Filtrar por arquivo..."
            className="px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground placeholder:text-muted w-48"
          />
        </div>

        {/* Timeline */}
        {loading ? (
          <div className="flex items-center justify-center gap-2 py-12 text-muted text-sm">
            <Loader2 size={16} className="animate-spin" /> Carregando...
          </div>
        ) : entries.length === 0 ? (
          <p className="text-sm text-muted text-center py-12">Nenhuma entrada encontrada.</p>
        ) : (
          <div className="space-y-8">
            {Object.entries(grouped).map(([month, items]) => (
              <div key={month}>
                <h3 className="text-sm font-semibold text-muted mb-3 capitalize">{month}</h3>
                <div className="relative border-l-2 border-border ml-3 space-y-0">
                  {items.map((entry) => {
                    const Icon = SOURCE_ICONS[entry.source_type] || FileText;
                    const date = entry.source_date || entry.created_at;
                    return (
                      <button
                        key={entry.id}
                        onClick={() => openEntry(entry.id)}
                        className="relative w-full text-left flex items-start gap-3 pl-6 pr-4 py-3 hover:bg-hover rounded-r-lg transition-colors"
                      >
                        <div className="absolute -left-[9px] top-4 w-4 h-4 rounded-full bg-card-bg border-2 border-accent flex items-center justify-center">
                          <Icon size={8} className="text-accent" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-accent-surface text-accent-text">
                              {SOURCE_LABELS[entry.source_type] || entry.source_type}
                            </span>
                            {entry.decision_type && (
                              <span className="text-[10px] text-muted">{entry.decision_type}</span>
                            )}
                            <span className="text-[10px] text-muted ml-auto">
                              {new Date(date).toLocaleDateString("pt-BR")}
                            </span>
                          </div>
                          <p className="text-sm font-medium mt-1">{entry.title}</p>
                          {entry.summary && (
                            <p className="text-xs text-muted mt-0.5 line-clamp-2">{entry.summary}</p>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Detail Drawer */}
      {selectedEntry && (
        <div className="fixed right-0 top-0 h-full w-[420px] border-l border-border bg-card-bg shadow-lg z-30 flex flex-col overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-border">
            <span className="text-xs font-medium px-2 py-0.5 rounded bg-accent-surface text-accent-text">
              {SOURCE_LABELS[selectedEntry.source_type] || selectedEntry.source_type}
            </span>
            <button onClick={() => setSelectedEntry(null)} className="p-1 rounded hover:bg-hover">
              <X size={16} />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            <h2 className="text-lg font-semibold">{selectedEntry.title}</h2>
            {selectedEntry.source_url && (
              <a href={selectedEntry.source_url} target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-accent hover:underline">
                Ver no GitHub <ExternalLink size={12} />
              </a>
            )}
            {selectedEntry.summary && (
              <div>
                <h3 className="text-xs font-semibold text-muted mb-1">Resumo</h3>
                <p className="text-sm whitespace-pre-wrap">{selectedEntry.summary}</p>
              </div>
            )}
            {selectedEntry.content && (
              <div>
                <h3 className="text-xs font-semibold text-muted mb-1">Conteudo</h3>
                <div className="text-sm whitespace-pre-wrap bg-hover rounded-lg p-3 max-h-80 overflow-y-auto font-mono text-xs">
                  {selectedEntry.content}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
