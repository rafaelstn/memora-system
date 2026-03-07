"use client";

import { useState, useRef, useCallback } from "react";
import { cn } from "@/lib/utils";
import { Send, Lock } from "lucide-react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  disabledMessage?: string;
}

export function ChatInput({ onSend, disabled, disabledMessage }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const adjustHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    const lineHeight = 24;
    const maxHeight = lineHeight * 5;
    textarea.style.height = `${Math.min(textarea.scrollHeight, maxHeight)}px`;
  }, []);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (disabled) {
    return (
      <div className="px-4 py-3 border-t border-border bg-card-bg">
        <div className="flex items-center gap-2 justify-center py-3 text-muted">
          <Lock className="h-4 w-4" />
          <span className="text-sm">
            {disabledMessage || "Entrada desabilitada"}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="px-4 py-3 border-t border-border bg-card-bg">
      <div className="flex items-end gap-2 max-w-3xl mx-auto">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            adjustHeight();
          }}
          onKeyDown={handleKeyDown}
          placeholder="Faça uma pergunta sobre o repositório..."
          rows={1}
          className={cn(
            "flex-1 resize-none bg-background border border-border rounded-xl px-4 py-2.5 text-sm text-foreground",
            "placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent",
            "transition-colors"
          )}
          style={{ lineHeight: "24px" }}
        />
        <button
          onClick={handleSend}
          disabled={!value.trim()}
          className={cn(
            "shrink-0 p-2.5 rounded-xl transition-colors",
            value.trim()
              ? "bg-accent text-white hover:bg-accent-dark"
              : "bg-border text-muted cursor-not-allowed"
          )}
          title="Enviar mensagem"
        >
          <Send className="h-4 w-4" />
        </button>
      </div>
      <p className="text-xs text-muted text-center mt-2">
        Enter para enviar, Shift+Enter para quebrar linha
      </p>
    </div>
  );
}
