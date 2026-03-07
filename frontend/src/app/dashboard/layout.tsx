"use client";

import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/hooks/useAuth";
import { Loader2, Clock } from "lucide-react";

const DashboardSidebar = dynamic(
  () => import("@/components/layout/dashboard-sidebar").then((m) => m.DashboardSidebar),
  { ssr: false },
);

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  // While loading auth, show spinner
  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <Loader2 size={32} className="animate-spin text-accent" />
      </div>
    );
  }

  // Admin with incomplete onboarding -> redirect to /setup
  if (user && !user.onboarding_completed && user.role === "admin") {
    router.push("/setup");
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <Loader2 size={32} className="animate-spin text-accent" />
      </div>
    );
  }

  // Non-admin with incomplete onboarding -> waiting screen
  if (user && !user.onboarding_completed && user.role !== "admin") {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="text-center space-y-4 max-w-md px-6">
          <div className="flex justify-center">
            <div className="w-16 h-16 rounded-2xl bg-muted/10 flex items-center justify-center">
              <Clock size={32} className="text-muted" />
            </div>
          </div>
          <h1 className="text-xl font-bold">Aguardando configuracao</h1>
          <p className="text-muted">
            O administrador ainda esta concluindo a configuracao inicial do Memora.
            Voce sera redirecionado automaticamente quando o setup for finalizado.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="text-sm text-accent hover:underline"
          >
            Verificar novamente
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <DashboardSidebar />
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
