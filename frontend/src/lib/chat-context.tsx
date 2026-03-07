"use client";

import {
  createContext,
  useContext,
  useCallback,
  useRef,
  useState,
  useEffect,
} from "react";
import type { Conversation, Message, Source } from "./types";
import {
  listConversations as apiListConversations,
  listMessages as apiListMessages,
  deleteConversation as apiDeleteConversation,
} from "./api";

interface ChatState {
  /** Conversations cache per repo */
  conversationsByRepo: Record<string, Conversation[]>;
  /** Messages cache per conversation */
  messagesByConv: Record<string, Message[]>;
  /** Currently active conversation id */
  activeConversationId: string | null;
  /** Currently active repo */
  activeRepoName: string | null;
  /** Current sources from last response */
  sources: Source[];
  /** Last active conversation per repo (for restore on repo switch) */
  lastActiveByRepo: Record<string, string>;
  /** Which repo is open in the dashboard chat panel */
  dashboardActiveRepo: string | null;
}

interface ChatContextValue extends ChatState {
  /** Load (or use cached) conversations for a repo */
  loadConversations: (repoName: string) => Promise<Conversation[]>;
  /** Load (or use cached) messages for a conversation */
  loadMessages: (conversationId: string) => Promise<Message[]>;
  /** Set active conversation + repo */
  setActiveConversation: (conversationId: string | null, repoName: string) => void;
  /** Update conversations list for a repo (e.g. after stream done) */
  refreshConversations: (repoName: string) => Promise<void>;
  /** Update messages in cache (for streaming updates) */
  setMessages: (messages: Message[] | ((prev: Message[]) => Message[])) => void;
  /** Set sources */
  setSources: (sources: Source[]) => void;
  /** Delete a conversation (API + cache) */
  deleteConversation: (conversationId: string, repoName: string) => void;
  /** Start a new conversation (clear active, keep history) */
  startNewConversation: (repoName: string) => void;
  /** Cache messages for a specific conversation directly */
  cacheMessages: (conversationId: string, messages: Message[]) => void;
  /** Set dashboard active repo */
  setDashboardActiveRepo: (repoName: string | null) => void;
}

const ChatContext = createContext<ChatContextValue | null>(null);

const SESSION_KEY = "memora-chat-active";

interface SessionData {
  convId: string | null;
  repo: string | null;
  dashRepo: string | null;
}

function loadSession(): SessionData {
  if (typeof window === "undefined") return { convId: null, repo: null, dashRepo: null };
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return { convId: null, repo: null, dashRepo: null };
    const parsed = JSON.parse(raw);
    return {
      convId: parsed.convId ?? null,
      repo: parsed.repo ?? null,
      dashRepo: parsed.dashRepo ?? null,
    };
  } catch {
    return { convId: null, repo: null, dashRepo: null };
  }
}

function saveSession(convId: string | null, repo: string | null, dashRepo: string | null) {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify({ convId, repo, dashRepo }));
  } catch {}
}

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<ChatState>(() => {
    const session = loadSession();
    return {
      conversationsByRepo: {},
      messagesByConv: {},
      activeConversationId: session.convId,
      activeRepoName: session.repo,
      sources: [],
      lastActiveByRepo: session.convId && session.repo
        ? { [session.repo]: session.convId }
        : {},
      dashboardActiveRepo: session.dashRepo,
    };
  });

  // Persist to sessionStorage
  useEffect(() => {
    saveSession(state.activeConversationId, state.activeRepoName, state.dashboardActiveRepo);
  }, [state.activeConversationId, state.activeRepoName, state.dashboardActiveRepo]);

  // Track in-flight fetches to avoid duplicates
  const fetchingConvsRef = useRef<Set<string>>(new Set());
  const fetchingMsgsRef = useRef<Set<string>>(new Set());

  const loadConversations = useCallback(async (repoName: string): Promise<Conversation[]> => {
    // Return cached if available
    const cached = state.conversationsByRepo[repoName];
    if (cached) return cached;

    // Avoid duplicate fetches
    if (fetchingConvsRef.current.has(repoName)) {
      return state.conversationsByRepo[repoName] ?? [];
    }

    fetchingConvsRef.current.add(repoName);
    try {
      const convs = await apiListConversations(repoName);
      setState((prev) => ({
        ...prev,
        conversationsByRepo: {
          ...prev.conversationsByRepo,
          [repoName]: convs,
        },
      }));
      return convs;
    } catch {
      return [];
    } finally {
      fetchingConvsRef.current.delete(repoName);
    }
  }, [state.conversationsByRepo]);

  const refreshConversations = useCallback(async (repoName: string): Promise<void> => {
    try {
      const convs = await apiListConversations(repoName);
      setState((prev) => ({
        ...prev,
        conversationsByRepo: {
          ...prev.conversationsByRepo,
          [repoName]: convs,
        },
      }));
    } catch {}
  }, []);

  const loadMessages = useCallback(async (conversationId: string): Promise<Message[]> => {
    // Return cached if available
    const cached = state.messagesByConv[conversationId];
    if (cached) return cached;

    if (fetchingMsgsRef.current.has(conversationId)) {
      return state.messagesByConv[conversationId] ?? [];
    }

    fetchingMsgsRef.current.add(conversationId);
    try {
      const msgs = await apiListMessages(conversationId);
      setState((prev) => ({
        ...prev,
        messagesByConv: {
          ...prev.messagesByConv,
          [conversationId]: msgs,
        },
      }));
      return msgs;
    } catch {
      return [];
    } finally {
      fetchingMsgsRef.current.delete(conversationId);
    }
  }, [state.messagesByConv]);

  const setActiveConversation = useCallback((conversationId: string | null, repoName: string) => {
    setState((prev) => ({
      ...prev,
      activeConversationId: conversationId,
      activeRepoName: repoName,
      sources: conversationId !== prev.activeConversationId ? [] : prev.sources,
      lastActiveByRepo: conversationId
        ? { ...prev.lastActiveByRepo, [repoName]: conversationId }
        : prev.lastActiveByRepo,
    }));
  }, []);

  const setMessages = useCallback((messagesOrFn: Message[] | ((prev: Message[]) => Message[])) => {
    setState((prev) => {
      const convId = prev.activeConversationId;
      if (!convId) return prev;
      const currentMsgs = prev.messagesByConv[convId] ?? [];
      const newMsgs = typeof messagesOrFn === "function" ? messagesOrFn(currentMsgs) : messagesOrFn;
      return {
        ...prev,
        messagesByConv: {
          ...prev.messagesByConv,
          [convId]: newMsgs,
        },
      };
    });
  }, []);

  const setSources = useCallback((sources: Source[]) => {
    setState((prev) => ({ ...prev, sources }));
  }, []);

  const cacheMessages = useCallback((conversationId: string, messages: Message[]) => {
    setState((prev) => ({
      ...prev,
      messagesByConv: {
        ...prev.messagesByConv,
        [conversationId]: messages,
      },
    }));
  }, []);

  const deleteConversation = useCallback((conversationId: string, repoName: string) => {
    apiDeleteConversation(conversationId).catch(() => {});
    setState((prev) => {
      const convs = (prev.conversationsByRepo[repoName] ?? []).filter(
        (c) => c.id !== conversationId,
      );
      const newMessagesByConv = { ...prev.messagesByConv };
      delete newMessagesByConv[conversationId];

      const isActive = prev.activeConversationId === conversationId;
      return {
        ...prev,
        conversationsByRepo: {
          ...prev.conversationsByRepo,
          [repoName]: convs,
        },
        messagesByConv: newMessagesByConv,
        activeConversationId: isActive ? null : prev.activeConversationId,
        sources: isActive ? [] : prev.sources,
      };
    });
  }, []);

  const startNewConversation = useCallback((repoName: string) => {
    setState((prev) => ({
      ...prev,
      activeConversationId: null,
      activeRepoName: repoName,
      sources: [],
    }));
  }, []);

  const setDashboardActiveRepo = useCallback((repoName: string | null) => {
    setState((prev) => ({ ...prev, dashboardActiveRepo: repoName }));
  }, []);

  // Build current messages from cache
  const currentMessages = state.activeConversationId
    ? (state.messagesByConv[state.activeConversationId] ?? [])
    : [];

  const value: ChatContextValue = {
    ...state,
    // Override messagesByConv with direct access pattern isn't needed,
    // consumers use the methods
    loadConversations,
    refreshConversations,
    loadMessages,
    setActiveConversation,
    setMessages,
    setSources,
    cacheMessages,
    deleteConversation,
    startNewConversation,
    setDashboardActiveRepo,
  };

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  );
}

export function useChatContext(): ChatContextValue {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChatContext must be used within ChatProvider");
  return ctx;
}
