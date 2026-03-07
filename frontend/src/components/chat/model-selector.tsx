"use client";

import { useState, useEffect, useRef } from "react";
import { ChevronDown, Zap, Brain, Star } from "lucide-react";
import { cn } from "@/lib/utils";
import { listActiveLLMProviders } from "@/lib/api";
import { useAuth } from "@/lib/hooks/useAuth";
import type { LLMProviderActive } from "@/lib/types";

function providerIcon(provider: string, size = 12) {
  switch (provider) {
    case "openai":
      return <Zap size={size} className="text-green-500" />;
    case "anthropic":
      return <Brain size={size} className="text-orange-500" />;
    case "google":
      return <Zap size={size} className="text-blue-500" />;
    case "groq":
      return <Zap size={size} className="text-purple-500" />;
    default:
      return <Zap size={size} className="text-muted" />;
  }
}

interface ModelSelectorProps {
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}

export function ModelSelector({ selectedId, onSelect }: ModelSelectorProps) {
  const { role } = useAuth();
  const [providers, setProviders] = useState<LLMProviderActive[]>([]);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listActiveLLMProviders()
      .then(setProviders)
      .catch(() => {});
  }, []);

  // Close on click outside
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  if (providers.length === 0) return null;

  const defaultProvider = providers.find((p) => p.is_default);
  const selected = providers.find((p) => p.id === selectedId) || defaultProvider;

  // Suporte: show fixed label, no dropdown
  if (role === "suporte") {
    if (!defaultProvider) return null;
    return (
      <div className="flex items-center gap-1.5 px-2 py-1 text-xs text-muted">
        {providerIcon(defaultProvider.provider)}
        <span>Usando {defaultProvider.name}</span>
      </div>
    );
  }

  // Dev/Admin: dropdown
  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs text-muted hover:text-foreground hover:bg-hover transition-colors"
      >
        {selected && providerIcon(selected.provider)}
        <span className="max-w-[120px] truncate">{selected?.name || "Modelo"}</span>
        <ChevronDown size={12} className={cn("transition-transform", open && "rotate-180")} />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1 w-56 rounded-lg border border-border bg-card-bg py-1 z-50" style={{ boxShadow: "var(--shadow-lg)" }}>
          {providers.map((p) => (
            <button
              key={p.id}
              onClick={() => {
                onSelect(p.is_default ? null : p.id);
                setOpen(false);
              }}
              className={cn(
                "w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-hover transition-colors",
                (selectedId === p.id || (!selectedId && p.is_default)) && "bg-accent-surface"
              )}
            >
              {providerIcon(p.provider, 14)}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="truncate font-medium text-xs">{p.name}</span>
                  {p.is_default && (
                    <Star size={10} className="text-accent shrink-0 fill-accent" />
                  )}
                </div>
                <span className="text-[11px] text-muted font-mono">{p.model_id}</span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
