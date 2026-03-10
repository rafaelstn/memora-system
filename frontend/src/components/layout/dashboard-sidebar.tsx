"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Database,
  BarChart3,
  Users,
  Settings,
  ChevronLeft,
  ChevronRight,
  LogOut,
  ShieldAlert,
  Brain,
  FileSearch,
  BookOpen,
  Scale,
  Code2,
  GitCompare,
  LineChart,
  Package,
  Search,
  Download,
  Crown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { RoleBadge } from "@/components/ui/badge";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/lib/hooks/useAuth";
import { ProductSwitcher } from "@/components/products/ProductSwitcher";
import { useState, useEffect } from "react";
import { getIncidentStats } from "@/lib/api";
import { UserProfilePanel } from "@/components/profile/UserProfilePanel";

const navItems = [
  { href: "/dashboard", label: "Repositórios", icon: Database },
  { href: "/dashboard/monitor", label: "Monitor de Erros", icon: ShieldAlert, roles: ["admin", "dev"] },
  { href: "/dashboard/memory", label: "Memória Técnica", icon: Brain, roles: ["admin", "dev"] },
  { href: "/dashboard/reviews", label: "Revisão de Código", icon: FileSearch, roles: ["admin", "dev"] },
  { href: "/dashboard/docs", label: "Documentação", icon: BookOpen, roles: ["admin", "dev"] },
  { href: "/dashboard/rules", label: "Regras de Negócio", icon: Scale },
  { href: "/dashboard/codegen", label: "Geração de Código", icon: Code2, roles: ["admin", "dev"] },
  { href: "/dashboard/impact", label: "Análise de Impacto", icon: GitCompare, roles: ["admin", "dev"] },
];

const adminItems = [
  { href: "/dashboard/metrics", label: "Métricas", icon: BarChart3 },
  { href: "/dashboard/executive", label: "Painel Executivo", icon: LineChart },
  { href: "/dashboard/admin/users", label: "Usuários", icon: Users },
  { href: "/dashboard/admin/produtos", label: "Produtos", icon: Package },
  { href: "/dashboard/admin/exportar", label: "Exportar Dados", icon: Download },
  { href: "/dashboard/admin/planos", label: "Planos", icon: Crown },
  { href: "/dashboard/settings", label: "Configurações", icon: Settings },
];

export function DashboardSidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const { user, signOut, isLoading, refreshUser } = useAuth();
  const [activeIncidents, setActiveIncidents] = useState(0);
  const [profileOpen, setProfileOpen] = useState(false);

  useEffect(() => {
    if (!user || !["admin", "dev"].includes(user.role)) return;
    getIncidentStats()
      .then((s) => setActiveIncidents(s.active))
      .catch(() => {});
    const interval = setInterval(() => {
      getIncidentStats()
        .then((s) => setActiveIncidents(s.active))
        .catch(() => {});
    }, 30000);
    return () => clearInterval(interval);
  }, [user]);

  if (isLoading || !user) {
    return (
      <aside className={cn(
        "fixed left-0 top-0 z-40 flex h-screen flex-col border-r border-border bg-sidebar-bg w-64",
        "max-lg:hidden lg:relative",
      )}>
        <div className="flex h-14 items-center gap-3 border-b border-border px-4">
          <div className="h-8 w-8 rounded-lg bg-hover animate-pulse" />
          <div className="h-5 w-20 rounded bg-hover animate-pulse" />
        </div>
      </aside>
    );
  }

  return (
    <>
      {/* Mobile overlay */}
      <div className={cn(
        "fixed inset-0 z-40 bg-black/50 lg:hidden",
        collapsed ? "hidden" : "block lg:hidden"
      )} onClick={() => setCollapsed(true)} />

      <aside
        className={cn(
          "fixed left-0 top-0 z-40 flex h-screen flex-col border-r border-border bg-sidebar-bg transition-all duration-200",
          collapsed ? "w-16" : "w-64",
          "max-lg:hidden lg:relative"
        )}
      >
        {/* Logo */}
        <div className="flex h-14 items-center gap-3 border-b border-border px-4">
          <img src="/logo-icon.png" alt="Memora" className="h-8 w-8 shrink-0 rounded-lg dark:hidden" />
          <img src="/logo-white.png" alt="Memora" className="h-8 w-8 shrink-0 rounded-lg hidden dark:block" />
          {!collapsed && <span className="text-lg font-bold tracking-tight">Memora</span>}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="ml-auto p-1.5 rounded-lg hover:bg-hover text-muted transition-colors"
          >
            {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>

        {/* Search button */}
        <div className="border-b border-border px-3 py-2">
          <button
            onClick={() => window.dispatchEvent(new CustomEvent("open-global-search"))}
            className={cn(
              "flex items-center gap-3 w-full rounded-lg px-3 py-2 text-sm text-muted hover:bg-hover hover:text-foreground transition-colors",
              collapsed && "justify-center"
            )}
            title="Buscar (Ctrl+K)"
          >
            <Search size={18} />
            {!collapsed && (
              <>
                <span>Buscar...</span>
                <kbd className="ml-auto text-[10px] bg-muted/10 border border-border rounded px-1.5 py-0.5">
                  Ctrl+K
                </kbd>
              </>
            )}
          </button>
        </div>

        {/* Product switcher */}
        <div className="border-b border-border px-3 py-2">
          <ProductSwitcher />
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {navItems
            .filter((item) => !("roles" in item) || (item.roles as string[]).includes(user.role))
            .map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href))
                  ? "bg-accent-surface text-accent-text"
                  : "text-muted hover:bg-hover hover:text-foreground"
              )}
            >
              <item.icon size={18} />
              {!collapsed && item.label}
              {!collapsed && item.href === "/dashboard/monitor" && activeIncidents > 0 && (
                <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 text-white text-[10px] font-bold animate-pulse">
                  {activeIncidents}
                </span>
              )}
            </Link>
          ))}

          {/* Admin section */}
          {user.role === "admin" && (
            <>
              {!collapsed && (
                <div className="pt-5 pb-2 px-3">
                  <span className="text-[11px] font-semibold uppercase tracking-widest text-muted">
                    Administração
                  </span>
                </div>
              )}
              {collapsed && <div className="border-t border-border my-3" />}
              {adminItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                    pathname.startsWith(item.href)
                      ? "bg-accent-surface text-accent-text"
                      : "text-muted hover:bg-hover hover:text-foreground"
                  )}
                >
                  <item.icon size={18} />
                  {!collapsed && item.label}
                </Link>
              ))}
            </>
          )}
        </nav>

        {/* Footer: Theme toggle + User */}
        <div className="border-t border-border p-3 space-y-3">
          {!collapsed && (
            <div className="flex items-center justify-between px-1">
              <span className="text-[11px] font-medium text-muted uppercase tracking-wider">Tema</span>
              <ThemeToggle />
            </div>
          )}
          {collapsed && (
            <div className="flex justify-center">
              <ThemeToggle />
            </div>
          )}

          <div className="flex items-center gap-3">
            <button
              onClick={() => setProfileOpen(true)}
              className="flex items-center gap-3 flex-1 min-w-0 rounded-lg p-1 -m-1 hover:bg-hover transition-colors"
              title="Meu Perfil"
            >
              {user.avatar_url ? (
                <img
                  src={user.avatar_url}
                  alt={user.name}
                  className="h-9 w-9 shrink-0 rounded-full object-cover"
                />
              ) : (
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent-surface text-accent-text text-sm font-semibold">
                  {user.name.charAt(0).toUpperCase()}
                </div>
              )}
              {!collapsed && (
                <div className="flex-1 min-w-0 text-left">
                  <p className="text-sm font-medium truncate">{user.name}</p>
                  <RoleBadge role={user.role} />
                </div>
              )}
            </button>
            {!collapsed && (
              <button
                onClick={signOut}
                className="p-1.5 rounded-lg hover:bg-hover text-muted hover:text-foreground transition-colors"
                title="Sair"
              >
                <LogOut size={16} />
              </button>
            )}
          </div>
        </div>

        {/* Profile panel */}
        <UserProfilePanel
          open={profileOpen}
          onClose={() => setProfileOpen(false)}
          user={user}
          onProfileUpdated={refreshUser}
        />
      </aside>
    </>
  );
}
