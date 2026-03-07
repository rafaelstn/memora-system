"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { cn } from "@/lib/utils";
import type { Message, Source } from "@/lib/types";
import { askQuestionStream } from "@/lib/api";
import { useAuth } from "@/lib/hooks/useAuth";
import { useChatContext } from "@/lib/chat-context";
import { ChatSidebar } from "@/components/chat/chat-sidebar";
import { MessageBubble } from "@/components/chat/message-bubble";
import { SourcesPanel } from "@/components/chat/sources-panel";
import { ChatInput } from "@/components/chat/chat-input";
import { StatusBadge } from "@/components/ui/badge";
import toast from "react-hot-toast";
import {
  Menu,
  BookOpen,
  MessageSquareText,
  Sparkles,
  Code2,
  GitBranch,
  AlertTriangle,
} from "lucide-react";

export default function ChatPage() {
  const params = useParams();
  const repoName = params.repo as string;
  const { user } = useAuth();

  const chat = useChatContext();

  const repoStatus = "indexed" as "indexed" | "outdated" | "not_indexed";

  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isError, setIsError] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  // Local streaming messages — synced to context on completion
  const [streamingMessages, setStreamingMessages] = useState<Message[] | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const initRef = useRef<string | null>(null);
  const streamConvIdRef = useRef<string | null>(null);

  // Derive state from context
  const conversations = chat.conversationsByRepo[repoName] ?? [];
  const activeConversationId = chat.activeRepoName === repoName ? chat.activeConversationId : null;
  const contextMessages = activeConversationId
    ? (chat.messagesByConv[activeConversationId] ?? [])
    : [];
  // During streaming, use local state; otherwise use context
  const messages = streamingMessages ?? contextMessages;
  const sources = chat.sources;

  // Load conversations + restore last active on mount / repo change
  useEffect(() => {
    if (initRef.current === repoName) return;
    initRef.current = repoName;

    chat.loadConversations(repoName).then((convs) => {
      const lastActive = chat.lastActiveByRepo[repoName];
      if (lastActive && convs.some((c) => c.id === lastActive)) {
        chat.setActiveConversation(lastActive, repoName);
        if (!chat.messagesByConv[lastActive]) {
          setIsLoading(true);
          chat.loadMessages(lastActive).finally(() => setIsLoading(false));
        }
      } else {
        chat.setActiveConversation(null, repoName);
      }
    });
  }, [repoName]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSelectConversation = useCallback(
    (id: string) => {
      // Cancel any in-flight stream
      abortRef.current?.abort();
      setStreamingMessages(null);

      chat.setActiveConversation(id, repoName);
      setSidebarOpen(false);
      setSourcesOpen(false);
      setIsError(false);

      if (!chat.messagesByConv[id]) {
        setIsLoading(true);
        chat.loadMessages(id).finally(() => setIsLoading(false));
      }
    },
    [repoName, chat],
  );

  const handleNewConversation = useCallback(() => {
    abortRef.current?.abort();
    setStreamingMessages(null);
    chat.startNewConversation(repoName);
    setSourcesOpen(false);
    setSidebarOpen(false);
    setIsError(false);
  }, [repoName, chat]);

  const handleDeleteConversation = useCallback(
    (id: string) => {
      chat.deleteConversation(id, repoName);
      setSourcesOpen(false);
      setIsError(false);
    },
    [repoName, chat],
  );

  const handleSend = useCallback(
    async (content: string) => {
      const userMsg: Message = {
        id: `m-${Date.now()}`,
        conversation_id: activeConversationId ?? "",
        role: "user",
        content,
        created_at: new Date().toISOString(),
      };

      const assistantMsgId = `m-${Date.now()}-a`;

      // Start streaming with local state (base = current context messages + user msg)
      const baseMsgs = [...contextMessages, userMsg];
      setStreamingMessages(baseMsgs);
      setIsLoading(true);
      setIsError(false);

      streamConvIdRef.current = activeConversationId;

      const controller = await askQuestionStream(
        repoName,
        content,
        // onText
        (text) => {
          setIsLoading(false);
          setStreamingMessages((prev) => {
            if (!prev) return prev;
            const last = prev[prev.length - 1];
            if (last && last.id === assistantMsgId) {
              return [
                ...prev.slice(0, -1),
                { ...last, content: last.content + text },
              ];
            }
            const assistantMsg: Message = {
              id: assistantMsgId,
              conversation_id: streamConvIdRef.current ?? "",
              role: "assistant",
              content: text,
              created_at: new Date().toISOString(),
            };
            return [...prev, assistantMsg];
          });
        },
        // onSources
        (streamSources) => {
          const mapped: Source[] = streamSources.map((s) => ({
            file_path: s.file_path,
            chunk_name: s.chunk_name,
            chunk_type: s.chunk_type as Source["chunk_type"],
            content_preview: s.content_preview,
            start_line: s.start_line,
          }));
          chat.setSources(mapped);
          setSourcesOpen(true);
          setStreamingMessages((prev) => {
            if (!prev) return prev;
            const last = prev[prev.length - 1];
            if (last && last.id === assistantMsgId) {
              return [...prev.slice(0, -1), { ...last, sources: mapped }];
            }
            return prev;
          });
        },
        // onDone — flush streaming messages to context
        (meta) => {
          setIsLoading(false);
          setStreamingMessages((prev) => {
            if (!prev) return prev;
            const last = prev[prev.length - 1];
            let final = prev;
            if (last && last.id === assistantMsgId) {
              final = [
                ...prev.slice(0, -1),
                {
                  ...last,
                  model_used: meta.model,
                  tokens_used: meta.tokens,
                  cost_usd: meta.cost_usd,
                },
              ];
            }
            // Flush to context
            const convId = streamConvIdRef.current;
            if (convId) {
              chat.cacheMessages(convId, final);
            }
            return null; // Clear streaming state, fall back to context
          });
          chat.refreshConversations(repoName);
        },
        // onError
        (error) => {
          setIsLoading(false);
          setIsError(true);
          toast.error(error || "Erro ao processar a pergunta");
          // Flush partial to context
          setStreamingMessages((prev) => {
            const convId = streamConvIdRef.current;
            if (convId && prev) {
              chat.cacheMessages(convId, prev);
            }
            return null;
          });
        },
        undefined, // providerId
        activeConversationId, // conversationId
        // onConversation
        (convId) => {
          streamConvIdRef.current = convId;
          chat.setActiveConversation(convId, repoName);
        },
      );

      abortRef.current = controller;
    },
    [activeConversationId, repoName, contextMessages, chat],
  );

  const handleRetry = useCallback(() => {
    const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
    if (lastUserMsg) {
      // Remove last assistant message
      if (activeConversationId) {
        chat.setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.role === "assistant") return prev.slice(0, -1);
          return prev;
        });
      }
      setIsError(false);
      handleSend(lastUserMsg.content);
    }
  }, [messages, handleSend, activeConversationId, chat]);

  const suggestions = [
    {
      icon: Code2,
      title: "Arquitetura do projeto",
      question: `Como o ${repoName} esta estruturado?`,
    },
    {
      icon: GitBranch,
      title: "Fluxo principal",
      question: `Qual o fluxo principal de execucao do ${repoName}?`,
    },
    {
      icon: Sparkles,
      title: "Funcionalidades",
      question: `Quais sao as principais funcionalidades do ${repoName}?`,
    },
  ];

  const showEmptyState = messages.length === 0 && !isLoading;

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <ChatSidebar
        conversations={conversations}
        activeId={activeConversationId}
        onSelect={handleSelectConversation}
        onNew={handleNewConversation}
        onDelete={handleDeleteConversation}
        repoName={repoName}
        user={
          user
            ? {
                id: user.id,
                name: user.name,
                email: user.email,
                role: user.role,
                is_active: user.is_active,
                created_at: "",
              }
            : {
                id: "",
                name: "...",
                email: "",
                role: "suporte" as const,
                is_active: true,
                created_at: "",
              }
        }
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="flex items-center justify-between px-4 py-3 border-b border-border bg-card-bg">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-1.5 rounded-lg hover:bg-border/50 text-muted"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-semibold text-foreground">
                {repoName}
              </h1>
              <StatusBadge status={repoStatus} />
            </div>
          </div>
          <button
            onClick={() => setSourcesOpen((prev) => !prev)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors",
              sourcesOpen
                ? "bg-accent/10 text-accent"
                : "text-muted hover:bg-border/50 hover:text-foreground",
            )}
          >
            <BookOpen className="h-4 w-4" />
            <span className="hidden sm:inline">Fontes</span>
            {sources.length > 0 && (
              <span className="bg-accent text-white text-xs rounded-full px-1.5 py-0.5 min-w-[18px] text-center">
                {sources.length}
              </span>
            )}
          </button>
        </header>

        {/* Outdated banner */}
        {repoStatus === "outdated" && (
          <div className="flex items-center gap-2 px-4 py-2 bg-warning/10 border-b border-warning/20 text-warning text-sm">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>
              Este repositorio esta desatualizado. A indexacao pode nao refletir
              as ultimas alteracoes do codigo.
            </span>
          </div>
        )}

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto">
          {showEmptyState && (
            <div className="flex flex-col items-center justify-center h-full text-center px-4">
              <div className="h-16 w-16 rounded-2xl bg-accent/10 flex items-center justify-center mb-4">
                <MessageSquareText className="h-8 w-8 text-accent" />
              </div>
              <h2 className="text-xl font-semibold text-foreground mb-2">
                Faca sua primeira pergunta sobre{" "}
                <span className="text-accent">{repoName}</span>
              </h2>
              <p className="text-sm text-muted max-w-md mb-8">
                Pergunte qualquer coisa sobre a base de codigo. O Memora vai
                buscar os trechos mais relevantes para responder.
              </p>
              <div className="grid gap-3 w-full max-w-lg">
                {suggestions.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(s.question)}
                    className="flex items-center gap-3 p-4 rounded-xl border border-border bg-card-bg hover:border-accent/40 hover:bg-accent/5 text-left transition-colors group"
                  >
                    <div className="h-10 w-10 rounded-lg bg-accent/10 flex items-center justify-center group-hover:bg-accent/20 transition-colors">
                      <s.icon className="h-5 w-5 text-accent" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground">
                        {s.title}
                      </p>
                      <p className="text-xs text-muted">{s.question}</p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.length > 0 && (
            <div className="max-w-3xl mx-auto py-4">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}

              {isLoading && (
                <MessageBubble
                  message={{
                    id: "loading",
                    conversation_id: "",
                    role: "assistant",
                    content: "",
                    created_at: new Date().toISOString(),
                  }}
                  isLoading
                />
              )}

              {isError && (
                <MessageBubble
                  message={{
                    id: "error",
                    conversation_id: "",
                    role: "assistant",
                    content: "",
                    created_at: new Date().toISOString(),
                  }}
                  isError
                  onRetry={handleRetry}
                />
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <ChatInput
          onSend={handleSend}
          disabled={repoStatus === "not_indexed"}
          disabledMessage="Este repositorio ainda nao foi indexado. Execute a ingestao antes de fazer perguntas."
        />
      </div>

      {/* Sources panel */}
      <SourcesPanel
        sources={sources}
        open={sourcesOpen}
        onClose={() => setSourcesOpen(false)}
      />
    </div>
  );
}
