"use client";

import { useState, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import {
  Shield,
  Zap,
  Loader2,
  RefreshCcw,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ChevronDown,
  ChevronUp,
  XCircle,
} from "lucide-react";
import {
  listSecurityScans,
  startSecurityScan,
  getSecurityScan,
  getSecurityFindings,
  getSecurityStats,
  startDASTScan,
  getDASTScan,
  getDASTFindings,
  listDASTScans,
} from "@/lib/api";
import type {
  SecurityScan,
  SecurityFinding,
  SecurityStats,
  DASTScan,
  DASTFinding,
} from "@/lib/types";
import { Modal } from "@/components/ui/modal";
import { ExportPDFButton } from "@/components/ui/export-pdf-button";

type SubTab = "audits" | "dast";

const PROBE_LABELS: Record<string, string> = {
  sql_injection: "SQL Injection",
  auth_bypass: "Auth Bypass",
  rate_limit: "Rate Limiting",
  cors: "CORS",
  security_headers: "Security Headers",
  idor: "IDOR",
  xss: "XSS",
  brute_force: "Forca Bruta",
  sensitive_exposure: "Exposicao de Dados",
  http_methods: "HTTP Methods",
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-500/10 text-red-600 border-red-500/30",
  high: "bg-orange-500/10 text-orange-600 border-orange-500/30",
  medium: "bg-yellow-500/10 text-yellow-600 border-yellow-500/30",
  low: "bg-blue-500/10 text-blue-600 border-blue-500/30",
  info: "bg-gray-500/10 text-gray-500 border-gray-500/30",
};

// ────────────── Auditorias Sub-tab ──────────────

function AuditsSubTab() {
  const [scans, setScans] = useState<SecurityScan[]>([]);
  const [stats, setStats] = useState<SecurityStats | null>(null);
  const [selectedScan, setSelectedScan] = useState<SecurityScan | null>(null);
  const [findings, setFindings] = useState<SecurityFinding[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [repoName, setRepoName] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  useEffect(() => {
    Promise.allSettled([
      listSecurityScans().then((r) => setScans(r.scans)),
      getSecurityStats().then(setStats),
    ]).finally(() => setLoading(false));
  }, []);

  const handleStartScan = async () => {
    if (!repoName.trim()) return;
    setScanning(true);
    try {
      const res = await startSecurityScan(repoName.trim());
      // Poll for completion
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(async () => {
        const scan = await getSecurityScan(res.scan_id);
        if (scan.status === "completed" || scan.status === "failed") {
          if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
          }
          setScanning(false);
          setSelectedScan(scan);
          if (scan.status === "completed") {
            const f = await getSecurityFindings(scan.id);
            setFindings(f.findings);
          }
          listSecurityScans().then((r) => setScans(r.scans));
        }
      }, 2000);
    } catch {
      setScanning(false);
    }
  };

  const loadFindings = async (scan: SecurityScan) => {
    setSelectedScan(scan);
    if (scan.status === "completed") {
      const f = await getSecurityFindings(scan.id);
      setFindings(f.findings);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center py-20 text-muted text-sm"><Loader2 size={16} className="animate-spin" /> Carregando...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="rounded-lg border border-border p-4">
            <p className="text-sm text-muted">Score medio</p>
            <p className={cn("text-3xl font-bold", stats.avg_score != null && stats.avg_score >= 80 ? "text-green-500" : stats.avg_score != null && stats.avg_score >= 60 ? "text-yellow-500" : "text-red-500")}>
              {stats.avg_score ?? "—"}
            </p>
          </div>
          <div className="rounded-lg border border-border p-4">
            <p className="text-sm text-muted">Scans recentes</p>
            <p className="text-3xl font-bold">{stats.recent_scans.length}</p>
          </div>
          <div className="rounded-lg border border-border p-4">
            <p className="text-sm text-muted">Findings criticos</p>
            <p className="text-3xl font-bold text-red-500">{stats.total_critical_findings}</p>
          </div>
        </div>
      )}

      {/* New scan */}
      <div className="rounded-lg border border-border p-4">
        <h3 className="text-sm font-semibold mb-3">Nova Auditoria</h3>
        <div className="flex gap-3">
          <input
            type="text"
            value={repoName}
            onChange={(e) => setRepoName(e.target.value)}
            placeholder="Nome do repositorio"
            className="flex-1 rounded-lg border border-border bg-transparent px-3 py-2 text-sm"
          />
          <button
            onClick={handleStartScan}
            disabled={scanning || !repoName.trim()}
            className="flex items-center gap-2 rounded-lg bg-accent-surface px-4 py-2 text-sm font-medium text-accent-text hover:opacity-90 disabled:opacity-50"
          >
            {scanning ? <Loader2 size={14} className="animate-spin" /> : <Shield size={14} />}
            Analisar
          </button>
        </div>
      </div>

      {/* Selected scan results */}
      {selectedScan && selectedScan.status === "completed" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h3 className="font-semibold">Resultado: {selectedScan.repo_name}</h3>
              <ExportPDFButton
                endpoint={`/api/security/scan/${selectedScan.id}/report/pdf`}
                filename={`security-${selectedScan.repo_name}.pdf`}
                size="sm"
              />
            </div>
            <span className={cn("text-2xl font-bold", (selectedScan.security_score ?? 0) >= 80 ? "text-green-500" : (selectedScan.security_score ?? 0) >= 60 ? "text-yellow-500" : "text-red-500")}>
              {selectedScan.security_score}/100
            </span>
          </div>
          <div className="grid grid-cols-4 gap-3 text-center text-sm">
            <div className="rounded-lg bg-red-500/10 p-2"><p className="text-red-500 font-bold">{selectedScan.critical_count}</p><p className="text-xs text-muted">Criticos</p></div>
            <div className="rounded-lg bg-orange-500/10 p-2"><p className="text-orange-500 font-bold">{selectedScan.high_count}</p><p className="text-xs text-muted">Altos</p></div>
            <div className="rounded-lg bg-yellow-500/10 p-2"><p className="text-yellow-500 font-bold">{selectedScan.medium_count}</p><p className="text-xs text-muted">Medios</p></div>
            <div className="rounded-lg bg-blue-500/10 p-2"><p className="text-blue-500 font-bold">{selectedScan.low_count}</p><p className="text-xs text-muted">Baixos</p></div>
          </div>
          <div className="space-y-2">
            {findings.map((f) => (
              <div key={f.id} className={cn("rounded-lg border p-4", SEVERITY_COLORS[f.severity])}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-semibold uppercase">{f.severity}</span>
                  <span className="text-xs text-muted">({f.scanner})</span>
                </div>
                <p className="text-sm font-medium">{f.title}</p>
                <p className="text-xs mt-1">{f.description}</p>
                {f.file_path && <p className="text-xs text-muted mt-1">{f.file_path}:{f.line_start}</p>}
                {f.recommendation && <p className="text-xs mt-2 opacity-80">{f.recommendation}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Scan history */}
      {scans.length > 0 && (
        <div className="rounded-lg border border-border divide-y divide-border">
          <div className="px-4 py-3 text-sm font-semibold">Historico de Auditorias</div>
          {scans.map((s) => (
            <div
              key={s.id}
              className="flex items-center justify-between px-4 py-3 hover:bg-hover cursor-pointer"
              onClick={() => loadFindings(s)}
            >
              <div className="flex items-center gap-3">
                <span className={cn("text-lg font-bold", (s.security_score ?? 0) >= 80 ? "text-green-500" : (s.security_score ?? 0) >= 60 ? "text-yellow-500" : "text-red-500")}>
                  {s.security_score ?? "—"}
                </span>
                <span className="text-sm">{s.repo_name}</span>
                <span className={cn("text-xs px-2 py-0.5 rounded-full", s.status === "completed" ? "bg-green-500/10 text-green-500" : s.status === "failed" ? "bg-red-500/10 text-red-500" : "bg-yellow-500/10 text-yellow-500")}>{s.status}</span>
              </div>
              <span className="text-xs text-muted">{new Date(s.created_at).toLocaleDateString("pt-BR")}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ────────────── DAST Sub-tab ──────────────

function DASTSubTab() {
  const [targetUrl, setTargetUrl] = useState("");
  const [targetEnv, setTargetEnv] = useState<"development" | "staging">("development");
  const [confirmed, setConfirmed] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [activeScan, setActiveScan] = useState<DASTScan | null>(null);
  const [dastFindings, setDastFindings] = useState<DASTFinding[]>([]);
  const [history, setHistory] = useState<DASTScan[]>([]);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");
  const dastPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (dastPollRef.current) clearInterval(dastPollRef.current);
    };
  }, []);

  // Tutorial collapse state
  const [tutorialOpen, setTutorialOpen] = useState(() => {
    if (typeof window === "undefined") return true;
    return localStorage.getItem("memora-dast-tutorial-seen") !== "true";
  });

  useEffect(() => {
    listDASTScans().then((r) => setHistory(r.scans)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const closeTutorial = () => {
    setTutorialOpen(false);
    localStorage.setItem("memora-dast-tutorial-seen", "true");
  };

  const handleStart = async () => {
    setShowConfirmModal(false);
    setStarting(true);
    setError("");
    try {
      const res = await startDASTScan({ target_url: targetUrl, target_env: targetEnv });
      // Poll
      if (dastPollRef.current) clearInterval(dastPollRef.current);
      dastPollRef.current = setInterval(async () => {
        try {
          const scan = await getDASTScan(res.scan_id);
          setActiveScan(scan);
          if (scan.status === "completed" || scan.status === "failed") {
            if (dastPollRef.current) {
              clearInterval(dastPollRef.current);
              dastPollRef.current = null;
            }
            setStarting(false);
            if (scan.status === "completed") {
              const f = await getDASTFindings(scan.id);
              setDastFindings(f.findings);
            }
            listDASTScans().then((r) => setHistory(r.scans));
          }
        } catch {
          if (dastPollRef.current) {
            clearInterval(dastPollRef.current);
            dastPollRef.current = null;
          }
          setStarting(false);
        }
      }, 3000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Erro ao iniciar scan");
      setStarting(false);
    }
  };

  const loadScanResult = async (scan: DASTScan) => {
    setActiveScan(scan);
    if (scan.status === "completed") {
      const f = await getDASTFindings(scan.id);
      setDastFindings(f.findings);
    }
  };

  const resetForm = () => {
    setActiveScan(null);
    setDastFindings([]);
    setTargetUrl("");
    setConfirmed(false);
  };

  const probeStatus = (probeType: string): "done" | "confirmed" | "warning" | "running" | "waiting" => {
    if (!activeScan || activeScan.status === "pending") return "waiting";
    const finding = dastFindings.find((f) => f.probe_type === probeType);
    if (!finding) {
      const probeIndex = Object.keys(PROBE_LABELS).indexOf(probeType);
      if (probeIndex < (activeScan.probes_completed || 0)) return "done";
      if (probeIndex === (activeScan.probes_completed || 0) && activeScan.status === "running") return "running";
      return "waiting";
    }
    if (finding.confirmed) return "confirmed";
    return "done";
  };

  if (loading) {
    return <div className="flex items-center justify-center py-20 text-muted text-sm"><Loader2 size={16} className="animate-spin" /></div>;
  }

  // Show result if scan completed
  if (activeScan && activeScan.status === "completed" && dastFindings.length > 0) {
    const confirmedFindings = dastFindings.filter((f) => f.confirmed);
    const infoFindings = dastFindings.filter((f) => !f.confirmed);
    const riskColors: Record<string, string> = { critical: "text-red-500", high: "text-orange-500", medium: "text-yellow-500", low: "text-green-500" };

    return (
      <div className="space-y-6">
        {/* Result header */}
        <div className="rounded-lg border border-border p-6">
          <div className="flex items-center gap-2 mb-2">
            <Zap size={18} className="text-amber-500" />
            <h3 className="font-semibold">Resultado do Teste Ativo</h3>
            <ExportPDFButton
              endpoint={`/api/security/dast/scan/${activeScan.id}/report/pdf`}
              filename={`dast-${activeScan.id}.pdf`}
              size="sm"
            />
          </div>
          <p className="text-sm text-muted mb-3">
            {activeScan.target_url} &bull; {activeScan.duration_seconds ? `${activeScan.duration_seconds}s` : ""}
          </p>
          <p className="text-lg font-bold">
            {activeScan.vulnerabilities_confirmed} vulnerabilidades confirmadas
          </p>
          {activeScan.risk_level && (
            <p className={cn("text-sm font-semibold mt-1", riskColors[activeScan.risk_level] || "text-muted")}>
              Risco: {activeScan.risk_level.toUpperCase()}
            </p>
          )}
          {activeScan.summary && <p className="text-sm mt-2 italic text-muted">&ldquo;{activeScan.summary}&rdquo;</p>}
          <div className="flex gap-3 mt-4">
            <button onClick={resetForm} className="flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-2 text-sm font-medium text-amber-600 hover:bg-amber-500/20">
              <Zap size={14} /> Novo Teste
            </button>
          </div>
        </div>

        {/* Confirmed findings */}
        {confirmedFindings.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-semibold">Vulnerabilidades Confirmadas</h4>
            {confirmedFindings.map((f) => (
              <div key={f.id} className={cn("rounded-lg border p-4", SEVERITY_COLORS[f.severity])}>
                <div className="flex items-center gap-2 mb-1">
                  <XCircle size={14} />
                  <span className="text-xs font-semibold uppercase">{f.severity}</span>
                  <span className="text-xs">&mdash; {PROBE_LABELS[f.probe_type] || f.probe_type}</span>
                </div>
                <p className="text-sm font-medium">{f.title}</p>
                <p className="text-xs mt-1">{f.description}</p>
                {f.payload_used && (
                  <div className="mt-2 rounded bg-black/5 dark:bg-white/5 px-3 py-2 text-xs font-mono">
                    Payload: {f.payload_used}
                  </div>
                )}
                {f.result && (
                  <div className="mt-1 rounded bg-black/5 dark:bg-white/5 px-3 py-2 text-xs font-mono">
                    Resposta: {f.result.slice(0, 300)}
                  </div>
                )}
                {f.recommendation && <p className="text-xs mt-2 opacity-80">Como corrigir: {f.recommendation}</p>}
              </div>
            ))}
          </div>
        )}

        {/* Info findings */}
        {infoFindings.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-muted">Testado — nenhum problema</h4>
            {infoFindings.map((f) => (
              <div key={f.id} className="flex items-center gap-3 rounded-lg border border-border p-3">
                <CheckCircle2 size={14} className="text-green-500 shrink-0" />
                <div>
                  <p className="text-sm">{PROBE_LABELS[f.probe_type] || f.probe_type}</p>
                  <p className="text-xs text-muted">{f.title}</p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* History */}
        {history.length > 1 && <DASTHistory history={history} onSelect={loadScanResult} />}
      </div>
    );
  }

  // Show progress if running
  if (activeScan && (activeScan.status === "running" || starting)) {
    return (
      <div className="space-y-6">
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Zap size={18} className="text-amber-500 animate-pulse" />
            <h3 className="font-semibold">Teste em execucao...</h3>
          </div>
          <div className="w-full h-2 rounded-full bg-border mb-4 overflow-hidden">
            <div
              className="h-full rounded-full bg-amber-500 transition-all"
              style={{ width: `${((activeScan.probes_completed || 0) / (activeScan.probes_total || 10)) * 100}%` }}
            />
          </div>
          <p className="text-sm text-muted mb-4">{activeScan.probes_completed || 0} / {activeScan.probes_total || 10} probes</p>
          <div className="space-y-2">
            {Object.entries(PROBE_LABELS).map(([key, label]) => {
              const status = probeStatus(key);
              return (
                <div key={key} className="flex items-center gap-3 text-sm">
                  {status === "done" && <CheckCircle2 size={14} className="text-green-500" />}
                  {status === "confirmed" && <XCircle size={14} className="text-red-500" />}
                  {status === "running" && <Zap size={14} className="text-amber-500 animate-pulse" />}
                  {status === "waiting" && <span className="w-3.5 h-3.5 rounded-full bg-border" />}
                  {status === "warning" && <AlertTriangle size={14} className="text-yellow-500" />}
                  <span className={cn(status === "waiting" ? "text-muted" : "")}>{label}</span>
                  {status === "running" && <span className="text-xs text-amber-500">testando...</span>}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  // Show form
  return (
    <div className="space-y-6">
      {/* Tutorial */}
      <div className="rounded-lg border border-border bg-card-bg overflow-hidden">
        <button
          onClick={() => tutorialOpen ? closeTutorial() : setTutorialOpen(true)}
          className="flex items-center justify-between w-full px-4 py-3 text-sm font-semibold hover:bg-hover"
        >
          <span>Como funciona o Teste Ativo</span>
          {tutorialOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
        {tutorialOpen && (
          <div className="px-4 pb-4 text-sm text-muted space-y-2">
            <p>O Teste Ativo envia requisicoes reais para a URL configurada e verifica se vulnerabilidades conhecidas existem de verdade.</p>
            <p>Diferente da Auditoria de Codigo — que analisa o codigo e suspeita de problemas — o Teste Ativo confirma se a vulnerabilidade e exploravel.</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-1 mt-3">
              {Object.values(PROBE_LABELS).map((label) => (
                <span key={label} className="flex items-center gap-1.5 text-xs">
                  <CheckCircle2 size={10} className="text-green-500 shrink-0" />
                  {label}
                </span>
              ))}
            </div>
            <p className="mt-2 text-xs">Os testes sao nao-destrutivos: nenhum dado e modificado, deletado ou corrompido.</p>
          </div>
        )}
      </div>

      {/* Warning */}
      <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4">
        <div className="flex items-start gap-3">
          <AlertTriangle size={18} className="text-amber-500 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-amber-600">ATENCAO — Leia antes de executar</p>
            <p className="text-sm mt-1">Execute APENAS em ambiente de desenvolvimento ou staging. NUNCA em producao.</p>
            <ul className="text-xs text-muted mt-2 space-y-1 list-disc list-inside">
              <li>Os testes geram requisicoes automaticas que podem aparecer nos logs do servidor</li>
              <li>O probe de Rate Limit envia 20 requisicoes seguidas ao endpoint de login</li>
              <li>O probe de SQL Injection envia payloads que podem acionar alertas de seguranca</li>
            </ul>
            <p className="text-xs text-muted mt-2">Em producao: use a Auditoria de Codigo (aba Auditorias) — ela analisa sem enviar requisicoes ao servidor.</p>
          </div>
        </div>
      </div>

      {/* Form */}
      <div className="rounded-lg border border-border p-6">
        <h3 className="flex items-center gap-2 text-sm font-semibold mb-4">
          <Zap size={14} className="text-amber-500" />
          Novo Teste Ativo
        </h3>
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-1 block">URL do ambiente alvo</label>
            <input
              type="url"
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              placeholder="http://localhost:8000"
              className="w-full rounded-lg border border-border bg-transparent px-3 py-2 text-sm"
            />
            <p className="text-xs text-muted mt-1">Insira a URL base da API ou aplicacao</p>
          </div>
          <div>
            <label className="text-sm font-medium mb-2 block">Ambiente</label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="radio" name="env" checked={targetEnv === "development"} onChange={() => setTargetEnv("development")} className="accent-amber-500" />
                Desenvolvimento
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="radio" name="env" checked={targetEnv === "staging"} onChange={() => setTargetEnv("staging")} className="accent-amber-500" />
                Staging
              </label>
            </div>
          </div>
          <label className="flex items-start gap-2 text-sm cursor-pointer">
            <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} className="accent-amber-500 mt-0.5" />
            <span>Confirmo que esta URL NAO e um ambiente de producao com dados reais de usuarios</span>
          </label>

          {error && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-600">{error}</div>
          )}

          <button
            onClick={() => setShowConfirmModal(true)}
            disabled={!confirmed || !targetUrl.trim() || starting}
            className="flex items-center gap-2 rounded-lg bg-amber-500 px-4 py-2.5 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Zap size={14} />
            Iniciar Teste Ativo
          </button>
        </div>
      </div>

      {/* History */}
      {history.length > 0 && <DASTHistory history={history} onSelect={loadScanResult} />}

      {/* Confirm Modal */}
      <Modal open={showConfirmModal} onClose={() => setShowConfirmModal(false)} title="Confirmar Teste Ativo">
        <div className="space-y-3">
          <p className="text-sm">Voce esta prestes a executar testes ativos em:</p>
          <p className="text-sm font-mono font-medium">{targetUrl}</p>
          <p className="text-sm text-muted">Ambiente: {targetEnv === "development" ? "Desenvolvimento" : "Staging"}</p>
          <p className="text-xs text-muted">O teste enviara requisicoes reais para esta URL e levara aproximadamente 2 a 5 minutos.</p>
          <div className="flex justify-end gap-3 pt-2">
            <button onClick={() => setShowConfirmModal(false)} className="px-4 py-2 text-sm rounded-lg border border-border hover:bg-hover">Cancelar</button>
            <button onClick={handleStart} className="flex items-center gap-2 rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-white hover:bg-amber-600">
              <Zap size={14} /> Confirmar e Iniciar
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

function DASTHistory({ history, onSelect }: { history: DASTScan[]; onSelect: (s: DASTScan) => void }) {
  const riskColors: Record<string, string> = { critical: "text-red-500", high: "text-orange-500", medium: "text-yellow-500", low: "text-green-500" };
  return (
    <div className="rounded-lg border border-border divide-y divide-border">
      <div className="px-4 py-3 text-sm font-semibold">Historico de Testes</div>
      {history.map((s) => (
        <div key={s.id} className="flex items-center justify-between px-4 py-3 hover:bg-hover cursor-pointer" onClick={() => onSelect(s)}>
          <div className="flex items-center gap-3">
            <Zap size={14} className="text-amber-500" />
            <span className="text-sm">{s.target_url}</span>
            <span className="text-xs text-muted">{s.vulnerabilities_confirmed} vulns</span>
            {s.risk_level && <span className={cn("text-xs font-semibold", riskColors[s.risk_level])}>{s.risk_level.toUpperCase()}</span>}
          </div>
          <span className="text-xs text-muted">{new Date(s.created_at).toLocaleDateString("pt-BR")}</span>
        </div>
      ))}
    </div>
  );
}

// ────────────── Main Security Tab ──────────────

export default function SecurityTab() {
  const [subTab, setSubTab] = useState<SubTab>("audits");

  return (
    <div className="space-y-6">
      {/* Sub-tabs */}
      <div className="flex items-center gap-1">
        <button
          onClick={() => setSubTab("audits")}
          className={cn(
            "px-4 py-2 text-sm font-medium rounded-lg transition-colors",
            subTab === "audits" ? "bg-accent-surface text-accent-text" : "text-muted hover:bg-hover",
          )}
        >
          Auditorias
        </button>
        <div className="w-px h-6 bg-border mx-1" />
        <button
          onClick={() => setSubTab("dast")}
          className={cn(
            "flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg border transition-colors",
            subTab === "dast"
              ? "bg-amber-500/10 text-amber-600 border-amber-500/30"
              : "text-muted hover:bg-hover border-transparent hover:border-amber-500/20",
          )}
        >
          <Zap size={14} />
          Teste Ativo
        </button>
      </div>

      {subTab === "audits" && <AuditsSubTab />}
      {subTab === "dast" && <DASTSubTab />}
    </div>
  );
}
