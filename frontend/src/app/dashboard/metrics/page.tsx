"use client";

import { Suspense, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { BarChart3, Shield, LineChart, Loader2, Server } from "lucide-react";
import dynamic from "next/dynamic";
import { useAuth } from "@/lib/hooks/useAuth";

const UsageTab = dynamic(() => import("./usage-tab"), { ssr: false });
const SecurityTab = dynamic(() => import("./security-tab"), { ssr: false });
const ExecutiveTab = dynamic(() => import("./executive-tab"), { ssr: false });
const SystemTab = dynamic(() => import("./system-tab"), { ssr: false });

const ALL_TABS = [
  { id: "usage", label: "Uso", icon: BarChart3 },
  { id: "security", label: "Seguranca", icon: Shield },
  { id: "executive", label: "Visao Executiva", icon: LineChart },
  { id: "sistema", label: "Sistema", icon: Server, adminOnly: true },
] as const;

type TabId = (typeof ALL_TABS)[number]["id"];

function MetricsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const TABS = ALL_TABS.filter((t) => !("adminOnly" in t && t.adminOnly) || isAdmin);

  const initialTab = (searchParams.get("tab") as TabId) || "usage";
  const [activeTab, setActiveTab] = useState<TabId>(
    TABS.some((t) => t.id === initialTab) ? initialTab : "usage",
  );

  const switchTab = (tab: TabId) => {
    setActiveTab(tab);
    router.replace(`/dashboard/metrics?tab=${tab}`, { scroll: false });
  };

  return (
    <div className="p-5 md:p-8 space-y-6">
      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-border">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => switchTab(tab.id)}
            className={cn(
              "flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors -mb-px",
              activeTab === tab.id
                ? "border-accent-text text-accent-text"
                : "border-transparent text-muted hover:text-foreground hover:border-border",
            )}
          >
            <tab.icon size={16} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "usage" && <UsageTab />}
      {activeTab === "security" && <SecurityTab />}
      {activeTab === "executive" && <ExecutiveTab />}
      {activeTab === "sistema" && isAdmin && <SystemTab />}
    </div>
  );
}

export default function MetricsPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center py-20"><Loader2 className="animate-spin text-muted" size={24} /></div>}>
      <MetricsContent />
    </Suspense>
  );
}
