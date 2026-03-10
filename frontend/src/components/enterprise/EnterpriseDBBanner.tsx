"use client";

import { useState, useEffect, useCallback } from "react";
import { AlertTriangle, RefreshCw, X, CheckCircle2 } from "lucide-react";
import { useAuth } from "@/lib/hooks/useAuth";
import { enterpriseGetStatus, enterpriseHealthCheck } from "@/lib/api";

export function EnterpriseDBBanner() {
  const { user } = useAuth();
  const [status, setStatus] = useState<"ok" | "error" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const [checking, setChecking] = useState(false);

  const checkStatus = useCallback(async () => {
    try {
      const s = await enterpriseGetStatus();
      if (s.last_health_status === "error") {
        setStatus("error");
        setError(s.last_health_error || "Banco indisponivel");
      } else {
        setStatus(s.last_health_status as "ok" | null);
        setError(null);
      }
    } catch {
      // Silently ignore — user may not be enterprise
    }
  }, []);

  useEffect(() => {
    if (!user || user.org_mode !== "enterprise" || !user.enterprise_setup_complete) return;
    checkStatus();
    const interval = setInterval(checkStatus, 60_000); // Poll every 60s
    return () => clearInterval(interval);
  }, [user, checkStatus]);

  const handleRetry = async () => {
    setChecking(true);
    try {
      const result = await enterpriseHealthCheck();
      setStatus(result.status);
      setError(result.error);
      if (result.status === "ok") setDismissed(false);
    } catch {
      // keep current state
    } finally {
      setChecking(false);
    }
  };

  // Don't render if not enterprise, not error, or dismissed
  if (!user || user.org_mode !== "enterprise" || status !== "error" || dismissed) {
    return null;
  }

  return (
    <div className="bg-red-500/10 border-b border-red-500/30 px-4 py-2.5 flex items-center gap-3">
      <AlertTriangle size={16} className="shrink-0 text-red-500" />
      <div className="flex-1 min-w-0">
        <span className="text-sm font-medium text-red-700 dark:text-red-400">
          Banco de dados Enterprise indisponivel
        </span>
        {error && (
          <span className="text-xs text-red-600/70 dark:text-red-400/70 ml-2 truncate">
            — {error}
          </span>
        )}
      </div>
      <button
        onClick={handleRetry}
        disabled={checking}
        className="flex items-center gap-1.5 text-xs font-medium text-red-700 dark:text-red-400 hover:text-red-900 dark:hover:text-red-300 transition-colors disabled:opacity-50"
      >
        <RefreshCw size={12} className={checking ? "animate-spin" : ""} />
        Verificar
      </button>
      <button
        onClick={() => setDismissed(true)}
        className="text-red-500/60 hover:text-red-500 transition-colors"
      >
        <X size={14} />
      </button>
    </div>
  );
}
