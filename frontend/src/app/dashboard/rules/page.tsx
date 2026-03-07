"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import toast from "react-hot-toast";
import {
  Calculator,
  Shield,
  Lock,
  Plug,
  GitBranch,
  Search,
  Loader2,
  RefreshCw,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  X,
  Play,
  CheckCircle2,
  Eye,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/hooks/useAuth";
import {
  listRules,
  listRepos,
  searchRules,
  getRule,
  extractRules,
  getExtractStatus,
  simulateRule,
  listRuleAlerts,
  acknowledgeRuleAlert,
} from "@/lib/api";
import type {
  BusinessRuleSummary,
  BusinessRuleDetail,
  RuleChangeAlert,
  RuleType,
  RuleExtractStatus,
} from "@/lib/types";

const RULE_TYPE_CONFIG: Record<RuleType, { icon: typeof Calculator; label: string; color: string }> = {
  calculation: { icon: Calculator, label: "Calculos", color: "text-blue-500" },
  validation: { icon: Shield, label: "Validacoes", color: "text-green-500" },
  permission: { icon: Lock, label: "Permissoes", color: "text-purple-500" },
  integration: { icon: Plug, label: "Integracoes", color: "text-orange-500" },
  conditional: { icon: GitBranch, label: "Condicionais", color: "text-cyan-500" },
};

export default function RulesPage() {
  const { role } = useAuth();
  const canManage = role === "admin" || role === "dev";

  const [repos, setRepos] = useState<Array<{ name: string }>>([]);
  const [selectedRepo, setSelectedRepo] = useState<string>("");
  const [rules, setRules] = useState<BusinessRuleSummary[]>([]);
  const [alerts, setAlerts] = useState<RuleChangeAlert[]>([]);
  const [status, setStatus] = useState<RuleExtractStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [extracting, setExtracting] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<BusinessRuleSummary[] | null>(null);
  const [selectedRule, setSelectedRule] = useState<BusinessRuleDetail | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [collapsedTypes, setCollapsedTypes] = useState<Set<string>>(new Set());
  const [simInputs, setSimInputs] = useState<Record<string, string>>({});
  const [simResult, setSimResult] = useState<string | null>(null);
  const [simulating, setSimulating] = useState(false);
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load repos
  useEffect(() => {
    listRepos().then((r: any[]) => {
      setRepos(r);
      if (r.length > 0) setSelectedRepo(r[0].name);
    }).catch(() => {});
  }, []);

  // Load rules when repo changes
  const loadData = useCallback(async () => {
    if (!selectedRepo) return;
    setLoading(true);
    try {
      const [rulesResp, statusResp] = await Promise.all([
        listRules(selectedRepo),
        getExtractStatus(selectedRepo),
      ]);
      setRules(rulesResp.rules);
      setStatus(statusResp);

      if (canManage) {
        const alertsResp = await listRuleAlerts(selectedRepo);
        setAlerts(alertsResp);
      }
    } catch {}
    setLoading(false);
  }, [selectedRepo, canManage]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Debounced search
  useEffect(() => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    if (!searchQuery || searchQuery.length < 2) {
      setSearchResults(null);
      return;
    }
    searchTimerRef.current = setTimeout(async () => {
      try {
        const results = await searchRules(searchQuery, selectedRepo || undefined);
        setSearchResults(results);
      } catch {
        setSearchResults([]);
      }
    }, 500);
  }, [searchQuery, selectedRepo]);

  async function handleExtract() {
    if (!selectedRepo || !canManage) return;
    setExtracting(true);
    try {
      await extractRules(selectedRepo);
      toast.success("Extracao iniciada em background");
      // Poll for completion
      const interval = setInterval(async () => {
        const s = await getExtractStatus(selectedRepo);
        setStatus(s);
        if (s.total_rules > (status?.total_rules ?? 0)) {
          clearInterval(interval);
          setExtracting(false);
          await loadData();
          toast.success(`${s.total_rules} regras extraidas!`);
        }
      }, 5000);
      setTimeout(() => {
        clearInterval(interval);
        setExtracting(false);
      }, 120000);
    } catch (e: any) {
      toast.error(e.message || "Erro ao extrair regras");
      setExtracting(false);
    }
  }

  async function handleSelectRule(ruleId: string) {
    try {
      const detail = await getRule(ruleId);
      setSelectedRule(detail);
      setDrawerOpen(true);
      setSimResult(null);
      setSimInputs({});
    } catch (e: any) {
      toast.error(e.message);
    }
  }

  async function handleSimulate() {
    if (!selectedRule) return;
    setSimulating(true);
    try {
      const result = await simulateRule(selectedRule.id, simInputs);
      setSimResult(result.result);
    } catch (e: any) {
      toast.error(e.message || "Erro na simulacao");
    }
    setSimulating(false);
  }

  async function handleAcknowledgeAlert(alertId: string) {
    try {
      await acknowledgeRuleAlert(alertId);
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
      toast.success("Alerta reconhecido");
    } catch (e: any) {
      toast.error(e.message);
    }
  }

  function toggleType(type: string) {
    setCollapsedTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }

  // Group rules by type
  const displayRules = searchResults ?? rules;
  const grouped = displayRules.reduce<Record<string, BusinessRuleSummary[]>>((acc, rule) => {
    const t = rule.rule_type;
    if (!acc[t]) acc[t] = [];
    acc[t].push(rule);
    return acc;
  }, {});

  return (
    <div className="flex h-full">
      {/* Main content */}
      <div className={cn("flex-1 overflow-y-auto p-6", drawerOpen && "mr-[480px]")}>
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Regras de Negocio</h1>
            <p className="text-sm text-muted mt-0.5">
              Regras extraidas automaticamente do codigo em linguagem simples
            </p>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={selectedRepo}
              onChange={(e) => setSelectedRepo(e.target.value)}
              className="px-3 py-2 rounded-lg border border-border bg-background text-sm"
            >
              {repos.map((r) => (
                <option key={r.name} value={r.name}>{r.name}</option>
              ))}
            </select>
            {canManage && (
              <button
                onClick={handleExtract}
                disabled={extracting || !selectedRepo}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-dark transition-colors disabled:opacity-50"
              >
                {extracting ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                Extrair regras
              </button>
            )}
          </div>
        </div>

        {/* Stats cards */}
        {status && (
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="p-4 rounded-xl border border-border bg-card-bg">
              <p className="text-2xl font-bold">{status.total_rules}</p>
              <p className="text-xs text-muted">Regras extraidas</p>
            </div>
            <div className={cn(
              "p-4 rounded-xl border bg-card-bg",
              (status.changed_since_push ?? 0) > 0 ? "border-warning/50" : "border-border",
            )}>
              <p className="text-2xl font-bold">{status.changed_since_push ?? 0}</p>
              <p className="text-xs text-muted">Alteradas no ultimo push</p>
            </div>
            <div className="p-4 rounded-xl border border-border bg-card-bg">
              <p className="text-sm font-medium">
                {status.last_extracted
                  ? new Date(status.last_extracted).toLocaleDateString("pt-BR")
                  : "Nunca"}
              </p>
              <p className="text-xs text-muted">Ultima extracao</p>
            </div>
          </div>
        )}

        {/* Alerts banner */}
        {alerts.length > 0 && (
          <div className="mb-6 p-4 rounded-xl bg-warning-surface border border-warning/30">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-warning shrink-0" />
              <p className="text-sm font-medium flex-1">
                {alerts.length} regra(s) foram alteradas no ultimo push
              </p>
            </div>
            <div className="mt-2 space-y-1">
              {alerts.slice(0, 3).map((a) => (
                <div key={a.id} className="flex items-center gap-2 text-xs">
                  <span className="text-muted">{a.change_type === "modified" ? "Modificada" : "Removida"}:</span>
                  <span className="font-medium">{a.rule_title}</span>
                  {canManage && (
                    <button
                      onClick={() => handleAcknowledgeAlert(a.id)}
                      className="ml-auto text-accent hover:text-accent-dark text-xs"
                    >
                      Reconhecer
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Search */}
        <div className="relative mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Buscar regra... Ex: como e calculado o desconto?"
            className="w-full pl-10 pr-4 py-3 rounded-xl border border-border bg-background text-sm placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent/50"
          />
          {searchQuery && (
            <button
              onClick={() => { setSearchQuery(""); setSearchResults(null); }}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Rules list */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-accent" />
          </div>
        ) : displayRules.length === 0 ? (
          <div className="text-center py-16">
            <Calculator className="h-12 w-12 text-muted mx-auto mb-3" />
            <p className="text-sm font-medium">
              {searchQuery ? "Nenhuma regra encontrada" : "Nenhuma regra extraida"}
            </p>
            <p className="text-xs text-muted mt-1">
              {searchQuery ? "Tente outra busca" : "Clique em 'Extrair regras' para comecar"}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {Object.entries(grouped).map(([type, typeRules]) => {
              const config = RULE_TYPE_CONFIG[type as RuleType] || RULE_TYPE_CONFIG.conditional;
              const Icon = config.icon;
              const isCollapsed = collapsedTypes.has(type);

              return (
                <div key={type}>
                  <button
                    onClick={() => toggleType(type)}
                    className="flex items-center gap-2 mb-2 text-sm font-medium text-muted hover:text-foreground transition-colors"
                  >
                    {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    <Icon className={cn("h-4 w-4", config.color)} />
                    {config.label} ({typeRules.length})
                  </button>

                  {!isCollapsed && (
                    <div className="space-y-2 ml-6">
                      {typeRules.map((rule) => (
                        <button
                          key={rule.id}
                          onClick={() => handleSelectRule(rule.id)}
                          className={cn(
                            "w-full text-left p-4 rounded-xl border transition-colors hover:border-accent/40",
                            rule.changed_in_last_push
                              ? "border-warning/40 bg-warning-surface/30"
                              : "border-border bg-card-bg hover:bg-hover",
                          )}
                        >
                          <div className="flex items-start gap-2">
                            <Icon className={cn("h-4 w-4 mt-0.5 shrink-0", config.color)} />
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <p className="text-sm font-medium">{rule.title}</p>
                                {rule.changed_in_last_push && (
                                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-warning text-black font-medium">
                                    Alterada
                                  </span>
                                )}
                              </div>
                              <p className="text-xs text-muted mt-1 line-clamp-2">
                                &quot;{rule.plain_english}&quot;
                              </p>
                              <div className="flex items-center gap-3 mt-2 text-xs text-muted">
                                {rule.affected_files?.[0] && (
                                  <span className="font-mono">{rule.affected_files[0]}</span>
                                )}
                                <span>Confianca: {Math.round(rule.confidence * 100)}%</span>
                              </div>
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Detail drawer */}
      {drawerOpen && selectedRule && (
        <div className="fixed right-0 top-0 h-full w-[480px] bg-card-bg border-l border-border overflow-y-auto z-50 shadow-xl">
          <div className="p-6">
            {/* Header */}
            <div className="flex items-start justify-between mb-6">
              <div>
                <span className={cn(
                  "text-xs font-medium px-2 py-0.5 rounded-full",
                  `bg-${RULE_TYPE_CONFIG[selectedRule.rule_type as RuleType]?.color?.replace("text-", "")}/10`,
                  RULE_TYPE_CONFIG[selectedRule.rule_type as RuleType]?.color,
                )}>
                  {RULE_TYPE_CONFIG[selectedRule.rule_type as RuleType]?.label || selectedRule.rule_type}
                </span>
                <h2 className="text-lg font-bold mt-2">{selectedRule.title}</h2>
              </div>
              <button onClick={() => setDrawerOpen(false)} className="p-1 rounded-lg hover:bg-hover">
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Plain english */}
            <div className="p-4 rounded-xl bg-accent-surface border border-accent/20 mb-6">
              <p className="text-xs font-medium text-accent mb-1">Em linguagem simples</p>
              <p className="text-sm font-medium text-accent-text">{selectedRule.plain_english}</p>
            </div>

            {/* Technical description */}
            <div className="mb-6">
              <h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">Descricao tecnica</h3>
              <p className="text-sm text-foreground">{selectedRule.description}</p>
            </div>

            {/* Conditions */}
            {selectedRule.conditions && selectedRule.conditions.length > 0 && (
              <div className="mb-6">
                <h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">Condicoes</h3>
                <div className="space-y-2">
                  {selectedRule.conditions.map((c, i) => (
                    <div key={i} className="p-3 rounded-lg bg-hover text-sm font-mono">
                      {c.if && <p><span className="text-accent font-bold">SE</span> {c.if}</p>}
                      {c.and && <p><span className="text-accent font-bold">E</span> {c.and}</p>}
                      {c.then && <p><span className="text-success font-bold">ENTAO</span> {c.then}</p>}
                      {c.except && <p><span className="text-warning font-bold">EXCETO</span> {c.except}</p>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Files */}
            {selectedRule.affected_files && selectedRule.affected_files.length > 0 && (
              <div className="mb-6">
                <h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">Onde esta no codigo</h3>
                <div className="space-y-1">
                  {selectedRule.affected_files.map((f, i) => (
                    <p key={i} className="text-xs font-mono text-muted">{f}</p>
                  ))}
                </div>
              </div>
            )}

            {/* Change history */}
            {selectedRule.changes.length > 0 && (
              <div className="mb-6">
                <h3 className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">Historico de mudancas</h3>
                <div className="space-y-2">
                  {selectedRule.changes.map((c, i) => (
                    <div key={i} className="p-3 rounded-lg border border-border text-xs">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={cn(
                          "font-medium",
                          c.change_type === "modified" ? "text-warning" : "text-danger",
                        )}>
                          {c.change_type === "modified" ? "Modificada" : c.change_type === "removed" ? "Removida" : "Adicionada"}
                        </span>
                        <span className="text-muted">{c.detected_at ? new Date(c.detected_at).toLocaleDateString("pt-BR") : ""}</span>
                      </div>
                      {c.new_description && <p className="text-muted">{c.new_description}</p>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Simulator */}
            <div className="border-t border-border pt-6">
              <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                <Play className="h-4 w-4 text-accent" />
                Simular esta regra
              </h3>
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-muted">Valores de entrada (chave: valor)</label>
                  <textarea
                    value={Object.entries(simInputs).map(([k, v]) => `${k}: ${v}`).join("\n")}
                    onChange={(e) => {
                      const lines = e.target.value.split("\n");
                      const inputs: Record<string, string> = {};
                      for (const line of lines) {
                        const [k, ...rest] = line.split(":");
                        if (k?.trim()) inputs[k.trim()] = rest.join(":").trim();
                      }
                      setSimInputs(inputs);
                    }}
                    placeholder={"tipo_cliente: VIP\nvalor_pedido: 800\ncategoria: Premium"}
                    className="w-full mt-1 p-3 rounded-lg border border-border bg-background text-sm font-mono resize-none h-24 placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent/50"
                  />
                </div>
                <button
                  onClick={handleSimulate}
                  disabled={simulating || Object.keys(simInputs).length === 0}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-dark transition-colors disabled:opacity-50"
                >
                  {simulating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                  Simular
                </button>

                {simResult && (
                  <div className="p-4 rounded-xl bg-success-surface/50 border border-success/20">
                    <p className="text-xs font-medium text-success mb-2">Resultado da simulacao</p>
                    <div className="prose prose-sm max-w-none text-sm">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{simResult}</ReactMarkdown>
                    </div>
                  </div>
                )}

                {/* Past simulations */}
                {selectedRule.simulations.length > 0 && (
                  <div className="mt-4">
                    <p className="text-xs text-muted font-medium mb-2">Simulacoes anteriores</p>
                    {selectedRule.simulations.map((s) => (
                      <div key={s.id} className="p-3 rounded-lg border border-border text-xs mb-2">
                        <p className="text-muted mb-1">
                          {Object.entries(s.input_values as Record<string, unknown>).map(([k, v]) => `${k}=${v}`).join(", ")}
                        </p>
                        <p className="text-foreground line-clamp-2">{s.result}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
