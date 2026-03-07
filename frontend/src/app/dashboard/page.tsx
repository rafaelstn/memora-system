"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Database,
  FolderGit2,
  Github,
  AlertTriangle,
  Settings,
  Loader2,
  Lock,
  Globe,
  Download,
  Search,
  Star,
  StarOff,
  MessageSquare,
  RefreshCw,
  BookOpen,
} from "lucide-react";
import toast from "react-hot-toast";
import { StatusBadge } from "@/components/ui/badge";
import { useAuth } from "@/lib/hooks/useAuth";
import { useChatContext } from "@/lib/chat-context";
import { getGitHubStatus, listRepos, listGitHubRepos, ingestRepositoryStream } from "@/lib/api";
import { ChatPanel } from "@/components/chat/chat-panel";
import { cn } from "@/lib/utils";

interface RepoInfo {
  name: string;
  chunks_count: number;
  last_indexed?: string;
  status: string;
}

interface GitHubRepo {
  name: string;
  full_name: string;
  private: boolean;
  url: string;
  language: string | null;
  updated_at: string | null;
  default_branch: string;
}

export default function DashboardPage() {
  const { user, role } = useAuth();
  const chat = useChatContext();
  const activeRepo = chat.dashboardActiveRepo;
  const setActiveRepo = chat.setDashboardActiveRepo;
  const [ghConnected, setGhConnected] = useState<boolean | null>(null);
  const [repos, setRepos] = useState<RepoInfo[]>([]);
  const [ghRepos, setGhRepos] = useState<GitHubRepo[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingGh, setLoadingGh] = useState(false);
  const [indexingRepo, setIndexingRepo] = useState<string | null>(null);
  const [indexProgress, setIndexProgress] = useState<{ percent: number; detail: string } | null>(null);
  const [tab, setTab] = useState<"indexed" | "available">("indexed");
  const [search, setSearch] = useState("");
  const [favorites, setFavorites] = useState<Set<string>>(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("memora_favorites");
      return saved ? new Set(JSON.parse(saved)) : new Set();
    }
    return new Set();
  });
  const [sidebarWidth, setSidebarWidth] = useState(340);
  const [isResizing, setIsResizing] = useState(false);
  const canManage = role === "admin" || role === "dev";

  // Resize handler
  function handleMouseDown() {
    setIsResizing(true);
    const handleMouseMove = (e: MouseEvent) => {
      // Account for dashboard sidebar (w-64 = 256px)
      const newWidth = e.clientX - 256;
      setSidebarWidth(Math.max(260, Math.min(600, newWidth)));
    };
    const handleMouseUp = () => {
      setIsResizing(false);
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }

  // Persist favorites
  useEffect(() => {
    localStorage.setItem("memora_favorites", JSON.stringify([...favorites]));
  }, [favorites]);

  useEffect(() => {
    if (!user) return;
    getGitHubStatus()
      .then((data) => setGhConnected(data.connected))
      .catch(() => setGhConnected(false));
  }, [user]);

  useEffect(() => {
    if (!user) return;
    listRepos()
      .then(setRepos)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user]);

  function loadGhRepos() {
    setLoadingGh(true);
    listGitHubRepos()
      .then(setGhRepos)
      .catch((err) => toast.error(err.message))
      .finally(() => setLoadingGh(false));
  }

  // Load GH repos for count (and when tab switches)
  useEffect(() => {
    if (ghConnected && ghRepos.length === 0) {
      loadGhRepos();
    }
  }, [ghConnected]);

  async function handleIndex(repo: GitHubRepo) {
    if (indexingRepo) return;
    setIndexingRepo(repo.full_name);
    setIndexProgress({ percent: 0, detail: "Iniciando..." });

    await ingestRepositoryStream(
      repo.url,
      repo.name,
      (_stage, percent, detail) => {
        setIndexProgress({ percent, detail });
      },
      async (result) => {
        setIndexProgress(null);
        setIndexingRepo(null);
        if (result.chunks_created === 0) {
          toast.error(`${repo.name}: nenhum chunk criado (${result.files_processed} arquivos)`);
        } else {
          toast.success(`${repo.name}: ${result.chunks_created} chunks criados`);
          const updated = await listRepos();
          setRepos(updated);
          setTab("indexed");
        }
      },
      (error) => {
        setIndexProgress(null);
        setIndexingRepo(null);
        toast.error(error || "Erro ao indexar");
      },
    );
  }

  async function handleReindex(repoName: string) {
    if (indexingRepo) return;
    setIndexingRepo(repoName);
    setIndexProgress({ percent: 0, detail: "Iniciando..." });

    const ghRepo = ghRepos.find((r) => r.name === repoName);
    const repoUrl = ghRepo?.url || `https://github.com/${repoName}`;

    await ingestRepositoryStream(
      repoUrl,
      repoName,
      (_stage, percent, detail) => {
        setIndexProgress({ percent, detail });
      },
      async (result) => {
        setIndexProgress(null);
        setIndexingRepo(null);
        toast.success(`Re-indexado: ${result.chunks_created} chunks`);
        const updated = await listRepos();
        setRepos(updated);
      },
      (error) => {
        setIndexProgress(null);
        setIndexingRepo(null);
        toast.error(error || "Erro ao re-indexar");
      },
    );
  }

  function toggleFavorite(name: string) {
    setFavorites((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

  const indexedNames = new Set(repos.map((r) => r.name));
  const availableRepos = ghRepos.filter((r) => !indexedNames.has(r.name));

  // Filter + sort repos (favorites first)
  const filteredRepos = repos
    .filter((r) => r.name.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      const aFav = favorites.has(a.name) ? 0 : 1;
      const bFav = favorites.has(b.name) ? 0 : 1;
      return aFav - bFav || a.name.localeCompare(b.name);
    });

  const filteredGhRepos = availableRepos.filter((r) =>
    r.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex h-full">
      {/* Left: Repo list */}
      <div
        className={cn(
          "flex flex-col border-r border-border bg-card-bg shrink-0",
          !activeRepo && "w-full max-w-4xl mx-auto border-r-0"
        )}
        style={activeRepo ? { width: `${sidebarWidth}px` } : undefined}
      >
        {/* Header */}
        <div className="p-4 border-b border-border shrink-0">
          <div className="flex items-center justify-between mb-3">
            <h1 className={cn("font-bold", activeRepo ? "text-lg" : "text-2xl")}>
              Repositórios
            </h1>
            {ghConnected && canManage && (
              <div className="flex items-center gap-0.5 rounded-lg border border-border bg-background p-0.5">
                <button
                  onClick={() => setTab("indexed")}
                  className={cn(
                    "px-2 py-1 text-xs font-medium rounded-md transition-colors",
                    tab === "indexed"
                      ? "bg-accent text-white"
                      : "text-muted hover:text-foreground"
                  )}
                >
                  Indexados ({repos.length})
                </button>
                <button
                  onClick={() => setTab("available")}
                  className={cn(
                    "px-2 py-1 text-xs font-medium rounded-md transition-colors",
                    tab === "available"
                      ? "bg-accent text-white"
                      : "text-muted hover:text-foreground"
                  )}
                >
                  GitHub ({ghRepos.length})
                </button>
              </div>
            )}
          </div>

          {/* Search */}
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar repositório..."
              className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent/50"
            />
          </div>
        </div>

        {/* GitHub not connected */}
        {ghConnected === false && role === "admin" && (
          <div className="flex items-center gap-2 p-3 m-3 rounded-xl border border-warning/30 bg-warning-surface">
            <AlertTriangle size={16} className="text-warning shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium">GitHub não conectado</p>
            </div>
            <Link
              href="/dashboard/settings"
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg bg-warning text-black hover:opacity-90 shrink-0 transition-opacity"
            >
              <Settings size={10} />
              Configurar
            </Link>
          </div>
        )}

        {/* Progress bar */}
        {indexingRepo && indexProgress && (
          <div className="px-4 py-3 border-b border-border shrink-0">
            <div className="flex items-center justify-between mb-1.5">
              <p className="text-xs font-medium text-foreground truncate">
                {indexingRepo}
              </p>
              <span className="text-xs font-mono text-accent shrink-0 ml-2">
                {indexProgress.percent}%
              </span>
            </div>
            <div className="w-full h-2 bg-border/50 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-accent to-accent-light rounded-full transition-all duration-300 ease-out"
                style={{ width: `${indexProgress.percent}%` }}
              />
            </div>
            <p className="text-[11px] text-muted mt-1 truncate">
              {indexProgress.detail}
            </p>
          </div>
        )}

        {/* Repo list */}
        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          {loading ? (
            <div className="flex items-center justify-center gap-2 py-12 text-muted text-sm">
              <Loader2 size={16} className="animate-spin" />
              Carregando...
            </div>
          ) : tab === "indexed" ? (
            <>
              {filteredRepos.length === 0 ? (
                <div className="text-center py-12">
                  <FolderGit2 size={36} className="mx-auto text-muted mb-3" />
                  <p className="text-sm font-medium mb-1">Nenhum repositório indexado</p>
                  <p className="text-xs text-muted">
                    {ghConnected
                      ? 'Clique em "GitHub" para indexar repositórios.'
                      : "Configure o GitHub nas configurações."}
                  </p>
                </div>
              ) : (
                filteredRepos.map((repo) => (
                  <div
                    key={repo.name}
                    role="button"
                    tabIndex={0}
                    onClick={() => setActiveRepo(repo.name)}
                    onKeyDown={(e) => { if (e.key === "Enter") setActiveRepo(repo.name); }}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-colors group",
                      activeRepo === repo.name
                        ? "bg-accent-surface border border-accent/30"
                        : "hover:bg-hover border border-transparent"
                    )}
                  >
                    <Database size={16} className={cn(
                      "shrink-0",
                      activeRepo === repo.name ? "text-accent" : "text-accent"
                    )} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium truncate">{repo.name}</p>
                        <StatusBadge status={repo.status} />
                      </div>
                      <p className="text-xs text-muted">
                        {repo.chunks_count} chunks
                        {repo.last_indexed && (
                          <> · {new Date(repo.last_indexed).toLocaleDateString("pt-BR")}</>
                        )}
                      </p>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleFavorite(repo.name);
                        }}
                        className="p-1 rounded text-muted hover:text-yellow-400 transition-colors"
                        title={favorites.has(repo.name) ? "Remover favorito" : "Favoritar"}
                      >
                        {favorites.has(repo.name) ? (
                          <Star size={14} className="fill-yellow-400 text-yellow-400" />
                        ) : (
                          <StarOff size={14} className="opacity-0 group-hover:opacity-100" />
                        )}
                      </button>
                      {canManage && (
                        <Link
                          href={`/dashboard/docs/${encodeURIComponent(repo.name)}`}
                          onClick={(e) => e.stopPropagation()}
                          className="p-1 rounded text-muted hover:text-accent transition-colors opacity-0 group-hover:opacity-100"
                          title="Documentacao"
                        >
                          <BookOpen size={14} />
                        </Link>
                      )}
                      {canManage && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleReindex(repo.name);
                          }}
                          disabled={indexingRepo === repo.name}
                          className="p-1 rounded text-muted hover:text-foreground transition-colors opacity-0 group-hover:opacity-100 disabled:opacity-50"
                          title="Re-indexar"
                        >
                          {indexingRepo === repo.name ? (
                            <Loader2 size={14} className="animate-spin" />
                          ) : (
                            <RefreshCw size={14} />
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </>
          ) : (
            <>
              {loadingGh ? (
                <div className="flex items-center justify-center gap-2 py-12 text-muted text-sm">
                  <Loader2 size={16} className="animate-spin" />
                  Buscando do GitHub...
                </div>
              ) : filteredGhRepos.length === 0 ? (
                <div className="text-center py-12">
                  <Github size={36} className="mx-auto text-muted mb-3" />
                  <p className="text-sm font-medium">Todos já indexados</p>
                </div>
              ) : (
                filteredGhRepos.map((repo) => (
                  <div
                    key={repo.full_name}
                    className="flex items-center gap-3 px-3 py-2.5 rounded-lg border border-transparent hover:bg-hover transition-colors"
                  >
                    <Github size={16} className="text-muted shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium truncate">{repo.name}</p>
                        {repo.private ? (
                          <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] rounded-full bg-warning-surface text-warning">
                            <Lock size={8} />
                            Privado
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] rounded-full bg-success-surface text-success">
                            <Globe size={8} />
                            Público
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-muted">
                        {repo.language || "—"}
                        {repo.updated_at && (
                          <> · {new Date(repo.updated_at).toLocaleDateString("pt-BR")}</>
                        )}
                      </p>
                    </div>
                    <button
                      onClick={() => handleIndex(repo)}
                      disabled={indexingRepo !== null}
                      className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-md bg-accent hover:bg-accent-dark text-white transition-colors disabled:opacity-50 shrink-0"
                    >
                      {indexingRepo === repo.full_name ? (
                        <>
                          <Loader2 size={12} className="animate-spin" />
                          {indexProgress ? `${indexProgress.percent}%` : "..."}
                        </>
                      ) : (
                        <>
                          <Download size={12} />
                          Indexar
                        </>
                      )}
                    </button>
                  </div>
                ))
              )}
            </>
          )}
        </div>
      </div>

      {/* Resize handle */}
      {activeRepo && (
        <div
          onMouseDown={handleMouseDown}
          className={cn(
            "w-1 shrink-0 cursor-col-resize group relative hover:w-1.5 transition-all",
            isResizing ? "bg-accent" : "bg-border hover:bg-accent/50"
          )}
        >
          <div className="absolute inset-y-0 -left-1 -right-1" />
        </div>
      )}

      {/* Right: Chat panel */}
      {activeRepo ? (
        <div className="flex-1 min-w-0 bg-background">
          <ChatPanel
            repoName={activeRepo}
            onClose={() => setActiveRepo(null)}
          />
        </div>
      ) : (
        !loading && repos.length > 0 && (
          <div className="flex-1 hidden lg:flex items-center justify-center text-center">
            <div>
              <MessageSquare size={48} className="mx-auto text-muted mb-4" />
              <p className="text-lg font-medium mb-1">Selecione um repositório</p>
              <p className="text-sm text-muted">
                Clique em um repositório para abrir o chat
              </p>
            </div>
          </div>
        )
      )}
    </div>
  );
}
