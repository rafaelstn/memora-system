"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Clock, AlertTriangle, XCircle } from "lucide-react";
import { useAuth } from "@/lib/hooks/useAuth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface PlanInfo {
  plan: "pro_trial" | "pro" | "enterprise" | "customer";
  status: "trial_active" | "trial_expired" | "active" | "inactive";
  days_remaining: number | null;
  trial_ends_at: string | null;
  is_active: boolean;
}

export default function TrialBanner() {
  const { user } = useAuth();
  const [planInfo, setPlanInfo] = useState<PlanInfo | null>(null);

  useEffect(() => {
    if (!user || user.role !== "admin") return;

    async function fetchPlan() {
      try {
        const { getAccessToken } = await import("@/lib/auth");
        const token = await getAccessToken();
        const res = await fetch(`${API_BASE}/api/admin/plan`, {
          headers: {
            "Content-Type": "application/json",
            "ngrok-skip-browser-warning": "true",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        });
        if (!res.ok) return;
        const data: PlanInfo = await res.json();
        setPlanInfo(data);
      } catch {
        // silently fail
      }
    }

    fetchPlan();
  }, [user]);

  if (!user || user.role !== "admin") return null;
  if (!planInfo) return null;

  // Active plans: no banner
  if (["pro", "enterprise", "customer"].includes(planInfo.plan)) return null;
  if (planInfo.plan !== "pro_trial") return null;

  const days = planInfo.days_remaining ?? 0;

  // 7-4 days: blue subtle
  if (days >= 4 && planInfo.status === "trial_active") {
    return (
      <div className="flex flex-col gap-2 px-4 py-2">
        <div className="flex items-center gap-3 px-4 py-3 rounded-lg border bg-blue-500/10 border-blue-500/30 text-blue-700 dark:text-blue-400">
          <Clock size={18} className="flex-shrink-0" />
          <span className="text-sm flex-1">
            Trial ativo — {days} dias restantes. Aproveite todos os recursos.
          </span>
        </div>
      </div>
    );
  }

  // 3-1 days: yellow warning
  if (days >= 1 && planInfo.status === "trial_active") {
    return (
      <div className="flex flex-col gap-2 px-4 py-2">
        <div className="flex items-center gap-3 px-4 py-3 rounded-lg border bg-yellow-500/10 border-yellow-500/30 text-yellow-700 dark:text-yellow-400">
          <AlertTriangle size={18} className="flex-shrink-0" />
          <span className="text-sm flex-1">
            Seu trial expira em {days} dia{days > 1 ? "s" : ""}. Entre em contato para continuar.
          </span>
          <Link
            href="/upgrade"
            className="flex-shrink-0 text-sm font-medium px-3 py-1.5 rounded-md bg-yellow-500/20 hover:bg-yellow-500/30 transition-colors"
          >
            Falar com a equipe
          </Link>
        </div>
      </div>
    );
  }

  // 0 days or expired
  if (days <= 0 || planInfo.status === "trial_expired") {
    return (
      <div className="flex flex-col gap-2 px-4 py-2">
        <div className="flex items-center gap-3 px-4 py-3 rounded-lg border bg-red-500/10 border-red-500/30 text-red-700 dark:text-red-400">
          <XCircle size={18} className="flex-shrink-0" />
          <span className="text-sm flex-1">
            Seu trial expirou. Para continuar usando o Memora, entre em contato.
          </span>
          <Link
            href="/upgrade"
            className="flex-shrink-0 text-sm font-medium px-3 py-1.5 rounded-md bg-red-500/20 hover:bg-red-500/30 transition-colors"
          >
            Ver opcoes
          </Link>
        </div>
      </div>
    );
  }

  return null;
}
