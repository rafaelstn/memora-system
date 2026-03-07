"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Search, AlertTriangle, FileCode, BookOpen, History,
  ChevronDown, ChevronUp, ArrowRight, Loader2,
} from "lucide-react";
import toast from "react-hot-toast";
import { useAuth } from "@/lib/hooks/useAuth";
import { startImpactAnalysis, getImpactAnalysis, listImpactHistory, listRepos } from "@/lib/api";
import type { ImpactAnalysis, ImpactFinding, RiskLevel } from "@/lib/types";
import { ExportPDFButton } from "@/components/ui/export-pdf-button";

const riskColors: Record<RiskLevel, string> = {
  low: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  medium: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  high: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  critical: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
};

const riskLabels: Record<RiskLevel, string> = {
  low: "BAIXO", medium: "MEDIO", high: "ALTO", critical: "CRITICO",
};

const typeIcons: Record<string, string> = {
  dependency: "dep", business_rule: "regra", pattern_break: "padrao", similar_change: "hist",
};

const typeLabels: Record<string, string> = {
  dependency: "Dependencias",
  business_rule: "Regras de Negocio",
  pattern_break: "Quebras de Padrao",
  similar_change: "Historico",
};

const steps = [
  "Identificando arquivos afetados...",
  "Mapeando dependencias...",
  "Verificando regras de negocio...",
  "Consultando historico de mudancas...",
  "Calculando risco...",
];

export default function ImpactPage() {
  const { user } = useAuth();
  const router = useRouter();

  const [repos, setRepos] = useState<{ name: string }[]>([]);
  const [selectedRepo, setSelectedRepo] = useState("");
  const [description, setDescription] = useState("");
  const [files, setFiles] = useState<string[]>([]);
  const [fileInput, setFileInput] = useState("");

  const [analyzing, setAnalyzing] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [result, setResult] = useState<ImpactAnalysis | null>(null);
  const [history, setHistory] = useState<ImpactAnalysis[]>([]);

  const [expandedTypes, setExpandedTypes] = useState<Set<string>>(new Set(["dependency", "business_rule"]));
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const stepRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (stepRef.current) clearInterval(stepRef.current);
    };
  }, []);

  useEffect(() => {
    if (!user || !["admin", "dev"].includes(user.role)) return;
    listRepos()
      .then((data) => {
        setRepos(Array.isArray(data) ? data : []);
        if (data.length > 0) setSelectedRepo(data[0].name);
      })
      .catch((e: unknown) => { console.error("Erro ao carregar repos:", e); });

    loadHistory();
  }, [user]);

  async function loadHistory() {
    try {
      const h = await listImpactHistory();
      setHistory(h.analyses);
    } catch (e: unknown) {
      console.error("Erro ao carregar historico:", e);
    }
  }

  async function handleAnalyze() {
    if (!description.trim() || !selectedRepo) return;
    setAnalyzing(true);
    setResult(null);
    setCurrentStep(0);

    try {
      const { analysis_id } = await startImpactAnalysis({
        change_description: description,
        repo_name: selectedRepo,
        affected_files: files.length > 0 ? files : undefined,
      });

      // Animate steps
      if (stepRef.current) clearInterval(stepRef.current);
      let step = 0;
      stepRef.current = setInterval(() => {
        step++;
        if (step < steps.length) setCurrentStep(step);
        else { clearInterval(stepRef.current!); stepRef.current = null; }
      }, 2000);

      // Poll for result
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(async () => {
        try {
          const data = await getImpactAnalysis(analysis_id);
          if (data.status === "completed" || data.status === "failed") {
            clearInterval(pollRef.current!); pollRef.current = null;
            if (stepRef.current) { clearInterval(stepRef.current); stepRef.current = null; }
            setResult(data);
            setAnalyzing(false);
            loadHistory();
            if (data.status === "failed") toast.error("Analise falhou");
          }
        } catch (e: unknown) {
          console.error("Erro ao verificar status da analise:", e);
        }
      }, 3000);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao iniciar analise");
      setAnalyzing(false);
    }
  }

  function addFile() {
    if (fileInput.trim() && !files.includes(fileInput.trim())) {
      setFiles([...files, fileInput.trim()]);
      setFileInput("");
    }
  }

  function removeFile(f: string) {
    setFiles(files.filter((x) => x !== f));
  }

  function toggleType(t: string) {
    const next = new Set(expandedTypes);
    if (next.has(t)) next.delete(t); else next.add(t);
    setExpandedTypes(next);
  }

  async function loadFromHistory(id: string) {
    try {
      const data = await getImpactAnalysis(id);
      setResult(data);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Erro ao carregar analise");
    }
  }

  if (!user || !["admin", "dev"].includes(user.role)) {
    return <div className="p-8 text-muted">Acesso restrito.</div>;
  }

  // Group findings by type
  const findingsByType: Record<string, ImpactFinding[]> = {};
  for (const f of result?.findings || []) {
    if (!findingsByType[f.finding_type]) findingsByType[f.finding_type] = [];
    findingsByType[f.finding_type].push(f);
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Analise de Impacto</h1>

      <div className="flex gap-6 flex-col lg:flex-row">
        {/* Left: Form + History */}
        <div className="w-full lg:w-[40%] space-y-6">
          {/* Repo select */}
          <select
            value={selectedRepo}
            onChange={(e) => setSelectedRepo(e.target.value)}
            className="w-full text-sm border border-border rounded-lg px-3 py-2 bg-card"
          >
            {repos.map((r) => (
              <option key={r.name} value={r.name}>{r.name}</option>
            ))}
          </select>

          {/* Description */}
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={5}
            className="w-full text-sm border border-border rounded-lg px-3 py-3 bg-card resize-none"
            placeholder="Descreva a mudanca que voce quer fazer...&#10;&#10;Ex: Quero alterar a funcao de calculo de desconto em services/pricing.py para adicionar uma nova faixa de desconto para clientes corporativos"
          />

          {/* Files tags */}
          <div>
            <label className="text-xs text-muted block mb-1">Arquivos que vou alterar (opcional)</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={fileInput}
                onChange={(e) => setFileInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addFile()}
                className="flex-1 text-sm border border-border rounded-lg px-3 py-1.5 bg-card"
                placeholder="caminho/arquivo.py"
              />
              <button onClick={addFile} className="px-3 py-1.5 text-sm rounded-lg border border-border hover:bg-hover">
                +
              </button>
            </div>
            {files.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {files.map((f) => (
                  <span key={f} className="inline-flex items-center gap-1 text-xs bg-hover rounded-full px-2.5 py-1">
                    {f}
                    <button onClick={() => removeFile(f)} className="text-muted hover:text-foreground">&times;</button>
                  </span>
                ))}
              </div>
            )}
          </div>

          <button
            onClick={handleAnalyze}
            disabled={analyzing || !description.trim()}
            className="w-full py-2.5 rounded-lg bg-accent-surface text-accent-text font-medium text-sm disabled:opacity-40"
          >
            {analyzing ? "Analisando..." : "Analisar Impacto"}
          </button>

          {/* History */}
          {history.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-muted mb-2 flex items-center gap-2">
                <History size={14} /> Historico
              </h3>
              <div className="space-y-2">
                {history.slice(0, 10).map((h) => (
                  <button
                    key={h.id}
                    onClick={() => loadFromHistory(h.id)}
                    className="w-full text-left p-3 rounded-lg border border-border hover:bg-hover/50 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      {h.risk_level && (
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${riskColors[h.risk_level]}`}>
                          {riskLabels[h.risk_level]}
                        </span>
                      )}
                      <span className="text-xs text-muted">{h.repo_name}</span>
                    </div>
                    <p className="text-sm mt-1 truncate">{h.change_description}</p>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: Result */}
        <div className="flex-1 min-w-0">
          {/* Initial state */}
          {!analyzing && !result && (
            <div className="flex flex-col items-center justify-center h-64 text-muted">
              <Search size={48} className="mb-4 opacity-30" />
              <p className="text-sm">Descreva sua mudanca e clique em Analisar</p>
            </div>
          )}

          {/* Analyzing */}
          {analyzing && (
            <div className="space-y-3 p-6">
              {steps.map((step, i) => (
                <div key={i} className={`flex items-center gap-3 transition-opacity ${i <= currentStep ? "opacity-100" : "opacity-30"}`}>
                  {i < currentStep ? (
                    <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center">
                      <span className="text-white text-xs">&#10003;</span>
                    </div>
                  ) : i === currentStep ? (
                    <Loader2 size={20} className="animate-spin text-accent-text" />
                  ) : (
                    <div className="w-5 h-5 rounded-full border-2 border-border" />
                  )}
                  <span className="text-sm">{step}</span>
                </div>
              ))}
            </div>
          )}

          {/* Result */}
          {result && result.status === "completed" && (
            <div className="space-y-6">
              {/* Risk header */}
              <div className="rounded-xl border border-border p-6">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-muted">Nivel de risco:</span>
                    {result.risk_level && (
                      <span className={`px-3 py-1 rounded-full text-sm font-bold ${riskColors[result.risk_level]}`}>
                        {riskLabels[result.risk_level]}
                      </span>
                    )}
                  </div>
                  <ExportPDFButton
                    endpoint={`/api/impact/${result.id}/report/pdf`}
                    filename={`impact-${result.id}.pdf`}
                    size="sm"
                  />
                </div>
                {result.risk_summary && (
                  <p className="text-sm text-muted leading-relaxed">{result.risk_summary}</p>
                )}
              </div>

              {/* Findings by type */}
              {Object.entries(findingsByType).map(([type, findings]) => (
                <div key={type} className="rounded-xl border border-border overflow-hidden">
                  <button
                    onClick={() => toggleType(type)}
                    className="w-full flex items-center justify-between px-5 py-3 hover:bg-hover/30"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold">{typeLabels[type] || type}</span>
                      <span className="text-xs text-muted">({findings.length})</span>
                    </div>
                    {expandedTypes.has(type) ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </button>

                  {expandedTypes.has(type) && (
                    <div className="border-t border-border divide-y divide-border">
                      {findings.map((f) => (
                        <div key={f.id} className="px-5 py-4 space-y-2">
                          <div className="flex items-center gap-2">
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${riskColors[f.severity]}`}>
                              {f.severity.toUpperCase()}
                            </span>
                            <span className="text-sm font-medium">{f.title}</span>
                          </div>
                          <p className="text-sm text-muted">{f.description}</p>
                          {f.file_path && (
                            <p className="text-xs text-muted">Arquivo: {f.file_path}</p>
                          )}
                          <div className="bg-hover/50 rounded-lg p-3">
                            <p className="text-xs font-medium text-muted mb-1">Recomendacao:</p>
                            <p className="text-sm">{f.recommendation}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}

              {(result.findings?.length || 0) === 0 && (
                <div className="text-center py-8 text-muted text-sm">
                  Nenhum finding identificado. A mudanca parece segura.
                </div>
              )}

              {/* Action buttons */}
              <div className="flex gap-3">
                <button
                  onClick={() => router.push(`/dashboard/codegen`)}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-accent-surface text-accent-text text-sm font-medium"
                >
                  Gerar codigo considerando esses riscos <ArrowRight size={14} />
                </button>
              </div>
            </div>
          )}

          {result && result.status === "failed" && (
            <div className="text-center py-8">
              <AlertTriangle size={32} className="mx-auto mb-3 text-red-500" />
              <p className="text-sm text-muted">A analise falhou. Tente novamente.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
