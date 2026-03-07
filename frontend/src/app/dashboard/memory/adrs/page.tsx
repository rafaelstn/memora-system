"use client";

import { useState, useEffect } from "react";
import {
  FileText,
  Plus,
  Loader2,
  Trash2,
  ExternalLink,
  X,
} from "lucide-react";
import toast from "react-hot-toast";
import { cn } from "@/lib/utils";
import { Modal } from "@/components/ui/modal";
import { listKnowledgeEntries, createADR, deleteADR, getKnowledgeEntry } from "@/lib/api";
import type { KnowledgeEntry, KnowledgeEntryDetail } from "@/lib/types";

const DECISION_TYPES = [
  { value: "arquitetura", label: "Arquitetura" },
  { value: "dependencia", label: "Dependencia" },
  { value: "padrao", label: "Padrao" },
  { value: "correcao", label: "Correcao" },
  { value: "refatoracao", label: "Refatoracao" },
];

export default function ADRsPage() {
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState<KnowledgeEntryDetail | null>(null);

  // Create form
  const [newTitle, setNewTitle] = useState("");
  const [newContent, setNewContent] = useState("");
  const [newType, setNewType] = useState("arquitetura");
  const [newFiles, setNewFiles] = useState("");

  useEffect(() => {
    fetchEntries();
  }, [typeFilter]);

  function fetchEntries() {
    setLoading(true);
    listKnowledgeEntries({
      source_type: "adr",
      decision_type: typeFilter || undefined,
    })
      .then(setEntries)
      .catch(() => toast.error("Erro ao carregar ADRs"))
      .finally(() => setLoading(false));
  }

  async function handleCreate() {
    if (!newTitle.trim() || !newContent.trim()) {
      toast.error("Titulo e conteudo obrigatorios");
      return;
    }
    setCreating(true);
    try {
      const filePaths = newFiles
        .split(",")
        .map((f) => f.trim())
        .filter(Boolean);
      const result = await createADR({
        title: newTitle,
        content: newContent,
        decision_type: newType,
        file_paths: filePaths.length > 0 ? filePaths : undefined,
      });
      setEntries((prev) => [
        {
          id: result.id,
          title: result.title,
          source_type: "adr",
          decision_type: newType as KnowledgeEntry["decision_type"],
          created_at: new Date().toISOString(),
        },
        ...prev,
      ]);
      setShowCreate(false);
      setNewTitle("");
      setNewContent("");
      setNewType("arquitetura");
      setNewFiles("");
      toast.success("ADR criado");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao criar");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteADR(id);
      setEntries((prev) => prev.filter((e) => e.id !== id));
      if (selectedEntry?.id === id) setSelectedEntry(null);
      toast.success("ADR removido");
    } catch {
      toast.error("Erro ao remover");
    }
  }

  async function openEntry(id: string) {
    try {
      const entry = await getKnowledgeEntry(id);
      setSelectedEntry(entry);
    } catch {
      toast.error("Erro ao carregar");
    }
  }

  return (
    <div className="flex flex-1 overflow-hidden">
      <div className={cn("flex-1 p-5 lg:p-8 space-y-6 overflow-y-auto", selectedEntry && "lg:mr-[420px]")}>
        {/* Header */}
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <FileText size={20} className="text-accent" />
            Decisoes de Arquitetura (ADRs)
          </h2>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors"
          >
            <Plus size={14} />
            Nova Decisao
          </button>
        </div>

        {/* Filters */}
        <div className="flex gap-3">
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-3 py-2 text-sm rounded-lg border border-border bg-card-bg"
          >
            <option value="">Todos os tipos</option>
            {DECISION_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>

        {/* List */}
        {loading ? (
          <div className="flex items-center justify-center gap-2 py-12 text-muted text-sm">
            <Loader2 size={16} className="animate-spin" /> Carregando...
          </div>
        ) : entries.length === 0 ? (
          <p className="text-sm text-muted text-center py-12">
            Nenhum ADR encontrado. Clique em &ldquo;Nova Decisao&rdquo; para criar.
          </p>
        ) : (
          <div className="space-y-2">
            {entries.map((entry) => (
              <div
                key={entry.id}
                className="group flex items-center gap-3 px-4 py-3 rounded-lg border border-border bg-card-bg hover:bg-hover transition-colors"
              >
                <button onClick={() => openEntry(entry.id)} className="flex-1 text-left min-w-0">
                  <p className="text-sm font-medium">{entry.title}</p>
                  <div className="flex items-center gap-2 mt-1">
                    {entry.decision_type && (
                      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-accent-surface text-accent-text">
                        {entry.decision_type}
                      </span>
                    )}
                    <span className="text-[10px] text-muted">
                      {new Date(entry.created_at).toLocaleDateString("pt-BR")}
                    </span>
                  </div>
                  {entry.summary && (
                    <p className="text-xs text-muted mt-1 line-clamp-1">{entry.summary}</p>
                  )}
                </button>
                <button
                  onClick={() => handleDelete(entry.id)}
                  className="p-1.5 rounded-lg border border-border hover:bg-hover transition-colors text-danger opacity-0 group-hover:opacity-100"
                  title="Remover"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Detail Drawer */}
      {selectedEntry && (
        <div className="fixed right-0 top-0 h-full w-[420px] border-l border-border bg-card-bg shadow-lg z-30 flex flex-col overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-border">
            <span className="text-xs font-medium px-2 py-0.5 rounded bg-accent-surface text-accent-text">ADR</span>
            <button onClick={() => setSelectedEntry(null)} className="p-1 rounded hover:bg-hover">
              <X size={16} />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            <h2 className="text-lg font-semibold">{selectedEntry.title}</h2>
            {selectedEntry.decision_type && (
              <span className="text-xs px-2 py-0.5 rounded bg-accent-surface text-accent-text">
                {selectedEntry.decision_type}
              </span>
            )}
            {selectedEntry.summary && selectedEntry.summary !== selectedEntry.content && (
              <div>
                <h3 className="text-xs font-semibold text-muted mb-1">Resumo</h3>
                <p className="text-sm whitespace-pre-wrap">{selectedEntry.summary}</p>
              </div>
            )}
            <div>
              <h3 className="text-xs font-semibold text-muted mb-1">Conteudo</h3>
              <div className="text-sm whitespace-pre-wrap leading-relaxed">{selectedEntry.content}</div>
            </div>
            {selectedEntry.file_paths && selectedEntry.file_paths.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-muted mb-1">Arquivos</h3>
                <div className="flex flex-wrap gap-1">
                  {selectedEntry.file_paths.map((fp) => (
                    <span key={fp} className="text-xs font-mono px-1.5 py-0.5 rounded bg-hover">{fp}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Create Modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Nova Decisao de Arquitetura">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Titulo *</label>
            <input
              type="text"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="Ex: Migrar de REST para GraphQL"
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground placeholder:text-muted"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Tipo de decisao</label>
            <select
              value={newType}
              onChange={(e) => setNewType(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card-bg"
            >
              {DECISION_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Arquivos relacionados (opcional)</label>
            <input
              type="text"
              value={newFiles}
              onChange={(e) => setNewFiles(e.target.value)}
              placeholder="app/core/auth.py, app/models/user.py"
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground placeholder:text-muted font-mono text-xs"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Conteudo (Markdown) *</label>
            <textarea
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              rows={10}
              placeholder="## Contexto&#10;&#10;## Decisao&#10;&#10;## Consequencias"
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground placeholder:text-muted font-mono"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={() => setShowCreate(false)}
              className="px-4 py-2 text-sm rounded-lg border border-border hover:bg-hover transition-colors"
            >
              Cancelar
            </button>
            <button
              onClick={handleCreate}
              disabled={creating}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors disabled:opacity-50"
            >
              {creating && <Loader2 size={14} className="animate-spin" />}
              Salvar
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
