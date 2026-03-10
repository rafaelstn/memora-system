"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  X,
  MessageSquare,
  BookOpen,
  Brain,
  FileText,
  Code,
  Shield,
  AlertCircle,
  BookMarked,
  Loader2,
  Clock,
} from "lucide-react";
import { useGlobalSearch, type SearchResultItem } from "@/lib/hooks/useGlobalSearch";

const SOURCE_CONFIG: Record<
  string,
  { icon: typeof Search; label: string; color: string }
> = {
  conversations: {
    icon: MessageSquare,
    label: "Conversas",
    color: "text-blue-500",
  },
  business_rules: {
    icon: BookOpen,
    label: "Regras de Negocio",
    color: "text-emerald-500",
  },
  knowledge_entries: {
    icon: Brain,
    label: "Memoria Tecnica",
    color: "text-purple-500",
  },
  repo_docs: {
    icon: FileText,
    label: "Documentacao",
    color: "text-orange-500",
  },
  review_findings: {
    icon: Code,
    label: "Revisao de Codigo",
    color: "text-cyan-500",
  },
  security_findings: {
    icon: Shield,
    label: "Seguranca",
    color: "text-red-500",
  },
  error_alerts: {
    icon: AlertCircle,
    label: "Alertas",
    color: "text-yellow-500",
  },
  knowledge_wikis: {
    icon: BookMarked,
    label: "Wikis",
    color: "text-indigo-500",
  },
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `ha ${mins}min`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `ha ${hours}h`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `ha ${days}d`;
  return `ha ${Math.floor(days / 30)}m`;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export default function GlobalSearch({ isOpen, onClose }: Props) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const {
    query,
    results,
    isLoading,
    error,
    recentSearches,
    debouncedSearch,
    reset,
  } = useGlobalSearch();

  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());

  // Flatten results for keyboard navigation
  const flatItems: { source: string; item: SearchResultItem }[] = [];
  if (results?.results) {
    for (const [source, items] of Object.entries(results.results)) {
      const limit = expandedSources.has(source) ? 10 : 3;
      for (const item of items.slice(0, limit)) {
        flatItems.push({ source, item });
      }
    }
  }

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setSelectedIndex(-1);
    } else {
      reset();
      setExpandedSources(new Set());
    }
  }, [isOpen, reset]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, flatItems.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, -1));
      } else if (e.key === "Enter" && selectedIndex >= 0) {
        e.preventDefault();
        const selected = flatItems[selectedIndex];
        if (selected) {
          router.push(selected.item.url);
          onClose();
        }
      }
    },
    [flatItems, selectedIndex, router, onClose]
  );

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]"
      onClick={onClose}
    >
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" />
      <div
        className="relative w-full max-w-2xl bg-background border border-border rounded-xl shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border">
          <Search size={18} className="text-muted flex-shrink-0" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Buscar em todos os modulos..."
            className="flex-1 bg-transparent outline-none text-sm"
            value={query}
            onChange={(e) => debouncedSearch(e.target.value)}
          />
          {isLoading && (
            <Loader2 size={16} className="animate-spin text-muted" />
          )}
          <kbd className="hidden sm:inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] text-muted bg-muted/10 border border-border rounded">
            ESC
          </kbd>
          <button onClick={onClose} className="p-1 hover:bg-muted/10 rounded">
            <X size={16} className="text-muted" />
          </button>
        </div>

        {/* Results */}
        <div className="max-h-[60vh] overflow-y-auto">
          {error && (
            <div className="px-4 py-3 text-sm text-red-500">{error}</div>
          )}

          {/* Recent searches (when no query) */}
          {!query && recentSearches.length > 0 && (
            <div className="p-3">
              <p className="text-xs text-muted mb-2 px-1">Buscas recentes</p>
              {recentSearches.map((s, i) => (
                <button
                  key={i}
                  className="flex items-center gap-2 w-full px-3 py-2 text-sm rounded-lg hover:bg-muted/10 text-left"
                  onClick={() => debouncedSearch(s)}
                >
                  <Clock size={14} className="text-muted" />
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Empty state */}
          {query && !isLoading && results && flatItems.length === 0 && (
            <div className="px-4 py-8 text-center text-sm text-muted">
              Nenhum resultado para &quot;{query}&quot;
            </div>
          )}

          {/* Grouped results */}
          {results?.results &&
            Object.entries(results.results).map(([source, items]) => {
              const config = SOURCE_CONFIG[source] || {
                icon: Search,
                label: source,
                color: "text-muted",
              };
              const Icon = config.icon;
              const isExpanded = expandedSources.has(source);
              const visibleItems = items.slice(0, isExpanded ? 10 : 3);
              const hasMore = items.length > 3 && !isExpanded;

              return (
                <div key={source} className="border-b border-border last:border-0">
                  <div className="flex items-center gap-2 px-4 py-2 bg-muted/5">
                    <Icon size={14} className={config.color} />
                    <span className="text-xs font-medium text-muted">
                      {config.label}
                    </span>
                    <span className="text-[10px] text-muted/60">
                      ({items.length})
                    </span>
                  </div>
                  {visibleItems.map((item) => {
                    const globalIdx = flatItems.findIndex(
                      (f) => f.item.id === item.id && f.source === source
                    );
                    const isSelected = globalIdx === selectedIndex;

                    return (
                      <button
                        key={item.id}
                        className={`flex items-start gap-3 w-full px-4 py-2.5 text-left hover:bg-muted/10 transition-colors ${
                          isSelected ? "bg-accent/10" : ""
                        }`}
                        onClick={() => {
                          router.push(item.url);
                          onClose();
                        }}
                      >
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">
                            {item.title}
                          </p>
                          <p className="text-xs text-muted truncate mt-0.5">
                            {item.preview}
                          </p>
                        </div>
                        <span className="text-[10px] text-muted whitespace-nowrap mt-1">
                          {timeAgo(item.created_at)}
                        </span>
                      </button>
                    );
                  })}
                  {hasMore && (
                    <button
                      className="w-full px-4 py-1.5 text-xs text-accent hover:underline text-center"
                      onClick={() =>
                        setExpandedSources((prev) => new Set(prev).add(source))
                      }
                    >
                      Ver mais ({items.length - 3} restantes)
                    </button>
                  )}
                </div>
              );
            })}

          {/* Footer */}
          {results && flatItems.length > 0 && (
            <div className="px-4 py-2 border-t border-border text-center">
              <span className="text-[10px] text-muted">
                {results.total} resultados encontrados
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
