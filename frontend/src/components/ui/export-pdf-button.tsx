"use client";

import { useState } from "react";
import { Download, Loader2, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { downloadPDF } from "@/lib/api";

interface ExportPDFButtonProps {
  endpoint: string;
  filename: string;
  label?: string;
  className?: string;
  size?: "sm" | "md";
}

export function ExportPDFButton({
  endpoint,
  filename,
  label = "Exportar PDF",
  className,
  size = "md",
}: ExportPDFButtonProps) {
  const [state, setState] = useState<"idle" | "loading" | "error">("idle");

  async function handleClick() {
    setState("loading");
    try {
      await downloadPDF(endpoint, filename);
      setState("idle");
    } catch {
      setState("error");
      setTimeout(() => setState("idle"), 3000);
    }
  }

  const sizeClass = size === "sm" ? "px-3 py-1.5 text-xs" : "px-4 py-2 text-sm";

  return (
    <button
      onClick={handleClick}
      disabled={state === "loading"}
      className={cn(
        "inline-flex items-center gap-2 border border-border rounded-lg font-medium transition-colors disabled:opacity-50",
        state === "error"
          ? "text-red-500 hover:bg-red-500/10"
          : "text-foreground hover:bg-muted/10",
        sizeClass,
        className,
      )}
    >
      {state === "loading" ? (
        <>
          <Loader2 size={14} className="animate-spin" />
          Gerando PDF...
        </>
      ) : state === "error" ? (
        <>
          <AlertCircle size={14} />
          Erro — tentar novamente
        </>
      ) : (
        <>
          <Download size={14} />
          {label}
        </>
      )}
    </button>
  );
}
