"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Brain,
  Search,
  GitPullRequest,
  GitCommit,
  AlertCircle,
  FileText,
  BookOpen,
  ExternalLink,
  RefreshCw,
  Loader2,
  Plus,
  Upload,
  X,
} from "lucide-react";
import toast from "react-hot-toast";
import { cn } from "@/lib/utils";
import {
  searchKnowledge,
  getKnowledgeStats,
  getKnowledgeEntry,
  syncKnowledgeRepo,
  listRepos,
} from "@/lib/api";
import type { KnowledgeSearchResult, KnowledgeStats, KnowledgeEntryDetail } from "@/lib/types";

const SOURCE_ICONS: Record<string, typeof GitPullRequest> = {
  pr: GitPullRequest,
  commit: GitCommit,
  issue: AlertCircle,
  document: FileText,
  adr: BookOpen,
};

const SOURCE_LABELS: Record<string, string> = {
  pr: "Pull Request",
  commit: "Commit",
  issue: "Issue",
  document: "Documento",
  adr: "ADR",
  code: "Codigo",
  discussion: "Discussao",
};

function timeAgo(dateStr: string | null | undefined): string {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "agora";
  if (mins < 60) return `ha ${mins}min`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `ha ${hours}h`;
  const days = Math.floor(hours / 24);
  return `ha ${days}d`;
}

export default function MemoryPage() {
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<KnowledgeSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState<KnowledgeEntryDetail | null>(null);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [repos, setRepos] = useState<{ name: string }[]>([]);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(null);

  useEffect(() => {
    getKnowledgeStats().then(setStats).catch(() => {});
    listRepos().then(setRepos).catch(() => {});
  }, []);

  const doSearch = useCallback(async (q: string) => {
    if (q.length < 2) {
      setResults([]);
      return;
    }
    setSearching(true);
    try {
      const data = await searchKnowledge({ q });
      setResults(data);
    } catch (e: unknown) {
      console.error("Erro ao buscar conhecimento:", e);
    } finally {
      setSearching(false);
    }
  }, []);

  function handleQueryChange(value: string) {
    setQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(value), 500);
  }

  async function openEntry(id: string) {
    setDrawerLoading(true);
    try {
      const entry = await getKnowledgeEntry(id);
      setSelectedEntry(entry);
    } catch {
      toast.error("Erro ao carregar entrada");
    } finally {
      setDrawerLoading(false);
    }
  }

  async function handleSync() {
    if (repos.length === 0) {
      toast.error("Nenhum repositorio indexado");
      return;
    }
    setSyncing(true);
    try {
      for (const repo of repos) {
        await syncKnowledgeRepo(repo.name);
      }
      toast.success("Sincronizacao iniciada");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao sincronizar");
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* Main content */}
      <div className={cn("flex-1 p-5 lg:p-8 space-y-6 overflow-y-auto", selectedEntry && "lg:mr-[420px]")}>
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Brain size={24} className="text-accent" />
            <h1 className="text-xl font-semibold">Memoria Tecnica</h1>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleSync}
              disabled={syncing}
              className="inline-flex items-center gap-2 px-3 py-2 text-sm rounded-lg border border-border hover:bg-hover transition-colors disabled:opacity-50"
            >
              {syncing ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
              Sincronizar GitHub
            </button>
          </div>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {[
              { label: "Total", value: stats.total_entries },
              { label: "PRs/Commits", value: stats.prs_commits },
              { label: "Issues", value: stats.issues },
              { label: "Documentos", value: stats.documents },
              { label: "ADRs", value: stats.adrs },
              { label: "Wikis", value: stats.wikis },
            ].map((s) => (
              <div key={s.label} className="rounded-lg border border-border bg-card-bg p-3 text-center">
                <p className="text-lg font-bold">{s.value}</p>
                <p className="text-xs text-muted">{s.label}</p>
              </div>
            ))}
          </div>
        )}

        {/* Search bar */}
        <div className="relative">
          <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-muted" />
          <input
            type="text"
            value={query}
            onChange={(e) => handleQueryChange(e.target.value)}
            placeholder="O que voce quer saber? Ex: Por que usamos pgvector?"
            className="w-full pl-11 pr-4 py-3.5 text-sm rounded-xl border border-border bg-card-bg text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
          {searching && <Loader2 size={16} className="absolute right-4 top-1/2 -translate-y-1/2 text-muted animate-spin" />}
        </div>

        {/* Results */}
        {results.length > 0 && (
          <div className="space-y-2">
            {results.map((r) => {
              const Icon = SOURCE_ICONS[r.source_type] || FileText;
              return (
                <button
                  key={r.id}
                  onClick={() => openEntry(r.id)}
                  className="w-full text-left flex items-start gap-3 px-4 py-3 rounded-lg border border-border bg-card-bg hover:bg-hover transition-colors"
                >
                  <Icon size={16} className="text-accent mt-0.5 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{r.title}</p>
                    <p className="text-xs text-muted mt-0.5 line-clamp-2">{r.summary}</p>
                    <div className="flex items-center gap-3 mt-1.5">
                      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-accent-surface text-accent-text">
                        {SOURCE_LABELS[r.source_type] || r.source_type}
                      </span>
                      {r.decision_type && (
                        <span className="text-[10px] text-muted">{r.decision_type}</span>
                      )}
                      {r.source_date && (
                        <span className="text-[10px] text-muted">{new Date(r.source_date).toLocaleDateString("pt-BR")}</span>
                      )}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}

        {query.length >= 2 && !searching && results.length === 0 && (
          <p className="text-sm text-muted text-center py-8">Nenhum resultado encontrado.</p>
        )}
      </div>

      {/* Detail Drawer */}
      {selectedEntry && (
        <div className="fixed right-0 top-0 h-full w-[420px] border-l border-border bg-card-bg shadow-lg z-30 flex flex-col overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-border">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium px-2 py-0.5 rounded bg-accent-surface text-accent-text">
                {SOURCE_LABELS[selectedEntry.source_type] || selectedEntry.source_type}
              </span>
              {selectedEntry.decision_type && (
                <span className="text-xs text-muted">{selectedEntry.decision_type}</span>
              )}
            </div>
            <button onClick={() => setSelectedEntry(null)} className="p-1 rounded hover:bg-hover">
              <X size={16} />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {drawerLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 size={20} className="animate-spin text-muted" />
              </div>
            ) : (
              <>
                <h2 className="text-lg font-semibold">{selectedEntry.title}</h2>

                {selectedEntry.source_date && (
                  <p className="text-xs text-muted">
                    {new Date(selectedEntry.source_date).toLocaleDateString("pt-BR", {
                      day: "2-digit", month: "long", year: "numeric",
                    })}
                  </p>
                )}

                {selectedEntry.source_url && (
                  <a
                    href={selectedEntry.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-accent hover:underline"
                  >
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

                {selectedEntry.file_paths && selectedEntry.file_paths.length > 0 && (
                  <div>
                    <h3 className="text-xs font-semibold text-muted mb-1">Arquivos relacionados</h3>
                    <div className="flex flex-wrap gap-1">
                      {selectedEntry.file_paths.map((fp) => (
                        <span key={fp} className="text-xs font-mono px-1.5 py-0.5 rounded bg-hover">
                          {fp}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {selectedEntry.components && selectedEntry.components.length > 0 && (
                  <div>
                    <h3 className="text-xs font-semibold text-muted mb-1">Componentes</h3>
                    <div className="flex flex-wrap gap-1">
                      {selectedEntry.components.map((c) => (
                        <span key={c} className="text-xs px-1.5 py-0.5 rounded bg-accent-surface text-accent-text">
                          {c}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
