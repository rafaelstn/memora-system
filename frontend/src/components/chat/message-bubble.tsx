"use client";

import { cn, formatTime, formatCostUSD } from "@/lib/utils";
import type { Message } from "@/lib/types";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Copy, Check, AlertCircle, RefreshCw } from "lucide-react";
import { useState } from "react";

interface MessageBubbleProps {
  message: Message;
  isLoading?: boolean;
  isError?: boolean;
  onRetry?: () => void;
}

function CodeBlock({
  language,
  children,
}: {
  language: string;
  children: string;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(children);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group my-3 rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-4 py-1.5 bg-[#1e1e1e] text-xs text-gray-400">
        <span>{language || "code"}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 hover:text-white transition-colors"
        >
          {copied ? (
            <>
              <Check className="h-3 w-3" />
              Copiado
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" />
              Copiar
            </>
          )}
        </button>
      </div>
      <SyntaxHighlighter
        style={oneDark}
        language={language || "text"}
        PreTag="div"
        customStyle={{ margin: 0, borderRadius: 0, fontSize: "0.8125rem" }}
      >
        {children}
      </SyntaxHighlighter>
    </div>
  );
}

export function MessageBubble({
  message,
  isLoading,
  isError,
  onRetry,
}: MessageBubbleProps) {
  const isUser = message.role === "user";

  // Loading state
  if (isLoading) {
    return (
      <div className="flex gap-3 px-4 py-3">
        <img src="/logo.png" alt="Memora" className="h-8 w-8 rounded-full shrink-0 dark:hidden" />
        <img src="/logo-white.png" alt="Memora" className="h-8 w-8 rounded-full shrink-0 hidden dark:block" />
        <div className="flex items-center gap-1.5 py-2">
          <span className="loading-dot h-2 w-2 rounded-full bg-accent" />
          <span className="loading-dot h-2 w-2 rounded-full bg-accent" />
          <span className="loading-dot h-2 w-2 rounded-full bg-accent" />
        </div>
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="flex gap-3 px-4 py-3">
        <div className="h-8 w-8 rounded-full bg-danger-surface flex items-center justify-center text-danger shrink-0">
          <AlertCircle className="h-4 w-4" />
        </div>
        <div className="rounded-2xl rounded-bl-sm bg-danger-surface border border-danger/20 px-4 py-3 max-w-[80%]">
          <p className="text-sm text-danger mb-2">
            Ocorreu um erro ao gerar a resposta.
          </p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="flex items-center gap-1.5 text-xs text-danger hover:text-danger/80 font-medium transition-colors"
            >
              <RefreshCw className="h-3 w-3" />
              Tentar novamente
            </button>
          )}
        </div>
      </div>
    );
  }

  // User message
  if (isUser) {
    return (
      <div className="flex justify-end px-4 py-3">
        <div className="bg-accent text-white px-4 py-2.5 rounded-2xl rounded-br-sm max-w-[80%]">
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          <p className="text-xs text-white/60 mt-1 text-right">
            {formatTime(message.created_at)}
          </p>
        </div>
      </div>
    );
  }

  // Assistant message
  return (
    <div className="flex gap-3 px-4 py-3">
      <img src="/logo.png" alt="Memora" className="h-8 w-8 rounded-full shrink-0 dark:hidden object-cover" />
      <img src="/logo-white.png" alt="Memora" className="h-8 w-8 rounded-full shrink-0 hidden dark:block object-cover" />
      <div className="min-w-0 max-w-[80%]">
        <div className="bg-card-bg border border-border rounded-2xl rounded-bl-sm px-4 py-3">
          <div className="prose-sm text-foreground">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || "");
                  const codeString = String(children).replace(/\n$/, "");

                  if (match) {
                    return (
                      <CodeBlock language={match[1]}>{codeString}</CodeBlock>
                    );
                  }

                  return (
                    <code
                      className="bg-accent-surface text-accent-text px-1.5 py-0.5 rounded-md text-sm font-mono"
                      {...props}
                    >
                      {children}
                    </code>
                  );
                },
                p({ children }) {
                  return <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>;
                },
                ul({ children }) {
                  return <ul className="list-disc pl-5 mb-2 space-y-1">{children}</ul>;
                },
                ol({ children }) {
                  return <ol className="list-decimal pl-5 mb-2 space-y-1">{children}</ol>;
                },
                strong({ children }) {
                  return <strong className="font-semibold">{children}</strong>;
                },
                h1({ children }) {
                  return <h1 className="text-lg font-bold mb-2">{children}</h1>;
                },
                h2({ children }) {
                  return <h2 className="text-base font-bold mb-2">{children}</h2>;
                },
                h3({ children }) {
                  return <h3 className="text-sm font-bold mb-1">{children}</h3>;
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        </div>
        {/* Metadata */}
        <div className="flex items-center gap-2 mt-1 px-1 flex-wrap">
          <span className="text-xs text-muted">
            {formatTime(message.created_at)}
          </span>
          {message.model_used && message.model_used !== "none" && message.model_used !== "search-only" && (
            <span className="inline-flex items-center gap-1 text-xs text-muted">
              <span>{message.provider === "ollama" ? "\uD83D\uDDA5\uFE0F" : "\u26A1"}</span>
              <span>{message.provider_name || message.model_used}</span>
            </span>
          )}
          {message.cost_usd !== undefined && message.cost_usd > 0 && (
            <span
              className="text-xs text-muted cursor-help"
              title={`Custo: ${formatCostUSD(message.cost_usd)} | Tokens: ${message.tokens_used ?? "?"}`}
            >
              {formatCostUSD(message.cost_usd)}
            </span>
          )}
          {message.cost_usd === 0 && message.provider === "ollama" && (
            <span className="text-xs text-muted">Local</span>
          )}
        </div>
      </div>
    </div>
  );
}
