"use client";

import { useState, useEffect, useCallback } from "react";
import {
  RefreshCw,
  Loader2,
  Building2,
  Mail,
  CheckCircle2,
  XCircle,
  Clock,
  Crown,
  Zap,
  Users,
  Ban,
} from "lucide-react";
import toast from "react-hot-toast";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ---------- Types ---------- */

interface OrgPlan {
  org_id: string;
  org_name: string;
  plan: string;
  is_active: boolean;
  trial_expires_at: string | null;
  notes: string | null;
  created_at: string;
}

interface ContactRequest {
  id: string;
  org_id: string;
  org_name: string | null;
  name: string;
  email: string;
  reason: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

/* ---------- Styles ---------- */

const PLAN_STYLES: Record<string, string> = {
  pro_trial: "bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300",
  pro: "bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-300",
  enterprise: "bg-purple-100 text-purple-700 dark:bg-purple-500/15 dark:text-purple-300",
  customer: "bg-orange-100 text-orange-700 dark:bg-orange-500/15 dark:text-orange-300",
  inactive: "bg-gray-100 text-gray-500 dark:bg-gray-500/15 dark:text-gray-500",
};

const PLAN_LABELS: Record<string, string> = {
  pro_trial: "PRO Trial",
  pro: "PRO",
  enterprise: "Enterprise",
  customer: "Customer",
  free: "Free",
};

/* ---------- Helpers ---------- */

async function getAuthHeaders(): Promise<Record<string, string>> {
  const { getAccessToken } = await import("@/lib/auth");
  const token = await getAccessToken();
  const headers: Record<string, string> = { "ngrok-skip-browser-warning": "true" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `API error: ${res.status}`);
  }
  return res.json();
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function trialStatus(org: OrgPlan): { label: string; style: string } {
  if (!org.is_active) return { label: "Inativo", style: PLAN_STYLES.inactive };
  if (!org.trial_expires_at) return { label: "Ativo", style: PLAN_STYLES.pro };
  const exp = new Date(org.trial_expires_at);
  const now = new Date();
  const diffDays = Math.ceil((exp.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return { label: "Trial expirado", style: PLAN_STYLES.inactive };
  if (diffDays <= 3) return { label: `${diffDays}d restantes`, style: "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300" };
  return { label: `${diffDays}d restantes`, style: PLAN_STYLES.pro_trial };
}

/* ---------- Component ---------- */

export default function PlanosPage() {
  const [tab, setTab] = useState<"orgs" | "contacts">("orgs");
  const [orgs, setOrgs] = useState<OrgPlan[]>([]);
  const [contacts, setContacts] = useState<ContactRequest[]>([]);
  const [loadingOrgs, setLoadingOrgs] = useState(true);
  const [loadingContacts, setLoadingContacts] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const unreadCount = contacts.filter((c) => !c.is_read).length;

  /* --- Fetch --- */

  const fetchOrgs = useCallback(async () => {
    try {
      const data = await apiFetch<OrgPlan[]>("/api/admin/plan/all");
      setOrgs(data);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao carregar organizacoes");
    } finally {
      setLoadingOrgs(false);
    }
  }, []);

  const fetchContacts = useCallback(async () => {
    try {
      const data = await apiFetch<ContactRequest[]>("/api/admin/plan/contacts?unread_only=false");
      setContacts(data);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao carregar contatos");
    } finally {
      setLoadingContacts(false);
    }
  }, []);

  useEffect(() => {
    fetchOrgs();
    fetchContacts();
  }, [fetchOrgs, fetchContacts]);

  /* --- Actions --- */

  async function updatePlan(orgId: string, plan: string) {
    const key = `${orgId}-${plan}`;
    setActionLoading(key);
    try {
      await apiFetch(`/api/admin/plan/${orgId}`, {
        method: "PUT",
        body: JSON.stringify({ plan, is_active: true, notes: "" }),
      });
      toast.success(`Plano atualizado para ${plan.toUpperCase()}`);
      await fetchOrgs();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao atualizar plano");
    } finally {
      setActionLoading(null);
    }
  }

  async function extendTrial(orgId: string) {
    const key = `${orgId}-extend`;
    setActionLoading(key);
    try {
      await apiFetch(`/api/admin/plan/${orgId}/extend-trial`, {
        method: "POST",
        body: JSON.stringify({ days: 7 }),
      });
      toast.success("Trial estendido em 7 dias");
      await fetchOrgs();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao estender trial");
    } finally {
      setActionLoading(null);
    }
  }

  async function deactivate(orgId: string) {
    const key = `${orgId}-deactivate`;
    setActionLoading(key);
    try {
      await apiFetch(`/api/admin/plan/${orgId}/deactivate`, {
        method: "POST",
      });
      toast.success("Organizacao desativada");
      await fetchOrgs();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao desativar");
    } finally {
      setActionLoading(null);
    }
  }

  async function markAsRead(contactId: string) {
    const key = `contact-${contactId}`;
    setActionLoading(key);
    try {
      await apiFetch(`/api/admin/plan/contacts/${contactId}/read`, {
        method: "POST",
      });
      setContacts((prev) =>
        prev.map((c) => (c.id === contactId ? { ...c, is_read: true } : c)),
      );
      toast.success("Marcado como lido");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao marcar como lido");
    } finally {
      setActionLoading(null);
    }
  }

  /* --- Action button helper --- */

  function ActionBtn({
    label,
    loadingKey,
    onClick,
    icon: Icon,
    variant = "default",
  }: {
    label: string;
    loadingKey: string;
    onClick: () => void;
    icon: React.ComponentType<{ size?: number; className?: string }>;
    variant?: "default" | "danger" | "accent";
  }) {
    const isLoading = actionLoading === loadingKey;
    const base = "inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed";
    const variants = {
      default: "border border-border hover:bg-hover text-foreground",
      danger: "border border-red-300 dark:border-red-500/30 hover:bg-red-50 dark:hover:bg-red-500/10 text-red-600 dark:text-red-400",
      accent: "bg-accent hover:bg-accent-dark text-white",
    };
    return (
      <button
        onClick={onClick}
        disabled={!!actionLoading}
        className={cn(base, variants[variant])}
      >
        {isLoading ? <Loader2 size={12} className="animate-spin" /> : <Icon size={12} />}
        {label}
      </button>
    );
  }

  /* --- Render --- */

  return (
    <div className="p-5 lg:p-8 space-y-6">
      {/* Header */}
      <div className="pt-2">
        <h1 className="text-xl font-semibold">Gestao de Planos</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        <button
          onClick={() => setTab("orgs")}
          className={cn(
            "px-4 py-2.5 text-sm font-medium border-b-2 transition-colors",
            tab === "orgs"
              ? "border-accent text-accent"
              : "border-transparent text-muted hover:text-foreground",
          )}
        >
          <span className="inline-flex items-center gap-2">
            <Building2 size={15} />
            Organizacoes
          </span>
        </button>
        <button
          onClick={() => setTab("contacts")}
          className={cn(
            "px-4 py-2.5 text-sm font-medium border-b-2 transition-colors",
            tab === "contacts"
              ? "border-accent text-accent"
              : "border-transparent text-muted hover:text-foreground",
          )}
        >
          <span className="inline-flex items-center gap-2">
            <Mail size={15} />
            Contatos
            {unreadCount > 0 && (
              <span className="ml-1 px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-red-500 text-white">
                {unreadCount}
              </span>
            )}
          </span>
        </button>
      </div>

      {/* Tab: Organizacoes */}
      {tab === "orgs" && (
        <div className="rounded-lg border border-border bg-card-bg overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-border">
            <h2 className="text-lg font-semibold">Organizacoes</h2>
            <button
              onClick={() => { setLoadingOrgs(true); fetchOrgs(); }}
              className="inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg border border-border hover:bg-hover text-muted hover:text-foreground transition-colors"
            >
              <RefreshCw size={14} />
              Atualizar
            </button>
          </div>

          {loadingOrgs ? (
            <div className="flex items-center justify-center gap-2 px-6 py-12 text-muted text-sm">
              <Loader2 size={16} className="animate-spin" />
              Carregando...
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-border bg-hover">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">
                      Organizacao
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">
                      Plano Atual
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">
                      Status Trial
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">
                      Expiracao
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted uppercase tracking-wide">
                      Acoes
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {orgs.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-sm text-muted">
                        Nenhuma organizacao encontrada.
                      </td>
                    </tr>
                  )}
                  {orgs.map((org) => {
                    const status = trialStatus(org);
                    return (
                      <tr key={org.org_id} className="hover:bg-hover">
                        <td className="px-4 py-3 text-sm font-medium">
                          {org.org_name}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={cn(
                              "px-2 py-0.5 rounded-full text-[11px] font-semibold",
                              PLAN_STYLES[org.plan] || PLAN_STYLES.inactive,
                            )}
                          >
                            {PLAN_LABELS[org.plan] || org.plan}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={cn(
                              "px-2 py-0.5 rounded-full text-[11px] font-semibold",
                              status.style,
                            )}
                          >
                            {status.label}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-muted">
                          {org.trial_expires_at
                            ? formatDate(org.trial_expires_at)
                            : "—"}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-1.5">
                            <ActionBtn
                              label="Ativar PRO"
                              loadingKey={`${org.org_id}-pro`}
                              onClick={() => updatePlan(org.org_id, "pro")}
                              icon={Zap}
                              variant="accent"
                            />
                            <ActionBtn
                              label="Enterprise"
                              loadingKey={`${org.org_id}-enterprise`}
                              onClick={() => updatePlan(org.org_id, "enterprise")}
                              icon={Crown}
                            />
                            <ActionBtn
                              label="Customer"
                              loadingKey={`${org.org_id}-customer`}
                              onClick={() => updatePlan(org.org_id, "customer")}
                              icon={Users}
                            />
                            <ActionBtn
                              label="Estender +7d"
                              loadingKey={`${org.org_id}-extend`}
                              onClick={() => extendTrial(org.org_id)}
                              icon={Clock}
                            />
                            <ActionBtn
                              label="Desativar"
                              loadingKey={`${org.org_id}-deactivate`}
                              onClick={() => deactivate(org.org_id)}
                              icon={Ban}
                              variant="danger"
                            />
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab: Contatos */}
      {tab === "contacts" && (
        <div className="rounded-lg border border-border bg-card-bg overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-border">
            <h2 className="text-lg font-semibold">Solicitacoes de contato</h2>
            <button
              onClick={() => { setLoadingContacts(true); fetchContacts(); }}
              className="inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg border border-border hover:bg-hover text-muted hover:text-foreground transition-colors"
            >
              <RefreshCw size={14} />
              Atualizar
            </button>
          </div>

          {loadingContacts ? (
            <div className="flex items-center justify-center gap-2 px-6 py-12 text-muted text-sm">
              <Loader2 size={16} className="animate-spin" />
              Carregando...
            </div>
          ) : (
            <div className="divide-y divide-border">
              {contacts.length === 0 && (
                <div className="px-6 py-8 text-center text-sm text-muted">
                  Nenhuma solicitacao de contato.
                </div>
              )}
              {contacts.map((contact) => (
                <div
                  key={contact.id}
                  className={cn(
                    "px-6 py-4 hover:bg-hover transition-colors",
                    !contact.is_read && "bg-accent/5",
                  )}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0 space-y-1.5">
                      <div className="flex items-center gap-3 flex-wrap">
                        <span className="text-sm font-medium">{contact.name}</span>
                        <span className="text-xs text-muted">{contact.email}</span>
                        {contact.org_name && (
                          <span className="text-xs text-muted">
                            <Building2 size={11} className="inline mr-1" />
                            {contact.org_name}
                          </span>
                        )}
                        <span className="text-xs text-muted">
                          {formatDate(contact.created_at)}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className={cn(
                            "px-2 py-0.5 rounded-full text-[11px] font-semibold",
                            "bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300",
                          )}
                        >
                          {contact.reason}
                        </span>
                        <span
                          className={cn(
                            "px-2 py-0.5 rounded-full text-[11px] font-semibold",
                            contact.is_read
                              ? "bg-gray-100 text-gray-500 dark:bg-gray-500/15 dark:text-gray-400"
                              : "bg-yellow-100 text-yellow-700 dark:bg-yellow-500/15 dark:text-yellow-300",
                          )}
                        >
                          {contact.is_read ? "Lido" : "Nao lido"}
                        </span>
                      </div>
                      {contact.message && (
                        <p className="text-sm text-muted leading-relaxed mt-1">
                          {contact.message}
                        </p>
                      )}
                    </div>
                    <div className="shrink-0">
                      {!contact.is_read && (
                        <button
                          onClick={() => markAsRead(contact.id)}
                          disabled={!!actionLoading}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-accent hover:bg-accent-dark text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                          {actionLoading === `contact-${contact.id}` ? (
                            <Loader2 size={12} className="animate-spin" />
                          ) : (
                            <CheckCircle2 size={12} />
                          )}
                          Marcar como lido
                        </button>
                      )}
                      {contact.is_read && (
                        <span className="inline-flex items-center gap-1 text-xs text-muted">
                          <CheckCircle2 size={12} />
                          Lido
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
