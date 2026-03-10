"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ChevronDown,
  ChevronRight,
  MessageSquare,
  Search,
  BookOpen,
  Brain,
  FileText,
  Code,
  Shield,
  AlertCircle,
  BookMarked,
  Loader2,
} from "lucide-react";
import { apiFetch } from "@/lib/api";

const SOURCE_ICONS: Record<string, typeof Search> = {
  conversations: MessageSquare,
  business_rules: BookOpen,
  knowledge_entries: Brain,
  repo_docs: FileText,
  review_findings: Code,
  security_findings: Shield,
  error_alerts: AlertCircle,
  knowledge_wikis: BookMarked,
};

interface SearchResultItem {
  id: string;
  title: string;
  preview: string;
  source: string;
  source_label: string;
  created_at: string;
  url: string;
}

interface Props {
  sourceType: "alert" | "review" | "knowledge" | "impact" | "security";
  sourceId: string;
  context: string;
  chatRepo?: string;
}

export default function RelatedContent({
  sourceType,
  sourceId,
  context,
  chatRepo,
}: Props) {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const [items, setItems] = useState<SearchResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [fetched, setFetched] = useState(false);

  useEffect(() => {
    if (!isOpen || fetched || !context) return;

    setLoading(true);
    apiFetch<{ results: Record<string, SearchResultItem[]> }>(
      `/api/search/global?q=${encodeURIComponent(context.slice(0, 200))}&limit=3`
    )
      .then((data) => {
        const allItems: SearchResultItem[] = [];
        for (const [, sourceItems] of Object.entries(data.results || {})) {
          for (const item of sourceItems) {
            if (item.id === sourceId) continue;
            allItems.push(item);
          }
        }
        setItems(allItems.slice(0, 9));
        setFetched(true);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [isOpen, fetched, context, sourceId]);

  function handleAskAssistant() {
    const repo = chatRepo || "default";
    const encoded = encodeURIComponent(context);
    router.push(`/chat/${repo}?context=${encoded}`);
  }

  if (!context) return null;

  return (
    <div className="mt-4 border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 w-full px-4 py-3 text-sm font-medium hover:bg-muted/5 transition-colors"
      >
        {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        Conteudo relacionado
      </button>

      {isOpen && (
        <div className="border-t border-border">
          <button
            onClick={handleAskAssistant}
            className="flex items-center gap-2 w-full px-4 py-2.5 text-sm text-accent hover:bg-accent/5 transition-colors border-b border-border"
          >
            <MessageSquare size={16} />
            Perguntar ao assistente sobre isso
          </button>

          {loading && (
            <div className="flex items-center gap-2 px-4 py-3 text-sm text-muted">
              <Loader2 size={14} className="animate-spin" />
              Buscando conteudo relacionado...
            </div>
          )}

          {!loading && items.length === 0 && fetched && (
            <div className="px-4 py-3 text-sm text-muted">
              Nenhum conteudo relacionado encontrado.
            </div>
          )}

          {items.map((item) => {
            const Icon = SOURCE_ICONS[item.source] || Search;
            return (
              <button
                key={item.id}
                onClick={() => router.push(item.url)}
                className="flex items-start gap-3 w-full px-4 py-2.5 text-left hover:bg-muted/5 transition-colors border-b border-border last:border-0"
              >
                <Icon size={14} className="text-muted mt-0.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{item.title}</p>
                  <p className="text-xs text-muted truncate">{item.preview}</p>
                  <span className="text-[10px] text-muted/60">
                    {item.source_label}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
