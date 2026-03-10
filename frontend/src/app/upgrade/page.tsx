"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import toast, { Toaster } from "react-hot-toast";
import {
  Crown,
  Building2,
  Sparkles,
  ArrowRight,
  LogOut,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type ContactReason = "upgrade_pro" | "enterprise" | "customer";

interface PlanInfo {
  trial_start?: string;
  trial_end?: string;
  status?: string;
}

interface UserProfile {
  name: string;
  email: string;
}

export default function UpgradePage() {
  const router = useRouter();
  const [plan, setPlan] = useState<PlanInfo | null>(null);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  // Contact form state
  const [showForm, setShowForm] = useState(false);
  const [contactReason, setContactReason] = useState<ContactReason>("upgrade_pro");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const { getAccessToken } = await import("@/lib/auth");
        const { fetchUserProfile } = await import("@/lib/auth");
        const token = await getAccessToken();

        const headers: Record<string, string> = {
          "Content-Type": "application/json",
          "ngrok-skip-browser-warning": "true",
        };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const [planRes, profile] = await Promise.all([
          fetch(`${API_BASE}/api/admin/plan`, { headers }).then((r) =>
            r.ok ? r.json() : null
          ),
          fetchUserProfile(),
        ]);

        setPlan(planRes);
        if (profile) setUser({ name: profile.name, email: profile.email });
      } catch {
        // silently handle — page works without data
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const { getAccessToken } = await import("@/lib/auth");
      const token = await getAccessToken();

      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "true",
      };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`${API_BASE}/api/admin/plan/contact`, {
        method: "POST",
        headers,
        body: JSON.stringify({ contact_reason: contactReason, message }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Erro ${res.status}`);
      }

      setSubmitted(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erro ao enviar contato";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleLogout() {
    const { signOut } = await import("@/lib/auth");
    await signOut();
    router.push("/auth/signin");
  }

  function openForm(reason: ContactReason) {
    setContactReason(reason);
    setShowForm(true);
    setSubmitted(false);
    setMessage("");
  }

  const formatDate = (d?: string) => {
    if (!d) return "—";
    return new Date(d).toLocaleDateString("pt-BR");
  };

  const plans = [
    {
      id: "upgrade_pro" as ContactReason,
      name: "Pro",
      icon: Crown,
      badge: "Recomendado",
      badgeColor: "bg-blue-500/20 text-blue-400 border-blue-500/30",
      borderColor: "border-blue-500/40 hover:border-blue-400/60",
      description:
        "Todos os modulos, multi-repo, multi-usuario. Infraestrutura Memora.",
    },
    {
      id: "enterprise" as ContactReason,
      name: "Enterprise",
      icon: Building2,
      badge: null,
      badgeColor: "",
      borderColor: "border-zinc-700 hover:border-zinc-600",
      description:
        "Banco de dados na sua infra. Compliance total. LGPD on-premise.",
    },
    {
      id: "customer" as ContactReason,
      name: "Customer",
      icon: Sparkles,
      badge: "Personalizado",
      badgeColor: "bg-purple-500/20 text-purple-400 border-purple-500/30",
      borderColor: "border-zinc-700 hover:border-zinc-600",
      description:
        "Implementacao personalizada. Modulos sob demanda.",
    },
  ];

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col items-center justify-center px-4 py-12">
      <Toaster position="top-right" />

      <div className="w-full max-w-4xl space-y-10">
        {/* Header */}
        <div className="text-center space-y-3">
          <h1 className="text-3xl font-bold text-white">Seu trial expirou</h1>
          <p className="text-zinc-400 text-lg">
            Escolha o plano ideal para continuar usando o Memora.
          </p>
        </div>

        {/* Trial summary */}
        {!loading && plan && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 text-center space-y-2">
            <p className="text-sm text-zinc-400">Periodo do trial</p>
            <p className="text-zinc-200 font-medium">
              {formatDate(plan.trial_start)} — {formatDate(plan.trial_end)}
            </p>
            {plan.status && (
              <span className="inline-block mt-1 text-xs px-2.5 py-0.5 rounded-full bg-red-500/15 text-red-400 border border-red-500/30">
                {plan.status}
              </span>
            )}
          </div>
        )}

        {/* Plan cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {plans.map((p) => {
            const Icon = p.icon;
            return (
              <div
                key={p.id}
                className={`relative bg-zinc-900 border rounded-xl p-6 flex flex-col gap-4 transition-colors ${p.borderColor}`}
              >
                {p.badge && (
                  <span
                    className={`absolute -top-3 left-4 text-xs font-medium px-2.5 py-0.5 rounded-full border ${p.badgeColor}`}
                  >
                    {p.badge}
                  </span>
                )}

                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-zinc-800">
                    <Icon className="w-5 h-5 text-zinc-300" />
                  </div>
                  <h2 className="text-lg font-semibold text-white">{p.name}</h2>
                </div>

                <p className="text-sm text-zinc-400 flex-1">{p.description}</p>

                <button
                  onClick={() => openForm(p.id)}
                  className="mt-auto flex items-center justify-center gap-2 w-full py-2.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-sm font-medium text-zinc-200 transition-colors cursor-pointer"
                >
                  Falar com a equipe
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            );
          })}
        </div>

        {/* Contact form */}
        {showForm && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 space-y-5">
            {submitted ? (
              <div className="text-center py-6 space-y-3">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-green-500/15 mb-2">
                  <Sparkles className="w-6 h-6 text-green-400" />
                </div>
                <p className="text-zinc-200 font-medium">
                  Recebemos seu contato.
                </p>
                <p className="text-zinc-400 text-sm">
                  Rafael entrara em contato em ate 24h.
                </p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <h3 className="text-lg font-semibold text-white">
                  Entrar em contato
                </h3>

                <input type="hidden" name="contact_reason" value={contactReason} />

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-sm text-zinc-400">Nome</label>
                    <input
                      type="text"
                      value={user?.name || ""}
                      readOnly
                      className="w-full px-3 py-2 rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm focus:outline-none"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-sm text-zinc-400">Email</label>
                    <input
                      type="email"
                      value={user?.email || ""}
                      readOnly
                      className="w-full px-3 py-2 rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm focus:outline-none"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-sm text-zinc-400">Mensagem</label>
                  <textarea
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    rows={4}
                    placeholder="Conte sobre sua necessidade..."
                    className="w-full px-3 py-2 rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm placeholder-zinc-500 focus:outline-none focus:border-zinc-600 resize-none"
                  />
                </div>

                <div className="flex items-center gap-3">
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-sm font-medium text-white transition-colors cursor-pointer"
                  >
                    {submitting ? "Enviando..." : "Enviar"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowForm(false)}
                    className="px-4 py-2.5 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 transition-colors cursor-pointer"
                  >
                    Cancelar
                  </button>
                </div>
              </form>
            )}
          </div>
        )}

        {/* Logout */}
        <div className="text-center pt-4">
          <button
            onClick={handleLogout}
            className="inline-flex items-center gap-2 text-sm text-zinc-500 hover:text-zinc-300 transition-colors cursor-pointer"
          >
            <LogOut className="w-4 h-4" />
            Sair da conta
          </button>
        </div>
      </div>
    </div>
  );
}
