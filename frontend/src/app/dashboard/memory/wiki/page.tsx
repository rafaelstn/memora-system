"use client";

import { useState, useEffect } from "react";
import { BookOpen, RefreshCw, Loader2, Plus, Trash2, Check, Sparkles, Code, Brain } from "lucide-react";
import toast from "react-hot-toast";
import { Modal } from "@/components/ui/modal";
import {
  listKnowledgeWikis,
  getKnowledgeWiki,
  generateWiki,
  getWikiSuggestions,
  generateWikiBatch,
  deleteWiki,
  listRepos,
} from "@/lib/api";
import type { KnowledgeWiki, KnowledgeWikiDetail, WikiSuggestion } from "@/lib/types";

export default function WikiPage() {
  const [wikis, setWikis] = useState<KnowledgeWiki[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedWiki, setSelectedWiki] = useState<KnowledgeWikiDetail | null>(null);
  const [wikiLoading, setWikiLoading] = useState(false);
  const [generating, setGenerating] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  // Suggestions
  const [suggestions, setSuggestions] = useState<WikiSuggestion[]>([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [selectedSuggestions, setSelectedSuggestions] = useState<Set<string>>(new Set());
  const [batchGenerating, setBatchGenerating] = useState(false);

  // Generate modal
  const [showGenerate, setShowGenerate] = useState(false);
  const [genPath, setGenPath] = useState("");
  const [genName, setGenName] = useState("");
  const [genRepoId, setGenRepoId] = useState("");
  const [genLoading, setGenLoading] = useState(false);
  const [repos, setRepos] = useState<{ name: string }[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [w, r] = await Promise.all([listKnowledgeWikis(), listRepos()]);
      setWikis(w);
      setRepos(r);
    } catch {
      toast.error("Erro ao carregar wikis");
    } finally {
      setLoading(false);
    }
    loadSuggestions();
  }

  async function loadSuggestions() {
    setSuggestionsLoading(true);
    try {
      const s = await getWikiSuggestions();
      setSuggestions(s);
      setSelectedSuggestions(new Set());
    } catch {
      // silent — suggestions are optional
    } finally {
      setSuggestionsLoading(false);
    }
  }

  async function openWiki(id: string) {
    setWikiLoading(true);
    try {
      const wiki = await getKnowledgeWiki(id);
      setSelectedWiki(wiki);
    } catch {
      toast.error("Erro ao carregar wiki");
    } finally {
      setWikiLoading(false);
    }
  }

  async function handleRegenerate(wiki: KnowledgeWiki) {
    setGenerating(wiki.id);
    try {
      await generateWiki({
        repo_id: wiki.repo_id || "default",
        component_path: wiki.component_path,
        component_name: wiki.component_name,
      });
      toast.success("Regeneracao iniciada");
      setTimeout(() => {
        listKnowledgeWikis().then(setWikis).catch(() => {});
      }, 8000);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro");
    } finally {
      setGenerating(null);
    }
  }

  async function handleDelete(wiki: KnowledgeWiki) {
    if (!confirm(`Deletar wiki "${wiki.component_name}"?`)) return;
    setDeleting(wiki.id);
    try {
      await deleteWiki(wiki.id);
      setWikis((prev) => prev.filter((w) => w.id !== wiki.id));
      if (selectedWiki?.id === wiki.id) setSelectedWiki(null);
      toast.success("Wiki deletada");
      loadSuggestions();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao deletar");
    } finally {
      setDeleting(null);
    }
  }

  function toggleSuggestion(path: string) {
    setSelectedSuggestions((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }

  function selectAllSuggestions() {
    if (selectedSuggestions.size === suggestions.length) {
      setSelectedSuggestions(new Set());
    } else {
      setSelectedSuggestions(new Set(suggestions.map((s) => s.path)));
    }
  }

  async function handleBatchGenerate() {
    if (selectedSuggestions.size === 0) {
      toast.error("Selecione ao menos um componente");
      return;
    }
    setBatchGenerating(true);
    try {
      const components = suggestions
        .filter((s) => selectedSuggestions.has(s.path))
        .map((s) => ({ path: s.path, name: s.name, repo_id: s.repo_name || undefined }));
      await generateWikiBatch(components);
      toast.success(`Gerando ${components.length} wikis. Atualize em instantes.`);
      setSelectedSuggestions(new Set());
      // Refresh after delay
      setTimeout(() => {
        loadData();
      }, 10000);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao gerar");
    } finally {
      setBatchGenerating(false);
    }
  }

  async function handleGenerate() {
    if (!genPath.trim()) {
      toast.error("Caminho do componente obrigatorio");
      return;
    }
    setGenLoading(true);
    try {
      await generateWiki({
        repo_id: genRepoId || "default",
        component_path: genPath.trim(),
        component_name: genName.trim() || undefined,
      });
      toast.success("Geracao iniciada. Atualize em instantes.");
      setShowGenerate(false);
      setGenPath("");
      setGenName("");
      setTimeout(() => {
        loadData();
      }, 8000);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao gerar");
    } finally {
      setGenLoading(false);
    }
  }

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* Left panel: wiki list + suggestions */}
      <div className="w-80 border-r border-border overflow-y-auto shrink-0">
        {/* Suggestions section */}
        {suggestions.length > 0 && (
          <div className="border-b border-border">
            <div className="p-3 bg-accent/5 border-b border-border">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-semibold flex items-center gap-1.5 text-accent">
                  <Sparkles size={13} />
                  Sugestoes ({suggestions.length})
                </h3>
                <div className="flex items-center gap-1">
                  <button
                    onClick={selectAllSuggestions}
                    className="text-[10px] px-1.5 py-0.5 rounded border border-border hover:bg-hover transition-colors"
                  >
                    {selectedSuggestions.size === suggestions.length ? "Desmarcar" : "Todos"}
                  </button>
                  <button
                    onClick={handleBatchGenerate}
                    disabled={batchGenerating || selectedSuggestions.size === 0}
                    className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-accent hover:bg-accent-dark text-white transition-colors disabled:opacity-50"
                  >
                    {batchGenerating ? <Loader2 size={10} className="animate-spin" /> : <Check size={10} />}
                    Gerar ({selectedSuggestions.size})
                  </button>
                </div>
              </div>
              <p className="text-[10px] text-muted">Selecione os componentes para gerar wiki</p>
            </div>
            <div className="max-h-48 overflow-y-auto divide-y divide-border">
              {suggestions.map((s) => (
                <label
                  key={s.path}
                  className="flex items-start gap-2 px-3 py-2 hover:bg-hover transition-colors cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selectedSuggestions.has(s.path)}
                    onChange={() => toggleSuggestion(s.path)}
                    className="mt-0.5 rounded border-border"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium truncate">{s.name}</p>
                    <p className="text-[10px] text-muted font-mono truncate">{s.path}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      {s.source === "code" ? (
                        <span className="inline-flex items-center gap-0.5 text-[9px] text-blue-500">
                          <Code size={8} /> {s.chunk_count} chunks
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-0.5 text-[9px] text-purple-500">
                          <Brain size={8} /> knowledge
                        </span>
                      )}
                      {s.repo_name && (
                        <span className="text-[9px] text-muted">{s.repo_name}</span>
                      )}
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Wiki list */}
        <div className="p-4 border-b border-border flex items-center justify-between">
          <h2 className="text-sm font-semibold flex items-center gap-2">
            <BookOpen size={16} className="text-accent" />
            Wikis ({wikis.length})
          </h2>
          <div className="flex items-center gap-1">
            <button
              onClick={loadSuggestions}
              disabled={suggestionsLoading}
              className="p-1.5 rounded-lg border border-border hover:bg-hover transition-colors"
              title="Atualizar sugestoes"
            >
              {suggestionsLoading ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
            </button>
            <button
              onClick={() => setShowGenerate(true)}
              className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors"
            >
              <Plus size={12} />
              Manual
            </button>
          </div>
        </div>
        {loading ? (
          <div className="flex items-center justify-center gap-2 py-8 text-muted text-sm">
            <Loader2 size={14} className="animate-spin" /> Carregando...
          </div>
        ) : wikis.length === 0 ? (
          <p className="text-sm text-muted text-center py-8 px-4">
            Nenhuma wiki gerada. Selecione componentes nas sugestoes acima ou clique em &ldquo;Manual&rdquo;.
          </p>
        ) : (
          <div className="divide-y divide-border">
            {wikis.map((wiki) => (
              <div key={wiki.id} className="flex items-center gap-1.5 px-3 py-2.5 hover:bg-hover transition-colors">
                <button
                  onClick={() => openWiki(wiki.id)}
                  className="flex-1 text-left min-w-0"
                >
                  <p className="text-sm font-medium truncate">{wiki.component_name}</p>
                  <p className="text-xs text-muted font-mono truncate">{wiki.component_path}</p>
                  <p className="text-[10px] text-muted mt-0.5">
                    v{wiki.generation_version} — {wiki.last_generated_at
                      ? new Date(wiki.last_generated_at).toLocaleDateString("pt-BR")
                      : ""}
                  </p>
                </button>
                <div className="flex items-center gap-0.5 shrink-0">
                  <button
                    onClick={() => handleRegenerate(wiki)}
                    disabled={generating === wiki.id}
                    className="p-1 rounded border border-border hover:bg-hover transition-colors"
                    title="Regenerar"
                  >
                    {generating === wiki.id ? (
                      <Loader2 size={11} className="animate-spin" />
                    ) : (
                      <RefreshCw size={11} />
                    )}
                  </button>
                  <button
                    onClick={() => handleDelete(wiki)}
                    disabled={deleting === wiki.id}
                    className="p-1 rounded border border-border hover:bg-hover transition-colors text-red-400 hover:text-red-500"
                    title="Deletar"
                  >
                    {deleting === wiki.id ? (
                      <Loader2 size={11} className="animate-spin" />
                    ) : (
                      <Trash2 size={11} />
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Wiki content */}
      <div className="flex-1 overflow-y-auto p-6">
        {wikiLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 size={20} className="animate-spin text-muted" />
          </div>
        ) : selectedWiki ? (
          <div className="max-w-3xl">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h1 className="text-xl font-semibold">{selectedWiki.component_name}</h1>
                <p className="text-sm text-muted font-mono">{selectedWiki.component_path}</p>
              </div>
              <span className="text-xs text-muted">v{selectedWiki.generation_version}</span>
            </div>
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <div className="whitespace-pre-wrap text-sm leading-relaxed">
                {selectedWiki.content}
              </div>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-20 text-muted">
            <BookOpen size={40} className="mb-3 opacity-30" />
            <p className="text-sm">Selecione uma wiki para visualizar</p>
            {suggestions.length > 0 && (
              <p className="text-xs mt-2 text-accent">
                {suggestions.length} sugestoes disponiveis no painel esquerdo
              </p>
            )}
          </div>
        )}
      </div>

      {/* Generate Wiki Modal */}
      <Modal open={showGenerate} onClose={() => setShowGenerate(false)} title="Gerar Wiki Manual">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Caminho do componente *</label>
            <input
              type="text"
              value={genPath}
              onChange={(e) => setGenPath(e.target.value)}
              placeholder="Ex: app/core/auth.py"
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground placeholder:text-muted font-mono"
            />
            <p className="text-xs text-muted mt-1">Arquivo ou pasta do componente indexado</p>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Nome do componente (opcional)</label>
            <input
              type="text"
              value={genName}
              onChange={(e) => setGenName(e.target.value)}
              placeholder="Ex: Modulo de Autenticacao"
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground placeholder:text-muted"
            />
          </div>
          {repos.length > 0 && (
            <div>
              <label className="block text-sm font-medium mb-1">Repositorio</label>
              <select
                value={genRepoId}
                onChange={(e) => setGenRepoId(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card-bg"
              >
                <option value="">Todos</option>
                {repos.map((r) => (
                  <option key={r.name} value={r.name}>{r.name}</option>
                ))}
              </select>
            </div>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={() => setShowGenerate(false)}
              className="px-4 py-2 text-sm rounded-lg border border-border hover:bg-hover transition-colors"
            >
              Cancelar
            </button>
            <button
              onClick={handleGenerate}
              disabled={genLoading}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors disabled:opacity-50"
            >
              {genLoading && <Loader2 size={14} className="animate-spin" />}
              Gerar
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
