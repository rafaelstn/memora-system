"use client";

import { cn } from "@/lib/utils";
import type { Source } from "@/lib/types";
import { ChunkTypeBadge } from "@/components/ui/badge";
import { X, ExternalLink, FileCode } from "lucide-react";

interface SourcesPanelProps {
  sources: Source[];
  open: boolean;
  onClose: () => void;
}

export function SourcesPanel({ sources, open, onClose }: SourcesPanelProps) {
  if (!open) return null;

  return (
    <aside className="w-[320px] shrink-0 h-full border-l border-border bg-sidebar-bg overflow-y-auto">
      {/* Header */}
      <div className="sticky top-0 bg-sidebar-bg z-10 flex items-center justify-between px-4 py-3 border-b border-border">
        <h3 className="text-sm font-semibold text-foreground">
          Fontes consultadas ({sources.length})
        </h3>
        <button
          onClick={onClose}
          className="p-1 rounded-lg hover:bg-hover text-muted hover:text-foreground transition-colors"
          title="Fechar painel"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Sources */}
      <div className="p-3 space-y-3">
        {sources.length === 0 && (
          <p className="text-sm text-muted text-center py-6">
            Nenhuma fonte disponivel
          </p>
        )}

        {sources.map((source, idx) => (
          <div
            key={idx}
            className="rounded-xl border border-border bg-card-bg p-3 hover:border-accent/20 transition-colors"
          >
            <div className="flex items-start gap-2 mb-2">
              <ChunkTypeBadge type={source.chunk_type} />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-foreground truncate">
                  {source.chunk_name}
                </p>
                <div className="flex items-center gap-1 text-xs text-muted mt-0.5">
                  <FileCode className="h-3 w-3" />
                  <span className="truncate">{source.file_path}</span>
                  {source.start_line && (
                    <span className="shrink-0">L{source.start_line}</span>
                  )}
                </div>
              </div>
            </div>

            {/* Preview */}
            <div className="bg-background rounded-lg p-2.5 mt-2">
              <pre className="text-xs font-mono text-muted whitespace-pre-wrap leading-relaxed line-clamp-5">
                {source.content_preview}
              </pre>
            </div>

            {/* GitHub link */}
            <a
              href="#"
              className="flex items-center gap-1 text-xs text-accent hover:text-accent-light mt-2 transition-colors"
            >
              <ExternalLink className="h-3 w-3" />
              Ver no GitHub
            </a>
          </div>
        ))}
      </div>
    </aside>
  );
}
