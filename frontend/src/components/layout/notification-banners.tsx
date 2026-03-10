"use client";

import { useEffect, useState, useCallback } from "react";
import { X, AlertTriangle, FileCode, Users, AlertCircle } from "lucide-react";
import { useAuth } from "@/lib/hooks/useAuth";
import { apiFetch } from "@/lib/api";

interface Banner {
  id: number;
  notification_type: string;
  detail: string | null;
  sent_at: string;
}

const ICONS: Record<string, typeof AlertTriangle> = {
  repo_outdated: FileCode,
  rules_changed: FileCode,
  dev_inactive: Users,
  critical_alerts: AlertCircle,
};

const COLORS: Record<string, string> = {
  repo_outdated:
    "bg-yellow-500/10 border-yellow-500/30 text-yellow-700 dark:text-yellow-400",
  rules_changed:
    "bg-blue-500/10 border-blue-500/30 text-blue-700 dark:text-blue-400",
  dev_inactive:
    "bg-purple-500/10 border-purple-500/30 text-purple-700 dark:text-purple-400",
  critical_alerts:
    "bg-red-500/10 border-red-500/30 text-red-700 dark:text-red-400",
};

export default function NotificationBanners() {
  const { user } = useAuth();
  const [banners, setBanners] = useState<Banner[]>([]);
  const [dismissed, setDismissed] = useState<Set<number>>(new Set());

  const fetchBanners = useCallback(async () => {
    try {
      const data = await apiFetch<Banner[]>(
        "/api/notifications/banners"
      );
      setBanners(data || []);
    } catch {
      // silently fail
    }
  }, []);

  useEffect(() => {
    if (!user || user.role === "suporte") return;
    fetchBanners();
    const interval = setInterval(fetchBanners, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [user, fetchBanners]);

  async function handleDismiss(id: number) {
    setDismissed((prev) => new Set(prev).add(id));
    try {
      await apiFetch(`/api/notifications/banners/${id}/dismiss`, {
        method: "POST",
      });
    } catch {
      setDismissed((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  }

  const visible = banners
    .filter((b) => !dismissed.has(b.id))
    .slice(0, 3);

  if (visible.length === 0) return null;

  return (
    <div className="flex flex-col gap-2 px-4 py-2">
      {visible.map((banner) => {
        const Icon =
          ICONS[banner.notification_type] || AlertTriangle;
        const colorClass =
          COLORS[banner.notification_type] || COLORS.repo_outdated;

        return (
          <div
            key={banner.id}
            className={`flex items-center gap-3 px-4 py-3 rounded-lg border ${colorClass}`}
          >
            <Icon size={18} className="flex-shrink-0" />
            <span className="text-sm flex-1">
              {banner.detail || banner.notification_type}
            </span>
            <button
              onClick={() => handleDismiss(banner.id)}
              className="flex-shrink-0 p-1 rounded hover:bg-black/10 dark:hover:bg-white/10 transition-colors"
              aria-label="Dispensar"
            >
              <X size={14} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
