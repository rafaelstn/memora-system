import { cn } from "@/lib/utils";
import type { Role } from "@/lib/types";

const roleColors: Record<Role, string> = {
  admin: "bg-purple-100 text-purple-700 dark:bg-purple-500/15 dark:text-purple-300",
  dev: "bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300",
  suporte: "bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-300",
};

const statusColors: Record<string, string> = {
  indexed: "bg-success-surface text-success",
  outdated: "bg-warning-surface text-warning",
  not_indexed: "bg-danger-surface text-danger",
  pending: "bg-warning-surface text-warning",
  used: "bg-hover text-muted",
  expired: "bg-danger-surface text-danger",
};

const chunkTypeColors: Record<string, string> = {
  function: "bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300",
  class: "bg-purple-100 text-purple-700 dark:bg-purple-500/15 dark:text-purple-300",
  module: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300",
};

export function RoleBadge({ role }: { role: Role }) {
  return (
    <span className={cn("px-2 py-0.5 rounded-full text-[11px] font-semibold", roleColors[role])}>
      {role}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const labels: Record<string, string> = {
    indexed: "Indexado",
    outdated: "Desatualizado",
    not_indexed: "Não indexado",
    pending: "Pendente",
    used: "Usado",
    expired: "Expirado",
  };
  return (
    <span className={cn("px-2 py-0.5 rounded-full text-[11px] font-semibold", statusColors[status])}>
      {labels[status] || status}
    </span>
  );
}

export function ChunkTypeBadge({ type }: { type: string }) {
  return (
    <span className={cn("px-2 py-0.5 rounded-full text-[11px] font-semibold", chunkTypeColors[type] || chunkTypeColors.module)}>
      {type}
    </span>
  );
}
