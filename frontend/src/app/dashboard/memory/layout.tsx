"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Search, Clock, BookOpen, FileText, Upload } from "lucide-react";

const tabs = [
  { href: "/dashboard/memory", label: "Busca", icon: Search, exact: true },
  { href: "/dashboard/memory/timeline", label: "Timeline", icon: Clock },
  { href: "/dashboard/memory/wiki", label: "Wiki", icon: BookOpen },
  { href: "/dashboard/memory/adrs", label: "ADRs", icon: FileText },
  { href: "/dashboard/memory/documents", label: "Documentos", icon: Upload },
];

export default function MemoryLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-border px-5 lg:px-8">
        <nav className="flex gap-1 -mb-px overflow-x-auto">
          {tabs.map((tab) => {
            const active = tab.exact
              ? pathname === tab.href
              : pathname.startsWith(tab.href);
            return (
              <Link
                key={tab.href}
                href={tab.href}
                className={cn(
                  "flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap",
                  active
                    ? "border-accent text-accent"
                    : "border-transparent text-muted hover:text-foreground hover:border-border"
                )}
              >
                <tab.icon size={16} />
                {tab.label}
              </Link>
            );
          })}
        </nav>
      </div>
      {children}
    </div>
  );
}
