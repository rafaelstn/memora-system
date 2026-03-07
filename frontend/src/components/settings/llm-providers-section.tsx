"use client";

import { useState, useEffect } from "react";
import {
  Plus,
  Loader2,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Star,
  Trash2,
  Pencil,
  Zap,
  Brain,
} from "lucide-react";
import toast from "react-hot-toast";
import { Modal } from "@/components/ui/modal";
import { cn } from "@/lib/utils";
import type { LLMProvider, LLMProviderType } from "@/lib/types";
import {
  listLLMProviders,
  createLLMProvider,
  updateLLMProvider,
  deleteLLMProvider,
  setDefaultLLMProvider,
  testLLMProvider,
  testLLMConnection,
} from "@/lib/api";

const PROVIDER_OPTIONS: { value: LLMProviderType; label: string }[] = [
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "google", label: "Google" },
  { value: "groq", label: "Groq" },
  { value: "ollama", label: "Ollama" },
];

const PROVIDER_MODELS: Record<string, { id: string; label: string }[]> = {
  openai: [
    { id: "gpt-4o", label: "GPT-4o" },
    { id: "gpt-4o-mini", label: "GPT-4o Mini" },
    { id: "gpt-4.1", label: "GPT-4.1" },
    { id: "gpt-4.1-mini", label: "GPT-4.1 Mini" },
    { id: "gpt-4.1-nano", label: "GPT-4.1 Nano" },
  ],
  anthropic: [
    { id: "claude-opus-4-5-20250514", label: "Claude Opus 4.5" },
    { id: "claude-sonnet-4-5-20250514", label: "Claude Sonnet 4.5" },
    { id: "claude-sonnet-4-6", label: "Claude Sonnet 4.6" },
    { id: "claude-haiku-4-5-20251001", label: "Claude Haiku 4.5" },
  ],
  google: [
    { id: "gemini-1.5-pro", label: "Gemini 1.5 Pro" },
    { id: "gemini-1.5-flash", label: "Gemini 1.5 Flash" },
    { id: "gemini-2.0-flash", label: "Gemini 2.0 Flash" },
  ],
  groq: [
    { id: "llama-3.1-70b-versatile", label: "Llama 3.1 70B" },
    { id: "llama-3.1-8b-instant", label: "Llama 3.1 8B" },
    { id: "mixtral-8x7b-32768", label: "Mixtral 8x7B" },
  ],
  ollama: [],
};

function providerIcon(provider: string) {
  switch (provider) {
    case "openai":
      return <Zap size={16} className="text-green-500" />;
    case "anthropic":
      return <Brain size={16} className="text-orange-500" />;
    case "google":
      return <Zap size={16} className="text-blue-500" />;
    case "groq":
      return <Zap size={16} className="text-purple-500" />;
    case "ollama":
      return <Zap size={16} className="text-muted" />;
    default:
      return <Zap size={16} />;
  }
}

function statusBadge(status: string) {
  switch (status) {
    case "ok":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-success-surface text-success">
          <CheckCircle2 size={10} />
          OK
        </span>
      );
    case "error":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-danger-surface text-danger">
          <AlertCircle size={10} />
          Erro
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-hover text-muted">
          <HelpCircle size={10} />
          Nao testado
        </span>
      );
  }
}

export function LLMProvidersSection() {
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [defaultModalId, setDefaultModalId] = useState<string | null>(null);

  // Form state
  const [formProvider, setFormProvider] = useState<LLMProviderType>("openai");
  const [formModelId, setFormModelId] = useState("");
  const [formName, setFormName] = useState("");
  const [formApiKey, setFormApiKey] = useState("");
  const [formBaseUrl, setFormBaseUrl] = useState("");
  const [formTested, setFormTested] = useState(false);
  const [formTestLoading, setFormTestLoading] = useState(false);
  const [formSaving, setFormSaving] = useState(false);

  async function fetchProviders() {
    try {
      const data = await listLLMProviders();
      setProviders(data);
    } catch {
      // Ignore errors on first load (table may not exist yet)
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchProviders();
  }, []);

  function openAddModal() {
    setEditingId(null);
    setFormProvider("openai");
    setFormModelId(PROVIDER_MODELS.openai[0]?.id || "");
    setFormName(PROVIDER_MODELS.openai[0]?.label || "");
    setFormApiKey("");
    setFormBaseUrl("");
    setFormTested(false);
    setModalOpen(true);
  }

  function openEditModal(p: LLMProvider) {
    setEditingId(p.id);
    setFormProvider(p.provider);
    setFormModelId(p.model_id);
    setFormName(p.name);
    setFormApiKey("");
    setFormBaseUrl(p.base_url || "");
    setFormTested(true); // already exists, skip test requirement
    setModalOpen(true);
  }

  function handleProviderChange(provider: LLMProviderType) {
    setFormProvider(provider);
    const models = PROVIDER_MODELS[provider];
    if (models && models.length > 0) {
      setFormModelId(models[0].id);
      setFormName(models[0].label);
    } else {
      setFormModelId("");
      setFormName("");
    }
    setFormTested(false);
  }

  function handleModelChange(modelId: string) {
    setFormModelId(modelId);
    const model = PROVIDER_MODELS[formProvider]?.find((m) => m.id === modelId);
    if (model) setFormName(model.label);
    setFormTested(false);
  }

  async function handleTestInModal() {
    if (!formApiKey && formProvider !== "ollama") {
      toast.error("Insira a API key antes de testar");
      return;
    }
    setFormTestLoading(true);
    try {
      const result = await testLLMConnection({
        provider: formProvider,
        model_id: formModelId,
        api_key: formApiKey || undefined,
        base_url: formBaseUrl || undefined,
      });

      if (result.status === "ok") {
        toast.success(`Conexao OK — ${result.latency_ms}ms`);
        setFormTested(true);
      } else {
        toast.error(`Erro: ${result.error}`);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao testar");
    } finally {
      setFormTestLoading(false);
    }
  }

  async function handleSave() {
    if (!formName.trim() || !formModelId.trim()) {
      toast.error("Preencha nome e modelo");
      return;
    }
    setFormSaving(true);
    try {
      if (editingId) {
        const data: Record<string, string> = { name: formName, model_id: formModelId };
        if (formApiKey) data.api_key = formApiKey;
        if (formBaseUrl) data.base_url = formBaseUrl;
        await updateLLMProvider(editingId, data);
        toast.success("Provedor atualizado");
      } else {
        await createLLMProvider({
          name: formName,
          provider: formProvider,
          model_id: formModelId,
          api_key: formApiKey || undefined,
          base_url: formBaseUrl || undefined,
        });
        toast.success("Provedor adicionado");
      }
      setModalOpen(false);
      await fetchProviders();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao salvar");
    } finally {
      setFormSaving(false);
    }
  }

  async function handleTest(id: string) {
    setTestingId(id);
    try {
      const result = await testLLMProvider(id);
      if (result.status === "ok") {
        toast.success(`Conexao OK — ${result.latency_ms}ms`);
      } else {
        toast.error(`Erro: ${result.error}`);
      }
      await fetchProviders();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao testar");
    } finally {
      setTestingId(null);
    }
  }

  async function handleSetDefault(id: string) {
    try {
      await setDefaultLLMProvider(id);
      toast.success("Modelo padrao atualizado");
      setDefaultModalId(null);
      await fetchProviders();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao definir padrao");
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteLLMProvider(id);
      toast.success("Provedor removido");
      await fetchProviders();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao remover");
    }
  }

  const defaultProvider = providers.find((p) => p.is_default);
  const defaultModalProvider = providers.find((p) => p.id === defaultModalId);

  return (
    <div className="rounded-xl border border-border bg-card-bg p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-accent-surface">
            <Brain size={18} className="text-accent" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">Modelos de IA</h2>
            <p className="text-sm text-muted">
              Gerencie provedores e modelos LLM usados pelo Memora.
            </p>
          </div>
        </div>
        <button
          onClick={openAddModal}
          className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors"
        >
          <Plus size={14} />
          Adicionar modelo
        </button>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-muted py-4">
          <Loader2 size={16} className="animate-spin" />
          Carregando...
        </div>
      ) : providers.length === 0 ? (
        <div className="text-sm text-muted py-4 text-center">
          Nenhum provedor configurado. Adicione um modelo para comecar.
        </div>
      ) : (
        <div className="space-y-3">
          {providers.map((p) => (
            <div
              key={p.id}
              className={cn(
                "flex items-center gap-4 p-4 rounded-lg border transition-colors",
                p.is_default
                  ? "border-accent/30 bg-accent-surface/30"
                  : "border-border hover:border-border"
              )}
            >
              <div className="shrink-0">{providerIcon(p.provider)}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-sm font-medium truncate">{p.name}</span>
                  {p.is_default && (
                    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-semibold rounded-full bg-accent text-white">
                      <Star size={8} />
                      Padrao
                    </span>
                  )}
                  {statusBadge(p.last_test_status)}
                </div>
                <div className="flex items-center gap-2 text-xs text-muted">
                  <span className="capitalize">{p.provider}</span>
                  <span>·</span>
                  <span className="font-mono">{p.model_id}</span>
                  {p.api_key_masked && (
                    <>
                      <span>·</span>
                      <span>Key: {p.api_key_masked}</span>
                    </>
                  )}
                </div>
                {p.last_tested_at && (
                  <p className="text-[11px] text-muted mt-0.5">
                    Testado em {new Date(p.last_tested_at).toLocaleString("pt-BR")}
                    {p.last_test_error && (
                      <span className="text-danger ml-1">— {p.last_test_error}</span>
                    )}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button
                  onClick={() => handleTest(p.id)}
                  disabled={testingId === p.id}
                  className="px-2 py-1 text-xs rounded-lg border border-border hover:bg-hover transition-colors disabled:opacity-50"
                  title="Testar conexao"
                >
                  {testingId === p.id ? (
                    <Loader2 size={12} className="animate-spin" />
                  ) : (
                    "Testar"
                  )}
                </button>
                <button
                  onClick={() => openEditModal(p)}
                  className="p-1.5 rounded-lg hover:bg-hover text-muted hover:text-foreground transition-colors"
                  title="Editar"
                >
                  <Pencil size={13} />
                </button>
                {!p.is_default && (
                  <button
                    onClick={() => setDefaultModalId(p.id)}
                    className="p-1.5 rounded-lg hover:bg-hover text-muted hover:text-accent transition-colors"
                    title="Definir como padrao"
                  >
                    <Star size={13} />
                  </button>
                )}
                {!p.is_default && (
                  <button
                    onClick={() => handleDelete(p.id)}
                    className="p-1.5 rounded-lg hover:bg-danger-surface text-muted hover:text-danger transition-colors"
                    title="Remover"
                  >
                    <Trash2 size={13} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add/Edit Modal */}
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editingId ? "Editar modelo" : "Adicionar modelo"}
      >
        <div className="space-y-4">
          {!editingId && (
            <div>
              <label className="block text-sm font-medium mb-1">Provedor</label>
              <select
                value={formProvider}
                onChange={(e) => handleProviderChange(e.target.value as LLMProviderType)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground"
              >
                {PROVIDER_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {formProvider !== "ollama" && PROVIDER_MODELS[formProvider]?.length > 0 ? (
            <div>
              <label className="block text-sm font-medium mb-1">Modelo</label>
              <select
                value={formModelId}
                onChange={(e) => handleModelChange(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground"
              >
                {PROVIDER_MODELS[formProvider].map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.label} ({m.id})
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <div>
              <label className="block text-sm font-medium mb-1">Model ID</label>
              <input
                type="text"
                value={formModelId}
                onChange={(e) => { setFormModelId(e.target.value); setFormTested(false); }}
                placeholder="ex: llama3.2"
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground"
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium mb-1">Nome amigavel</label>
            <input
              type="text"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              placeholder="Ex: Claude Haiku"
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground"
            />
          </div>

          {formProvider !== "ollama" && (
            <div>
              <label className="block text-sm font-medium mb-1">
                API Key {editingId && <span className="text-muted font-normal">(deixe vazio para manter a atual)</span>}
              </label>
              <input
                type="password"
                value={formApiKey}
                onChange={(e) => { setFormApiKey(e.target.value); setFormTested(false); }}
                placeholder={editingId ? "••••••••" : "sk-..."}
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground font-mono"
              />
            </div>
          )}

          {formProvider === "ollama" && (
            <div>
              <label className="block text-sm font-medium mb-1">URL base</label>
              <input
                type="text"
                value={formBaseUrl}
                onChange={(e) => { setFormBaseUrl(e.target.value); setFormTested(false); }}
                placeholder="http://localhost:11434"
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card-bg text-foreground font-mono"
              />
            </div>
          )}

          <div className="flex items-center justify-between pt-2">
            {!editingId && (
              <button
                onClick={handleTestInModal}
                disabled={formTestLoading}
                className="inline-flex items-center gap-2 px-3 py-2 text-sm rounded-lg border border-border hover:bg-hover transition-colors disabled:opacity-50"
              >
                {formTestLoading ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Zap size={14} />
                )}
                Testar conexao
              </button>
            )}
            <div className="flex items-center gap-2 ml-auto">
              <button
                onClick={() => setModalOpen(false)}
                className="px-4 py-2 text-sm rounded-lg border border-border hover:bg-hover transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleSave}
                disabled={formSaving || (!editingId && !formTested)}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors disabled:opacity-50"
              >
                {formSaving && <Loader2 size={14} className="animate-spin" />}
                {editingId ? "Salvar" : "Adicionar"}
              </button>
            </div>
          </div>
          {!editingId && !formTested && (
            <p className="text-xs text-muted">Teste a conexao antes de salvar.</p>
          )}
        </div>
      </Modal>

      {/* Set Default confirmation */}
      <Modal
        open={!!defaultModalId}
        onClose={() => setDefaultModalId(null)}
        title="Definir modelo padrao"
      >
        <p className="text-sm text-muted mb-4">
          Definir <strong className="text-foreground">{defaultModalProvider?.name}</strong> como
          modelo padrao para todos os usuarios?
          {defaultProvider && (
            <span>
              {" "}
              O padrao atual ({defaultProvider.name}) sera substituido.
            </span>
          )}
        </p>
        <div className="flex justify-end gap-3">
          <button
            onClick={() => setDefaultModalId(null)}
            className="px-4 py-2 text-sm rounded-lg border border-border hover:bg-hover transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={() => defaultModalId && handleSetDefault(defaultModalId)}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors"
          >
            Confirmar
          </button>
        </div>
      </Modal>
    </div>
  );
}
