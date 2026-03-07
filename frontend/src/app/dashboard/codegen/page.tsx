"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import {
  Code2,
  Loader2,
  Copy,
  Download,
  ChevronDown,
  ChevronRight,
  Check,
  Search,
  Scale,
  GitBranch,
  Terminal,
  RefreshCw,
  Clock,
} from "lucide-react";
import toast from "react-hot-toast";
import { useAuth } from "@/lib/hooks/useAuth";
import { listRepos, generateCodeStream, getCodeGenHistory, getCodeGenDetail } from "@/lib/api";
import type { CodeGenHistoryItem, CodeGenDetail } from "@/lib/types";

const REQUEST_TYPES = [
  { value: "function", label: "Funcao completa" },
  { value: "endpoint", label: "Endpoint de API (FastAPI)" },
  { value: "component", label: "Componente React" },
  { value: "script", label: "Script utilitario" },
  { value: "class", label: "Classe/servico" },
];

interface ContextInfo {
  similar_code_count: number;
  rules_count: number;
  has_patterns: boolean;
  decisions_count: number;
  has_env_vars: boolean;
}

export default function CodegenPage() {
  const { user } = useAuth();
  const [repos, setRepos] = useState<{ name: string }[]>([]);
  const [selectedRepo, setSelectedRepo] = useState("");
  const [description, setDescription] = useState("");
  const [requestType, setRequestType] = useState("function");
  const [filePath, setFilePath] = useState("");
  const [useContext, setUseContext] = useState(true);

  // Generation state
  const [generating, setGenerating] = useState(false);
  const [contextInfo, setContextInfo] = useState<ContextInfo | null>(null);
  const [streamedCode, setStreamedCode] = useState("");
  const [genId, setGenId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Context detail
  const [showContext, setShowContext] = useState(false);
  const [contextDetail, setContextDetail] = useState<Record<string, unknown> | null>(null);
  const [explanation, setExplanation] = useState("");

  // History
  const [history, setHistory] = useState<CodeGenHistoryItem[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  // Refine
  const [refineMode, setRefineMode] = useState(false);
  const [refineInput, setRefineInput] = useState("");

  const codeRef = useRef<HTMLPreElement>(null);
  const copiedTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (copiedTimeoutRef.current) clearTimeout(copiedTimeoutRef.current);
    };
  }, []);

  useEffect(() => {
    if (!user) return;
    listRepos().then((r) => setRepos(r)).catch((e: unknown) => { console.error("Erro ao carregar repos:", e); });
    getCodeGenHistory().then((r) => setHistory(r.generations)).catch((e: unknown) => { console.error("Erro ao carregar historico:", e); });
  }, [user]);

  const handleGenerate = useCallback(async () => {
    if (!description.trim() || !selectedRepo) return;
    setGenerating(true);
    setStreamedCode("");
    setContextInfo(null);
    setError(null);
    setGenId(null);
    setContextDetail(null);
    setExplanation("");
    setRefineMode(false);

    const finalDesc = refineMode && refineInput
      ? `${description}\n\n[REFINAMENTO]: ${refineInput}`
      : description;

    try {
      await generateCodeStream(
        {
          description: finalDesc,
          type: requestType,
          repo_name: selectedRepo,
          file_path: filePath || undefined,
          use_context: useContext,
        },
        (event) => {
          if (event.type === "context") {
            setContextInfo({
              similar_code_count: event.similar_code_count as number,
              rules_count: event.rules_count as number,
              has_patterns: event.has_patterns as boolean,
              decisions_count: event.decisions_count as number,
              has_env_vars: event.has_env_vars as boolean,
            });
            if (event.gen_id) setGenId(event.gen_id as string);
          } else if (event.type === "token") {
            setStreamedCode((prev) => prev + (event.content as string));
          } else if (event.type === "error") {
            setError(event.message as string);
          } else if (event.type === "done") {
            if (event.gen_id) setGenId(event.gen_id as string);
          }
        },
      );

      // Load saved detail for context + explanation
      // Small delay to let DB save complete
      await new Promise((r) => setTimeout(r, 500));
      if (genId) {
        try {
          const detail = await getCodeGenDetail(genId);
          setContextDetail(detail.context_used);
          setExplanation(detail.explanation || "");
        } catch (e: unknown) {
          console.error("Erro ao carregar detalhes da geracao:", e);
        }
      }

      // Refresh history
      getCodeGenHistory().then((r) => setHistory(r.generations)).catch((e: unknown) => { console.error("Erro ao atualizar historico:", e); });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Erro desconhecido");
    } finally {
      setGenerating(false);
    }
  }, [description, selectedRepo, requestType, filePath, useContext, refineMode, refineInput, genId]);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(streamedCode);
    setCopied(true);
    if (copiedTimeoutRef.current) clearTimeout(copiedTimeoutRef.current);
    copiedTimeoutRef.current = setTimeout(() => setCopied(false), 2000);
  }, [streamedCode]);

  const handleDownload = useCallback(() => {
    const ext = requestType === "component" ? ".tsx" : ".py";
    const blob = new Blob([streamedCode], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `generated${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  }, [streamedCode, requestType]);

  const loadHistoryItem = useCallback(async (id: string) => {
    try {
      const detail = await getCodeGenDetail(id);
      setDescription(detail.request_description);
      setRequestType(detail.request_type);
      setSelectedRepo(detail.repo_name);
      setFilePath(detail.file_path || "");
      setStreamedCode(detail.generated_code || "");
      setExplanation(detail.explanation || "");
      setContextDetail(detail.context_used);
      setGenId(detail.id);
      setShowHistory(false);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Erro ao carregar item do historico");
    }
  }, []);

  if (!user || (user.role !== "admin" && user.role !== "dev")) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm text-muted">Acesso restrito a admin e dev.</p>
      </div>
    );
  }

  return (
    <div className="h-full flex">
      {/* History sidebar */}
      <div
        className={`border-r border-border bg-card-bg transition-all ${showHistory ? "w-72" : "w-0"} overflow-hidden`}
      >
        <div className="p-3 border-b border-border flex items-center justify-between">
          <span className="text-sm font-medium">Historico</span>
          <button onClick={() => setShowHistory(false)} className="text-xs text-muted hover:text-foreground">
            Fechar
          </button>
        </div>
        <div className="overflow-y-auto h-[calc(100%-3rem)]">
          {history.map((item) => (
            <button
              key={item.id}
              onClick={() => loadHistoryItem(item.id)}
              className="w-full text-left p-3 border-b border-border hover:bg-hover transition-colors"
            >
              <p className="text-xs font-medium truncate">{item.title}</p>
              <p className="text-[10px] text-muted mt-1">
                {item.request_type} &middot; {item.created_at?.slice(0, 10)}
              </p>
            </button>
          ))}
          {history.length === 0 && (
            <p className="text-xs text-muted p-3">Nenhuma geracao ainda.</p>
          )}
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        {/* Left panel — Form */}
        <div className="lg:w-[45%] border-r border-border p-6 overflow-y-auto">
          <div className="flex items-center gap-3 mb-6">
            <Code2 className="h-6 w-6 text-accent" />
            <h1 className="text-2xl font-bold">Geracao de Codigo</h1>
            <button
              onClick={() => setShowHistory(!showHistory)}
              className="ml-auto text-xs text-muted hover:text-foreground flex items-center gap-1"
            >
              <Clock className="h-3 w-3" /> Historico
            </button>
          </div>

          {/* Repo selector */}
          <label className="text-xs font-medium text-muted block mb-1">Repositorio</label>
          <select
            className="w-full mb-4 px-3 py-2 rounded-lg border border-border bg-card-bg text-sm"
            value={selectedRepo}
            onChange={(e) => setSelectedRepo(e.target.value)}
          >
            <option value="">Selecione um repositorio</option>
            {repos.map((r) => (
              <option key={r.name} value={r.name}>{r.name}</option>
            ))}
          </select>

          {/* Description */}
          <label className="text-xs font-medium text-muted block mb-1">Descreva o que voce precisa implementar</label>
          <textarea
            className="w-full mb-4 px-3 py-2 rounded-lg border border-border bg-card-bg text-sm min-h-[120px] resize-y"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Ex: Preciso de uma funcao que calcula o desconto progressivo para pedidos, considerando o tipo do cliente e o valor total"
          />

          {/* Type selector */}
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="text-xs font-medium text-muted block mb-1">Tipo de entrega</label>
              <select
                className="w-full px-3 py-2 rounded-lg border border-border bg-card-bg text-sm"
                value={requestType}
                onChange={(e) => setRequestType(e.target.value)}
              >
                {REQUEST_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-muted block mb-1">Arquivo de destino (opcional)</label>
              <input
                className="w-full px-3 py-2 rounded-lg border border-border bg-card-bg text-sm"
                value={filePath}
                onChange={(e) => setFilePath(e.target.value)}
                placeholder="Ex: app/services/pricing.py"
              />
            </div>
          </div>

          {/* Context toggle */}
          <label className="flex items-center gap-2 mb-6 cursor-pointer">
            <input
              type="checkbox"
              checked={useContext}
              onChange={(e) => setUseContext(e.target.checked)}
              className="rounded border-border"
            />
            <span className="text-sm">Buscar contexto automaticamente</span>
          </label>

          {/* Generate button */}
          <button
            onClick={handleGenerate}
            disabled={generating || !description.trim() || !selectedRepo}
            className="w-full py-2.5 rounded-lg bg-accent text-white font-medium text-sm hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {generating ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Gerando...
              </>
            ) : (
              <>
                <Code2 className="h-4 w-4" /> Gerar codigo
              </>
            )}
          </button>
        </div>

        {/* Right panel — Output */}
        <div className="lg:w-[55%] p-6 overflow-y-auto">
          {/* Context steps */}
          {contextInfo && (
            <div className="mb-4 p-4 rounded-xl border border-border bg-card-bg">
              <p className="text-sm font-medium mb-3 flex items-center gap-2">
                <Search className="h-4 w-4 text-accent" />
                Contexto do sistema
              </p>
              <div className="space-y-1.5">
                <ContextStep
                  icon={<Code2 className="h-3 w-3" />}
                  label={`Codigo similar encontrado: ${contextInfo.similar_code_count} trechos`}
                  done={contextInfo.similar_code_count > 0}
                />
                <ContextStep
                  icon={<Scale className="h-3 w-3" />}
                  label={`Regras de negocio: ${contextInfo.rules_count} regras`}
                  done={contextInfo.rules_count > 0}
                />
                <ContextStep
                  icon={<GitBranch className="h-3 w-3" />}
                  label="Padroes do time: identificados"
                  done={contextInfo.has_patterns}
                />
                <ContextStep
                  icon={<Terminal className="h-3 w-3" />}
                  label={`Decisoes anteriores: ${contextInfo.decisions_count} decisoes`}
                  done={contextInfo.decisions_count > 0}
                />
                <ContextStep
                  icon={<Terminal className="h-3 w-3" />}
                  label="Variaveis de ambiente"
                  done={contextInfo.has_env_vars}
                />
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-400">
              {error}
            </div>
          )}

          {/* Generated code */}
          {(streamedCode || generating) && (
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-medium">Codigo gerado</p>
                {streamedCode && !generating && (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleCopy}
                      className="text-xs text-muted hover:text-foreground flex items-center gap-1"
                    >
                      {copied ? <Check className="h-3 w-3 text-green-400" /> : <Copy className="h-3 w-3" />}
                      {copied ? "Copiado" : "Copiar"}
                    </button>
                    <button
                      onClick={handleDownload}
                      className="text-xs text-muted hover:text-foreground flex items-center gap-1"
                    >
                      <Download className="h-3 w-3" /> Baixar
                    </button>
                  </div>
                )}
              </div>
              <pre
                ref={codeRef}
                className="p-4 rounded-xl border border-border bg-[#1e1e2e] text-[#cdd6f4] text-xs font-mono overflow-x-auto whitespace-pre-wrap max-h-[500px] overflow-y-auto"
              >
                {streamedCode}
                {generating && <span className="animate-pulse">|</span>}
              </pre>
            </div>
          )}

          {/* Explanation */}
          {explanation && !generating && (
            <div className="mb-4 p-4 rounded-xl border border-border bg-card-bg">
              <p className="text-sm font-medium mb-2">Por que o codigo foi gerado assim:</p>
              <div className="text-xs text-muted whitespace-pre-wrap">{explanation}</div>
            </div>
          )}

          {/* Context detail collapsible */}
          {contextDetail && !generating && (
            <div className="mb-4">
              <button
                onClick={() => setShowContext(!showContext)}
                className="flex items-center gap-1 text-xs text-muted hover:text-foreground"
              >
                {showContext ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                Contexto usado na geracao
              </button>
              {showContext && (
                <pre className="mt-2 p-3 rounded-lg border border-border bg-card-bg text-[10px] text-muted overflow-x-auto max-h-60 overflow-y-auto">
                  {JSON.stringify(contextDetail, null, 2)}
                </pre>
              )}
            </div>
          )}

          {/* Refine */}
          {streamedCode && !generating && (
            <div className="mb-4">
              {!refineMode ? (
                <button
                  onClick={() => setRefineMode(true)}
                  className="text-xs text-accent hover:underline flex items-center gap-1"
                >
                  <RefreshCw className="h-3 w-3" /> Refinar codigo
                </button>
              ) : (
                <div className="space-y-2">
                  <label className="text-xs font-medium text-muted block">O que voce quer ajustar?</label>
                  <textarea
                    className="w-full px-3 py-2 rounded-lg border border-border bg-card-bg text-sm min-h-[60px] resize-y"
                    value={refineInput}
                    onChange={(e) => setRefineInput(e.target.value)}
                    placeholder="Ex: Adicione validacao de email antes do calculo"
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={handleGenerate}
                      disabled={!refineInput.trim()}
                      className="px-3 py-1.5 rounded-lg bg-accent text-white text-xs font-medium hover:bg-accent/90 disabled:opacity-50"
                    >
                      Refinar
                    </button>
                    <button
                      onClick={() => { setRefineMode(false); setRefineInput(""); }}
                      className="px-3 py-1.5 rounded-lg border border-border text-xs hover:bg-hover"
                    >
                      Cancelar
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Empty state */}
          {!streamedCode && !generating && !error && (
            <div className="flex flex-col items-center justify-center h-full text-center py-20">
              <Code2 className="h-12 w-12 text-muted mb-3" />
              <p className="text-sm font-medium">Nenhum codigo gerado</p>
              <p className="text-xs text-muted mt-1">
                Descreva o que precisa implementar e clique em &quot;Gerar codigo&quot;.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ContextStep({ icon, label, done }: { icon: React.ReactNode; label: string; done: boolean }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      {done ? (
        <Check className="h-3 w-3 text-green-400" />
      ) : (
        <span className="h-3 w-3 text-muted">{icon}</span>
      )}
      <span className={done ? "text-foreground" : "text-muted"}>{label}</span>
    </div>
  );
}
