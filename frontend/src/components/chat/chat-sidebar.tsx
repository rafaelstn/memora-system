"use client";

import { cn, groupByDate, formatTime, truncate } from "@/lib/utils";
import type { Conversation, User } from "@/lib/types";
import { RoleBadge } from "@/components/ui/badge";
import { ListItemSkeleton } from "@/components/ui/skeleton";
import Link from "next/link";
import {
  Plus,
  Trash2,
  MessageSquare,
  LayoutDashboard,
  Brain,
} from "lucide-react";

interface ChatSidebarProps {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  repoName: string;
  user: User;
  open?: boolean;
  onClose?: () => void;
}

export function ChatSidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
  repoName,
  user,
  open,
  onClose,
}: ChatSidebarProps) {
  const grouped = groupByDate(conversations);

  const sidebarContent = (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2 mb-4">
          <img src="/memora-favicon.png" alt="Memora" className="h-8 w-8" />
          <div>
            <p className="text-sm font-semibold text-foreground">Memora</p>
            <p className="text-xs text-muted">{repoName}</p>
          </div>
        </div>
        <button
          onClick={onNew}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-dark transition-colors"
        >
          <Plus className="h-4 w-4" />
          Nova conversa
        </button>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto p-2">
        {conversations.length === 0 && (
          <div className="text-center text-muted text-sm py-8">
            Nenhuma conversa ainda
          </div>
        )}

        {Object.entries(grouped).map(([dateLabel, convs]) => (
          <div key={dateLabel} className="mb-3">
            <p className="text-xs font-medium text-muted px-2 py-1">
              {dateLabel}
            </p>
            {convs.map((conv) => (
              <div
                key={conv.id}
                role="button"
                tabIndex={0}
                onClick={() => onSelect(conv.id)}
                onKeyDown={(e) => { if (e.key === "Enter") onSelect(conv.id); }}
                className={cn(
                  "w-full group flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm transition-colors cursor-pointer",
                  conv.id === activeId
                    ? "bg-accent-surface text-accent-text"
                    : "text-foreground hover:bg-hover"
                )}
              >
                <MessageSquare className="h-4 w-4 shrink-0 text-muted" />
                <div className="flex-1 min-w-0">
                  <p className="truncate">
                    {truncate(conv.title, 6)}
                  </p>
                  <p className="text-xs text-muted">
                    {formatTime(conv.updated_at)}
                  </p>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(conv.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 rounded-lg hover:bg-danger-surface hover:text-danger transition-all"
                  title="Excluir conversa"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-border">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-full bg-accent-surface flex items-center justify-center text-accent-text text-sm font-semibold">
            {user.name.charAt(0)}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-foreground truncate">
              {user.name}
            </p>
            <RoleBadge role={user.role} />
          </div>
        </div>
        <Link
          href="/dashboard"
          className="mt-3 flex items-center gap-2 text-xs text-muted hover:text-foreground transition-colors"
        >
          <LayoutDashboard className="h-3.5 w-3.5" />
          Ir para o Dashboard
        </Link>
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed lg:relative z-50 lg:z-auto top-0 left-0 h-full w-[260px] bg-sidebar-bg border-r border-border transition-transform duration-200",
          "lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {sidebarContent}
      </aside>
    </>
  );
}
