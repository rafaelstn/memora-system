"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import type { Message, Source } from "@/lib/types";
import { askQuestionStream } from "@/lib/api";
import { useChatContext } from "@/lib/chat-context";
import { MessageBubble } from "./message-bubble";
import { ChatInput } from "./chat-input";
import { SourcesPanel } from "./sources-panel";
import { cn } from "@/lib/utils";
import toast from "react-hot-toast";
import {
  X,
  BookOpen,
  Code2,
  GitBranch,
  Sparkles,
  MessageSquareText,
  Trash2,
} from "lucide-react";
import { ModelSelector } from "./model-selector";

interface ChatPanelProps {
  repoName: string;
  onClose: () => void;
}

export function ChatPanel({ repoName, onClose }: ChatPanelProps) {
  const chat = useChatContext();

  // Local UI state
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isError, setIsError] = useState(false);
  const [selectedProviderId, setSelectedProviderId] = useState<string | null>(null);

  // Streaming state (local during active stream, flushed to context on done)
  const [streamingMessages, setStreamingMessages] = useState<Message[] | null>(null);
  const streamConvIdRef = useRef<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const initRef = useRef(false);

  // Load conversations on mount / repo change
  useEffect(() => {
    initRef.current = false;
  }, [repoName]);

  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;

    (async () => {
      const convs = await chat.loadConversations(repoName);

      // Restore last active conversation for this repo
      const lastId = chat.lastActiveByRepo[repoName];
      if (lastId && convs.some((c) => c.id === lastId)) {
        chat.setActiveConversation(lastId, repoName);
        await chat.loadMessages(lastId);
      } else if (convs.length > 0) {
        chat.setActiveConversation(convs[0].id, repoName);
        await chat.loadMessages(convs[0].id);
      } else {
        chat.setActiveConversation(null, repoName);
      }
    })();
  }, [repoName]); // eslint-disable-line react-hooks/exhaustive-deps

  // Messages: use streaming if active, otherwise context
  const contextMessages = chat.activeConversationId
    ? (chat.messagesByConv[chat.activeConversationId] ?? [])
    : [];
  const messages = streamingMessages ?? contextMessages;
  const sources = chat.sources;

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  function handleClearHistory() {
    abortRef.current?.abort();
    if (chat.activeConversationId) {
      chat.deleteConversation(chat.activeConversationId, repoName);
    }
    setStreamingMessages(null);
    setSourcesOpen(false);
    setIsLoading(false);
    setIsError(false);
  }

  const handleSend = useCallback(
    async (content: string) => {
      const userMsg: Message = {
        id: `m-${Date.now()}`,
        conversation_id: chat.activeConversationId || "pending",
        role: "user",
        content,
        created_at: new Date().toISOString(),
      };

      const assistantMsgId = `m-${Date.now()}-a`;

      // Start streaming with current messages + new user msg
      const currentMsgs = chat.activeConversationId
        ? (chat.messagesByConv[chat.activeConversationId] ?? [])
        : [];
      setStreamingMessages([...currentMsgs, userMsg]);
      setIsLoading(true);
      setIsError(false);
      streamConvIdRef.current = null;

      const controller = await askQuestionStream(
        repoName,
        content,
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
            return [
              ...prev,
              {
                id: assistantMsgId,
                conversation_id: streamConvIdRef.current || "pending",
                role: "assistant" as const,
                content: text,
                created_at: new Date().toISOString(),
              },
            ];
          });
        },
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
        (meta) => {
          // Stream done — flush to context
          setIsLoading(false);
          setStreamingMessages((prev) => {
            if (!prev) return null;
            const last = prev[prev.length - 1];
            let finalMsgs = prev;
            if (last && last.id === assistantMsgId) {
              finalMsgs = [
                ...prev.slice(0, -1),
                {
                  ...last,
                  model_used: meta.model,
                  tokens_used: meta.tokens,
                  cost_usd: meta.cost_usd,
                  provider_name: meta.provider_name,
                  provider: meta.provider,
                },
              ];
            }

            // Flush to context cache
            const convId = streamConvIdRef.current;
            if (convId) {
              chat.cacheMessages(convId, finalMsgs);
              chat.setActiveConversation(convId, repoName);
              chat.refreshConversations(repoName);
            }

            return null; // Clear streaming state
          });
        },
        (error) => {
          setIsLoading(false);
          setIsError(true);
          setStreamingMessages(null);
          toast.error(error || "Erro ao processar a pergunta");
        },
        selectedProviderId,
        chat.activeConversationId,
        (convId) => {
          // Backend tells us the conversation ID
          streamConvIdRef.current = convId;
        },
      );

      abortRef.current = controller;
    },
    [repoName, selectedProviderId, chat],
  );

  const handleRetry = useCallback(() => {
    const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
    if (lastUserMsg) {
      // Remove last assistant message if error
      if (chat.activeConversationId) {
        const currentMsgs = chat.messagesByConv[chat.activeConversationId] ?? [];
        const last = currentMsgs[currentMsgs.length - 1];
        if (last && last.role === "assistant") {
          chat.cacheMessages(chat.activeConversationId, currentMsgs.slice(0, -1));
        }
      }
      setIsError(false);
      handleSend(lastUserMsg.content);
    }
  }, [messages, handleSend, chat]);

  const suggestions = [
    {
      icon: Code2,
      title: "Arquitetura",
      question: `Como o ${repoName} está estruturado?`,
    },
    {
      icon: GitBranch,
      title: "Fluxo principal",
      question: `Qual o fluxo principal do ${repoName}?`,
    },
    {
      icon: Sparkles,
      title: "Funcionalidades",
      question: `Quais as principais funcionalidades?`,
    },
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-card-bg shrink-0">
        <div className="flex items-center gap-2">
          <MessageSquareText className="h-4 w-4 text-accent" />
          <h2 className="text-sm font-semibold">{repoName}</h2>
          <div className="border-l border-border pl-2 ml-1">
            <ModelSelector selectedId={selectedProviderId} onSelect={setSelectedProviderId} />
          </div>
        </div>
        <div className="flex items-center gap-1">
          {messages.length > 0 && (
            <button
              onClick={handleClearHistory}
              className="flex items-center gap-1 px-2 py-1 rounded-lg text-xs text-muted hover:text-danger hover:bg-danger-surface transition-colors"
              title="Limpar histórico"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          )}
          <button
            onClick={() => setSourcesOpen((prev) => !prev)}
            className={cn(
              "flex items-center gap-1 px-2 py-1 rounded-md text-xs transition-colors",
              sourcesOpen
                ? "bg-accent-surface text-accent-text"
                : "text-muted hover:bg-hover"
            )}
          >
            <BookOpen className="h-3.5 w-3.5" />
            {sources.length > 0 && (
              <span className="bg-accent text-white text-[10px] rounded-full px-1 min-w-[16px] text-center">
                {sources.length}
              </span>
            )}
          </button>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-muted hover:text-foreground hover:bg-hover transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex flex-1 min-h-0">
        {/* Messages */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex-1 overflow-y-auto">
            {messages.length === 0 && !isLoading ? (
              <div className="flex flex-col items-center justify-center h-full text-center px-4">
                <div className="h-12 w-12 rounded-2xl bg-accent-surface flex items-center justify-center mb-3">
                  <MessageSquareText className="h-6 w-6 text-accent" />
                </div>
                <p className="text-sm text-muted mb-4">
                  Pergunte sobre <span className="text-foreground font-medium">{repoName}</span>
                </p>
                <div className="grid gap-2 w-full max-w-sm">
                  {suggestions.map((s, i) => (
                    <button
                      key={i}
                      onClick={() => handleSend(s.question)}
                      className="flex items-center gap-2 p-3 rounded-xl border border-border bg-card-bg hover:border-accent/40 hover:bg-hover text-left transition-colors text-xs"
                    >
                      <s.icon className="h-4 w-4 text-accent shrink-0" />
                      <span className="text-muted">{s.question}</span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="px-4 py-3">
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
          <ChatInput onSend={handleSend} />
        </div>

        {/* Sources panel inline */}
        {sourcesOpen && (
          <SourcesPanel
            sources={sources}
            open={sourcesOpen}
            onClose={() => setSourcesOpen(false)}
          />
        )}
      </div>
    </div>
  );
}
