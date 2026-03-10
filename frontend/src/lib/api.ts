import { getAccessToken } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// --- Active Product ID (set by ProductContext) ---
let _activeProductId: string | null = null;

export function setActiveProductId(id: string | null) {
  _activeProductId = id;
}

export function getActiveProductId(): string | null {
  return _activeProductId;
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  const token = await getAccessToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (_activeProductId) headers["X-Product-ID"] = _activeProductId;
  return headers;
}

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "ngrok-skip-browser-warning": "true",
      ...authHeaders,
      ...options?.headers,
    },
  });
  if (!res.ok) {
    if (res.status === 402) {
      // Plan expired — redirect to upgrade page
      if (typeof window !== "undefined") {
        window.location.href = "/upgrade";
      }
      throw new Error("Seu trial expirou. Redirecionando...");
    }
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `API error: ${res.status}`);
  }
  return res.json();
}

// --- Profile ---

export async function updateProfile(data: { name?: string; avatar_url?: string }) {
  return apiFetch<Record<string, unknown>>("/api/auth/profile", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function changePassword(newPassword: string) {
  return apiFetch<{ message: string }>("/api/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ new_password: newPassword }),
  });
}

// --- Conversations ---
import type { Conversation, Message } from "./types";

export async function listConversations(repoName: string) {
  return apiFetch<Conversation[]>(
    `/api/conversations?repo_name=${encodeURIComponent(repoName)}`,
  );
}

export async function createConversation(repoName: string, userId: string, title: string) {
  return apiFetch<{ id: string; repo_name: string; title: string }>("/api/conversations", {
    method: "POST",
    body: JSON.stringify({ repo_name: repoName, user_id: userId, title }),
  });
}

export async function deleteConversation(convId: string) {
  return apiFetch<{ deleted: boolean }>(`/api/conversations/${convId}`, {
    method: "DELETE",
  });
}

export async function listMessages(convId: string) {
  return apiFetch<Message[]>(`/api/conversations/${convId}/messages`);
}

// --- Ask ---
export async function askQuestion(
  repoName: string,
  question: string,
  maxChunks = 5,
) {
  return apiFetch<{
    answer: string;
    sources: Array<{
      file: string;
      chunk_name: string;
      content_preview: string;
    }>;
  }>("/api/ask", {
    method: "POST",
    body: JSON.stringify({
      question,
      repo_name: repoName,
      max_chunks: maxChunks,
    }),
  });
}

// --- SSE streaming ask ---
export async function askQuestionStream(
  repoName: string,
  question: string,
  onText: (text: string) => void,
  onSources: (sources: Array<{
    file_path: string;
    chunk_name: string;
    chunk_type: string;
    content_preview: string;
    start_line?: number;
  }>) => void,
  onDone: (meta: { tokens: number; cost_usd: number; model: string; provider_name?: string; provider?: string }) => void,
  onError: (error: string) => void,
  providerId?: string | null,
  conversationId?: string | null,
  onConversation?: (conversationId: string) => void,
) {
  const controller = new AbortController();
  const authHeaders = await getAuthHeaders();

  const body: Record<string, unknown> = {
    question,
    repo_name: repoName,
  };
  if (providerId) body.provider_id = providerId;
  if (conversationId) body.conversation_id = conversationId;

  const streamHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    "ngrok-skip-browser-warning": "true",
    ...authHeaders,
  };
  if (_activeProductId) streamHeaders["X-Product-ID"] = _activeProductId;

  fetch(`${API_BASE}/api/ask/stream`, {
    method: "POST",
    headers: streamHeaders,
    body: JSON.stringify(body),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        onError(body.detail || `Erro ${res.status}`);
        return;
      }
      const reader = res.body?.getReader();
      if (!reader) return;

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const jsonStr = line.slice(6);
          if (jsonStr === "[DONE]") return;

          try {
            const event = JSON.parse(jsonStr);
            if (event.type === "text") onText(event.content);
            else if (event.type === "sources") onSources(event.sources);
            else if (event.type === "done") onDone(event);
            else if (event.type === "error") onError(event.message);
            else if (event.type === "conversation" && onConversation) onConversation(event.conversation_id);
          } catch {
            // skip malformed JSON
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError(err.message);
      }
    });

  return controller;
}

// --- Ingest ---
export async function ingestRepository(repoPath: string, repoName?: string) {
  return apiFetch<{
    repo_name: string;
    files_processed: number;
    chunks_created: number;
  }>("/api/ingest", {
    method: "POST",
    body: JSON.stringify({ repo_path: repoPath, repo_name: repoName }),
  });
}

// --- Ingest with SSE progress ---
export async function ingestRepositoryStream(
  repoPath: string,
  repoName: string | undefined,
  onProgress: (stage: string, percent: number, detail: string) => void,
  onResult: (result: { repo_name: string; files_processed: number; chunks_created: number }) => void,
  onError: (error: string) => void,
) {
  const authHeaders = await getAuthHeaders();

  const res = await fetch(`${API_BASE}/api/ingest/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "ngrok-skip-browser-warning": "true",
      ...authHeaders,
    },
    body: JSON.stringify({ repo_path: repoPath, repo_name: repoName }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    onError(body.detail || `Erro ${res.status}`);
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const jsonStr = line.slice(6);
      if (jsonStr === "[DONE]") return;

      try {
        const event = JSON.parse(jsonStr);
        if (event.type === "progress") {
          onProgress(event.stage, event.percent, event.detail);
        } else if (event.type === "result") {
          onResult(event);
        } else if (event.type === "error") {
          onError(event.message);
        }
      } catch {
        // skip malformed JSON
      }
    }
  }
}

// --- Repos ---
export async function listRepos() {
  return apiFetch<Array<{
    name: string;
    chunks_count: number;
    last_indexed?: string;
    status: string;
  }>>("/api/repos");
}

// --- Health ---
export async function getHealth() {
  return apiFetch<{ status: string; version: string }>("/api/health");
}

// --- Admin: Metrics ---
export async function getMetrics() {
  return apiFetch<{
    total_questions: number;
    total_cost_brl: number;
    avg_cost_per_question_brl: number;
    active_users_7d: number;
  }>("/api/admin/metrics");
}

export async function getDailyUsage(days = 30) {
  return apiFetch<Array<{ date: string; questions: number; cost_brl: number }>>(
    `/api/admin/metrics/daily?days=${days}`,
  );
}

export async function getUserUsage() {
  return apiFetch<Array<{
    user_id: string;
    name: string;
    role: string;
    total_questions: number;
    total_cost_brl: number;
    last_activity: string | null;
  }>>("/api/admin/metrics/users");
}

export async function getModelUsage() {
  return apiFetch<Array<{
    model: string;
    questions: number;
    cost_usd: number;
    percentage: number;
  }>>("/api/admin/metrics/models");
}

export async function listAdminRepos() {
  return apiFetch<Array<{
    name: string;
    chunks_count: number;
    last_indexed?: string;
    status: string;
  }>>("/api/admin/repos");
}

export async function deleteAdminRepo(repoName: string) {
  return apiFetch<{ deleted: boolean; repo_name: string; chunks_removed: number }>(
    `/api/admin/repos/${encodeURIComponent(repoName)}`,
    { method: "DELETE" },
  );
}

// --- GitHub Integration ---
export async function connectGitHub(token: string) {
  return apiFetch<{
    connected: boolean;
    github_login: string;
    github_avatar_url: string;
    scopes: string;
  }>("/api/integrations/github", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}

export async function getGitHubStatus() {
  return apiFetch<{
    connected: boolean;
    github_login?: string;
    github_avatar_url?: string;
    scopes?: string;
    connected_at?: string;
  }>("/api/integrations/github");
}

export async function listGitHubRepos() {
  return apiFetch<Array<{
    name: string;
    full_name: string;
    private: boolean;
    url: string;
    language: string | null;
    updated_at: string | null;
    default_branch: string;
  }>>("/api/integrations/github/repos");
}

export async function disconnectGitHub() {
  return apiFetch<{ connected: boolean; message: string }>("/api/integrations/github", {
    method: "DELETE",
  });
}

// --- Admin: Users ---
export async function listUsers(role?: string, search?: string) {
  const params = new URLSearchParams();
  if (role) params.set("role", role);
  if (search) params.set("search", search);
  const qs = params.toString();
  return apiFetch<Array<{
    id: string;
    name: string;
    email: string;
    role: string;
    is_active: boolean;
    created_at: string;
    last_activity?: string;
  }>>(`/api/admin/users${qs ? `?${qs}` : ""}`);
}

export async function updateUserRole(userId: string, role: string) {
  return apiFetch<{ updated: boolean }>(`/api/admin/users/${userId}/role`, {
    method: "PATCH",
    body: JSON.stringify({ role }),
  });
}

export async function toggleUserActive(userId: string) {
  return apiFetch<{ toggled: boolean }>(`/api/admin/users/${userId}/deactivate`, {
    method: "PATCH",
  });
}

// --- Admin: Invites ---
export async function listInvites() {
  return apiFetch<Array<{
    id: string;
    token: string;
    role: string;
    email?: string;
    created_at: string;
    expires_at: string;
    status: string;
  }>>("/api/admin/invites");
}

export async function createInvite(role: string, email?: string, productId?: string) {
  return apiFetch<{
    id: string;
    token: string;
    role: string;
    product_id: string | null;
    invite_url: string;
    expires_at: string;
  }>("/api/admin/invites", {
    method: "POST",
    body: JSON.stringify({ role, email: email || null, product_id: productId || null }),
  });
}

export async function revokeInviteApi(inviteId: string) {
  return apiFetch<{ revoked: boolean }>(`/api/admin/invites/${inviteId}`, {
    method: "DELETE",
  });
}

// --- Users search ---
export async function searchUsers(email: string) {
  return apiFetch<Array<{
    id: string;
    name: string;
    email: string;
    role: string;
    created_at: string;
  }>>(`/api/users/search?email=${encodeURIComponent(email)}`);
}


// --- Monitor de Erros ---
import type {
  AlertWebhook,
  ErrorAlertDetail,
  ErrorAlertSummary,
  LLMProvider,
  LLMProviderActive,
  LLMProviderType,
  LogEntry,
  MonitoredProject,
  MonitoredProjectCreated,
  MonitoredProjectDetail,
} from "./types";

export async function listMonitorProjects() {
  return apiFetch<MonitoredProject[]>("/api/monitor/projects");
}

export async function getMonitorProject(id: string) {
  return apiFetch<MonitoredProjectDetail>(`/api/monitor/projects/${id}`);
}

export async function createMonitorProject(data: { name: string; description?: string }) {
  return apiFetch<MonitoredProjectCreated>("/api/monitor/projects", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteMonitorProject(id: string) {
  return apiFetch<{ deleted: boolean }>(`/api/monitor/projects/${id}`, { method: "DELETE" });
}

export async function rotateProjectToken(id: string) {
  return apiFetch<{ token: string; token_preview: string }>(
    `/api/monitor/projects/${id}/rotate-token`,
    { method: "POST" },
  );
}

export async function listMonitorAlerts(params?: {
  project_id?: string;
  severity?: string;
  status?: string;
  page?: number;
}) {
  const qs = new URLSearchParams();
  if (params?.project_id) qs.set("project_id", params.project_id);
  if (params?.severity) qs.set("severity", params.severity);
  if (params?.status) qs.set("status", params.status);
  if (params?.page) qs.set("page", String(params.page));
  const q = qs.toString();
  return apiFetch<ErrorAlertSummary[]>(`/api/monitor/alerts${q ? `?${q}` : ""}`);
}

export async function getMonitorAlert(id: string) {
  return apiFetch<ErrorAlertDetail>(`/api/monitor/alerts/${id}`);
}

export async function updateAlertStatus(id: string, status: "acknowledged" | "resolved") {
  return apiFetch<{ updated: boolean }>(`/api/monitor/alerts/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export async function listMonitorLogs(params?: {
  project_id?: string;
  level?: string;
  page?: number;
}) {
  const qs = new URLSearchParams();
  if (params?.project_id) qs.set("project_id", params.project_id);
  if (params?.level) qs.set("level", params.level);
  if (params?.page) qs.set("page", String(params.page));
  const q = qs.toString();
  return apiFetch<LogEntry[]>(`/api/monitor/logs${q ? `?${q}` : ""}`);
}

export async function listAlertWebhooks() {
  return apiFetch<AlertWebhook[]>("/api/monitor/webhooks");
}

export async function createAlertWebhook(data: { name: string; url: string }) {
  return apiFetch<{ id: string; name: string; url: string }>("/api/monitor/webhooks", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteAlertWebhook(id: string) {
  return apiFetch<{ deleted: boolean }>(`/api/monitor/webhooks/${id}`, { method: "DELETE" });
}

export async function testAlertWebhook(id: string) {
  return apiFetch<{ status: string; http_status?: number; error?: string }>(
    `/api/monitor/webhooks/${id}/test`,
    { method: "POST" },
  );
}

// --- LLM Providers ---

export async function listLLMProviders() {
  return apiFetch<LLMProvider[]>("/api/llm-providers");
}

export async function listActiveLLMProviders() {
  return apiFetch<LLMProviderActive[]>("/api/llm-providers/active");
}

export async function createLLMProvider(data: {
  name: string;
  provider: LLMProviderType;
  model_id: string;
  api_key?: string;
  base_url?: string;
}) {
  return apiFetch<LLMProvider>("/api/llm-providers", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateLLMProvider(
  id: string,
  data: { name?: string; model_id?: string; api_key?: string; base_url?: string },
) {
  return apiFetch<LLMProvider>(`/api/llm-providers/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteLLMProvider(id: string) {
  return apiFetch<{ deleted: boolean }>(`/api/llm-providers/${id}`, {
    method: "DELETE",
  });
}

export async function setDefaultLLMProvider(id: string) {
  return apiFetch<{ default: boolean; provider_id: string }>(
    `/api/llm-providers/${id}/set-default`,
    { method: "POST" },
  );
}

export async function testLLMProvider(id: string) {
  return apiFetch<{ status: string; latency_ms: number; error?: string; response?: string }>(
    `/api/llm-providers/${id}/test`,
    { method: "POST" },
  );
}

export async function testLLMConnection(data: {
  provider: string;
  model_id: string;
  api_key?: string;
  base_url?: string;
}) {
  return apiFetch<{ status: string; latency_ms: number; error?: string; response?: string }>(
    "/api/llm-providers/test-connection",
    { method: "POST", body: JSON.stringify(data) },
  );
}

// --- Memoria Tecnica ---
import type {
  KnowledgeDocument,
  KnowledgeEntry,
  KnowledgeEntryDetail,
  KnowledgeSearchResult,
  KnowledgeStats,
  KnowledgeWiki,
  KnowledgeWikiDetail,
} from "./types";

export async function searchKnowledge(params: {
  q: string;
  repo_id?: string;
  source_type?: string;
  decision_type?: string;
}) {
  const qs = new URLSearchParams({ q: params.q });
  if (params.repo_id) qs.set("repo_id", params.repo_id);
  if (params.source_type) qs.set("source_type", params.source_type);
  if (params.decision_type) qs.set("decision_type", params.decision_type);
  return apiFetch<KnowledgeSearchResult[]>(`/api/knowledge/search?${qs}`);
}

export async function listKnowledgeEntries(params?: {
  repo_id?: string;
  source_type?: string;
  decision_type?: string;
  page?: number;
}) {
  const qs = new URLSearchParams();
  if (params?.repo_id) qs.set("repo_id", params.repo_id);
  if (params?.source_type) qs.set("source_type", params.source_type);
  if (params?.decision_type) qs.set("decision_type", params.decision_type);
  if (params?.page) qs.set("page", String(params.page));
  const q = qs.toString();
  return apiFetch<KnowledgeEntry[]>(`/api/knowledge/entries${q ? `?${q}` : ""}`);
}

export async function getKnowledgeEntry(id: string) {
  return apiFetch<KnowledgeEntryDetail>(`/api/knowledge/entries/${id}`);
}

export async function getKnowledgeTimeline(params?: {
  repo_id?: string;
  file_path?: string;
  source_type?: string;
  period?: string;
  page?: number;
}) {
  const qs = new URLSearchParams();
  if (params?.repo_id) qs.set("repo_id", params.repo_id);
  if (params?.file_path) qs.set("file_path", params.file_path);
  if (params?.source_type) qs.set("source_type", params.source_type);
  if (params?.period) qs.set("period", params.period);
  if (params?.page) qs.set("page", String(params.page));
  const q = qs.toString();
  return apiFetch<KnowledgeEntry[]>(`/api/knowledge/timeline${q ? `?${q}` : ""}`);
}

export async function createADR(data: {
  title: string;
  content: string;
  repo_id?: string;
  file_paths?: string[];
  decision_type?: string;
}) {
  return apiFetch<{ id: string; title: string }>("/api/knowledge/adrs", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateADR(
  id: string,
  data: { title?: string; content?: string; file_paths?: string[]; decision_type?: string },
) {
  return apiFetch<{ updated: boolean }>(`/api/knowledge/adrs/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteADR(id: string) {
  return apiFetch<{ deleted: boolean }>(`/api/knowledge/adrs/${id}`, { method: "DELETE" });
}

export async function uploadKnowledgeDocument(file: File, repoId?: string) {
  const formData = new FormData();
  formData.append("file", file);
  const authHeaders = await getAuthHeaders();
  const qs = repoId ? `?repo_id=${repoId}` : "";
  const res = await fetch(`${API_BASE}/api/knowledge/documents${qs}`, {
    method: "POST",
    headers: { "ngrok-skip-browser-warning": "true", ...authHeaders },
    body: formData,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `API error: ${res.status}`);
  }
  return res.json() as Promise<{ document_id: string; status: string }>;
}

export async function listKnowledgeDocuments(page?: number) {
  const qs = page ? `?page=${page}` : "";
  return apiFetch<KnowledgeDocument[]>(`/api/knowledge/documents${qs}`);
}

export async function getDocumentStatus(id: string) {
  return apiFetch<{ processed: boolean; entry_id?: string; status: string }>(
    `/api/knowledge/documents/${id}/status`,
  );
}

export async function deleteKnowledgeDocument(id: string) {
  return apiFetch<{ deleted: boolean }>(`/api/knowledge/documents/${id}`, { method: "DELETE" });
}

export async function listKnowledgeWikis(repoId?: string) {
  const qs = repoId ? `?repo_id=${repoId}` : "";
  return apiFetch<KnowledgeWiki[]>(`/api/knowledge/wikis${qs}`);
}

export async function getKnowledgeWiki(id: string) {
  return apiFetch<KnowledgeWikiDetail>(`/api/knowledge/wiki/${id}`);
}

export async function generateWiki(data: {
  repo_id: string;
  component_path: string;
  component_name?: string;
}) {
  return apiFetch<{ status: string; component_path: string }>("/api/knowledge/wiki/generate", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getWikiSuggestions() {
  return apiFetch<import("./types").WikiSuggestion[]>("/api/knowledge/wiki/suggestions");
}

export async function generateWikiBatch(components: { path: string; name?: string; repo_id?: string }[]) {
  return apiFetch<{ status: string; count: number }>("/api/knowledge/wiki/generate-batch", {
    method: "POST",
    body: JSON.stringify({ components }),
  });
}

export async function deleteWiki(id: string) {
  return apiFetch<{ deleted: boolean }>(`/api/knowledge/wiki/${id}`, { method: "DELETE" });
}

export async function syncKnowledgeRepo(repoName: string) {
  return apiFetch<{ status: string; repo_name: string }>(
    `/api/knowledge/sync/${encodeURIComponent(repoName)}`,
    { method: "POST" },
  );
}

export async function getKnowledgeStats() {
  return apiFetch<KnowledgeStats>("/api/knowledge/stats");
}

export async function getKnowledgeSettings() {
  return apiFetch<{ auto_wiki: boolean; auto_sync: boolean }>("/api/knowledge/settings");
}

export async function updateKnowledgeSettings(data: { auto_wiki: boolean; auto_sync: boolean }) {
  return apiFetch<{ auto_wiki: boolean; auto_sync: boolean }>("/api/knowledge/settings", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

// --- Revisao de Codigo ---
import type {
  CodeReviewDetail,
  CodeReviewSummary,
  ReviewStats,
} from "./types";

export async function listReviews(params?: {
  repo_id?: string;
  source_type?: string;
  verdict?: string;
  page?: number;
}) {
  const qs = new URLSearchParams();
  if (params?.repo_id) qs.set("repo_id", params.repo_id);
  if (params?.source_type) qs.set("source_type", params.source_type);
  if (params?.verdict) qs.set("verdict", params.verdict);
  if (params?.page) qs.set("page", String(params.page));
  const q = qs.toString();
  return apiFetch<CodeReviewSummary[]>(`/api/reviews${q ? `?${q}` : ""}`);
}

export async function getReview(id: string) {
  return apiFetch<CodeReviewDetail>(`/api/reviews/${id}`);
}

export async function getReviewStats() {
  return apiFetch<ReviewStats>("/api/reviews/stats");
}

export async function createManualReview(data: {
  code: string;
  language: string;
  context?: string;
  repo_id?: string;
}) {
  return apiFetch<{ review_id: string; status: string }>("/api/reviews/manual", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteReview(id: string) {
  return apiFetch<{ deleted: boolean }>(`/api/reviews/${id}`, { method: "DELETE" });
}

// --- Documentacao Automatica ---
import type { RepoDocStatus, RepoDoc, OnboardingProgress, OnboardingStepResult } from "./types";

export async function generateDocs(repoName: string, docType: string) {
  return apiFetch<{ status: string; repo_name: string; doc_type: string }>(
    `/api/docs/generate/${encodeURIComponent(repoName)}`,
    { method: "POST", body: JSON.stringify({ doc_type: docType }) },
  );
}

export async function getDocsStatus(repoName: string) {
  return apiFetch<RepoDocStatus>(`/api/docs/status/${encodeURIComponent(repoName)}`);
}

export async function getReadme(repoName: string) {
  return apiFetch<RepoDoc>(`/api/docs/${encodeURIComponent(repoName)}/readme`);
}

export async function getOnboardingGuide(repoName: string) {
  return apiFetch<RepoDoc>(`/api/docs/${encodeURIComponent(repoName)}/onboarding`);
}

export async function pushReadmeToGitHub(repoName: string, commitMessage?: string) {
  return apiFetch<{ status: string; repo_name: string; commit_message: string }>(
    `/api/docs/${encodeURIComponent(repoName)}/push-to-github`,
    { method: "POST", body: JSON.stringify({ commit_message: commitMessage }) },
  );
}

export async function getOnboardingProgress(repoName: string) {
  return apiFetch<OnboardingProgress>(`/api/onboarding/${encodeURIComponent(repoName)}/progress`);
}

export async function completeOnboardingStep(repoName: string, stepId: string) {
  return apiFetch<OnboardingStepResult>(
    `/api/onboarding/${encodeURIComponent(repoName)}/progress`,
    { method: "POST", body: JSON.stringify({ step_id: stepId }) },
  );
}

// --- Regras de Negocio ---
import type {
  RulesListResponse,
  BusinessRuleDetail,
  BusinessRuleSummary,
  RuleChangeAlert,
  RuleSimulationResult,
  RuleExtractStatus,
} from "./types";

export async function listRules(repoName?: string, ruleType?: string, page = 1) {
  const params = new URLSearchParams();
  if (repoName) params.set("repo_name", repoName);
  if (ruleType) params.set("rule_type", ruleType);
  params.set("page", String(page));
  return apiFetch<RulesListResponse>(`/api/rules?${params}`);
}

export async function getRule(ruleId: string) {
  return apiFetch<BusinessRuleDetail>(`/api/rules/${ruleId}`);
}

export async function searchRules(query: string, repoName?: string) {
  const params = new URLSearchParams({ q: query });
  if (repoName) params.set("repo_name", repoName);
  return apiFetch<Array<BusinessRuleSummary & { score: number; description: string }>>(`/api/rules/search?${params}`);
}

export async function extractRules(repoName: string) {
  return apiFetch<{ status: string; repo_name: string }>(
    `/api/rules/extract/${encodeURIComponent(repoName)}`,
    { method: "POST" },
  );
}

export async function getExtractStatus(repoName: string) {
  return apiFetch<RuleExtractStatus>(`/api/rules/extract/status/${encodeURIComponent(repoName)}`);
}

export async function simulateRule(ruleId: string, inputValues: Record<string, unknown>) {
  return apiFetch<RuleSimulationResult>(`/api/rules/${ruleId}/simulate`, {
    method: "POST",
    body: JSON.stringify({ input_values: inputValues }),
  });
}

export async function listRuleAlerts(repoName?: string, acknowledged = false) {
  const params = new URLSearchParams({ acknowledged: String(acknowledged) });
  if (repoName) params.set("repo_name", repoName);
  return apiFetch<RuleChangeAlert[]>(`/api/rules/alerts?${params}`);
}

export async function acknowledgeRuleAlert(alertId: string) {
  return apiFetch<{ acknowledged: boolean }>(`/api/rules/alerts/${alertId}/acknowledge`, {
    method: "PATCH",
  });
}

// --- Code Generation ---

import type { CodeGenHistoryResponse, CodeGenDetail, McpTokenStatus, McpTokenGenerated, McpHealth } from "./types";

export async function generateCodeStream(
  body: { description: string; type: string; repo_name: string; file_path?: string; use_context?: boolean },
  onEvent: (event: Record<string, unknown>) => void,
) {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/api/codegen/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "ngrok-skip-browser-warning": "true", ...authHeaders },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `API error: ${res.status}`);
  }

  const reader = res.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const data = JSON.parse(line.slice(6));
          onEvent(data);
        } catch {}
      }
    }
  }
}

export async function getCodeGenHistory(page = 1) {
  return apiFetch<CodeGenHistoryResponse>(`/api/codegen/history?page=${page}`);
}

export async function getCodeGenDetail(genId: string) {
  return apiFetch<CodeGenDetail>(`/api/codegen/${genId}`);
}

// --- MCP Token ---

export async function getMcpTokenStatus() {
  return apiFetch<McpTokenStatus>("/api/mcp/token/status");
}

export async function generateMcpToken() {
  return apiFetch<McpTokenGenerated>("/api/mcp/token", { method: "POST" });
}

export async function revokeMcpToken() {
  return apiFetch<{ revoked: boolean }>("/api/mcp/token", { method: "DELETE" });
}

export async function testMcpHealth(token: string) {
  const res = await fetch(`${API_BASE}/mcp/health`, {
    headers: { Authorization: `Bearer ${token}`, "ngrok-skip-browser-warning": "true" },
  });
  if (!res.ok) throw new Error(`MCP error: ${res.status}`);
  return res.json() as Promise<McpHealth>;
}

// --- Incidents ---
import type {
  Incident,
  IncidentListResponse,
  IncidentStats,
  IncidentTimelineEvent,
  SimilarIncident,
  PublicPostmortem,
} from "./types";

export async function declareIncident(body: {
  alert_id?: string;
  project_id: string;
  title?: string;
  description?: string;
  severity: string;
}) {
  return apiFetch<{ id: string; title: string; severity: string; status: string }>(
    "/api/incidents",
    { method: "POST", body: JSON.stringify(body) },
  );
}

export async function listIncidents(params?: {
  status?: string;
  project_id?: string;
  page?: number;
}) {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.project_id) qs.set("project_id", params.project_id);
  if (params?.page) qs.set("page", String(params.page));
  return apiFetch<IncidentListResponse>(`/api/incidents?${qs.toString()}`);
}

export async function getIncident(id: string) {
  return apiFetch<Incident>(`/api/incidents/${id}`);
}

export async function getIncidentTimeline(id: string) {
  return apiFetch<{ events: IncidentTimelineEvent[] }>(`/api/incidents/${id}/timeline`);
}

export async function getIncidentStats() {
  return apiFetch<IncidentStats>("/api/incidents/stats");
}

export async function updateIncidentStatus(
  id: string,
  body: { status: string; resolution_summary?: string },
) {
  return apiFetch<{ id: string; status: string }>(`/api/incidents/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function addTimelineEvent(
  id: string,
  body: { content: string; event_type: string },
) {
  return apiFetch<{ id: string; event_type: string; content: string }>(
    `/api/incidents/${id}/timeline`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export async function updateHypothesis(
  incidentId: string,
  hypothesisId: string,
  body: { status: "confirmed" | "discarded" },
) {
  return apiFetch<{ id: string; status: string }>(
    `/api/incidents/${incidentId}/hypotheses/${hypothesisId}`,
    { method: "PATCH", body: JSON.stringify(body) },
  );
}

export async function getSimilarIncidents(id: string) {
  return apiFetch<{ similar: SimilarIncident[]; computing?: boolean }>(
    `/api/incidents/${id}/similar`,
  );
}

export async function createShareToken(id: string) {
  return apiFetch<{ share_token: string; public_url: string }>(
    `/api/incidents/${id}/share`,
    { method: "POST" },
  );
}

export async function revokeShareToken(id: string) {
  return apiFetch<{ status: string }>(
    `/api/incidents/${id}/share`,
    { method: "DELETE" },
  );
}

export async function getPublicPostmortem(token: string) {
  return apiFetch<PublicPostmortem>(`/api/postmortem/${token}`);
}

// --- Impact Analysis ---
import type { ImpactAnalysis, ImpactHistoryResponse } from "./types";

export async function startImpactAnalysis(body: {
  change_description: string;
  repo_name: string;
  affected_files?: string[];
}) {
  return apiFetch<{ analysis_id: string; status: string }>("/api/impact/analyze", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getImpactAnalysis(id: string) {
  return apiFetch<ImpactAnalysis>(`/api/impact/${id}`);
}


export async function listImpactHistory(params?: { repo_name?: string; page?: number }) {
  const qs = new URLSearchParams();
  if (params?.repo_name) qs.set("repo_name", params.repo_name);
  if (params?.page) qs.set("page", String(params.page));
  return apiFetch<ImpactHistoryResponse>(`/api/impact/history/list?${qs.toString()}`);
}

// --- Executive Dashboard ---
import type {
  ExecutiveSnapshot,
  ExecutiveRealtimeMetrics,
} from "./types";

export async function getLatestSnapshot() {
  return apiFetch<ExecutiveSnapshot>("/api/executive/snapshot/latest");
}

export async function generateSnapshot(period: "week" | "month" = "week") {
  return apiFetch<ExecutiveSnapshot>(`/api/executive/snapshot/generate?period=${period}`);
}

export async function getSnapshotHistory(page = 1) {
  return apiFetch<{ snapshots: ExecutiveSnapshot[]; total: number; page: number }>(
    `/api/executive/snapshot/history?page=${page}`,
  );
}

export async function getRealtimeMetrics() {
  return apiFetch<ExecutiveRealtimeMetrics>("/api/executive/metrics");
}

// --- Executive History ---
import type { ExecutiveWeeklySnapshot } from "./types";

export async function getExecutiveHistory(period: "4w" | "3m" | "6m" = "4w") {
  return apiFetch<ExecutiveWeeklySnapshot[]>(
    `/api/executive/history?period=${period}`,
  );
}

export function getExecutiveHistoryCsvUrl(period: "4w" | "3m" | "6m" = "4w"): string {
  return `${API_BASE}/api/executive/history/csv?period=${period}`;
}

// --- Security Analyzer ---
import type {
  SecurityScan,
  SecurityFinding,
  SecurityStats,
  DASTScan,
  DASTFinding,
} from "./types";

export async function startSecurityScan(repoName: string) {
  return apiFetch<{ scan_id: string; status: string }>("/api/security/scan", {
    method: "POST",
    body: JSON.stringify({ repo_name: repoName }),
  });
}

export async function getSecurityScan(scanId: string) {
  return apiFetch<SecurityScan>(`/api/security/scan/${scanId}`);
}

export async function getSecurityFindings(scanId: string, params?: { severity?: string; scanner?: string }) {
  const qs = new URLSearchParams();
  if (params?.severity) qs.set("severity", params.severity);
  if (params?.scanner) qs.set("scanner", params.scanner);
  return apiFetch<{ findings: SecurityFinding[] }>(`/api/security/scan/${scanId}/findings?${qs.toString()}`);
}


export async function listSecurityScans(params?: { repo_name?: string; page?: number }) {
  const qs = new URLSearchParams();
  if (params?.repo_name) qs.set("repo_name", params.repo_name);
  if (params?.page) qs.set("page", String(params.page));
  return apiFetch<{ scans: SecurityScan[]; total: number; page: number }>(`/api/security/scans?${qs.toString()}`);
}

export async function getSecurityStats() {
  return apiFetch<SecurityStats>("/api/security/stats");
}

// --- DAST Scanner ---

export async function startDASTScan(body: { target_url: string; target_env: "development" | "staging" }) {
  return apiFetch<{ scan_id: string; status: string }>("/api/security/dast/scan", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getDASTScan(scanId: string) {
  return apiFetch<DASTScan>(`/api/security/dast/scan/${scanId}`);
}

export async function getDASTFindings(scanId: string) {
  return apiFetch<{ findings: DASTFinding[] }>(`/api/security/dast/scan/${scanId}/findings`);
}

export async function listDASTScans(page = 1) {
  return apiFetch<{ scans: DASTScan[]; total: number; page: number }>(`/api/security/dast/scans?page=${page}`);
}

// --- Notifications ---

export interface NotificationPreferences {
  email_enabled: boolean;
  alert_email: boolean;
  incident_email: boolean;
  review_email: boolean;
  security_email: boolean;
  executive_email: boolean;
}

export interface SMTPStatus {
  smtp_host: string;
  smtp_port: number;
  smtp_user: string;
  smtp_password: string;
  smtp_from: string;
  configured: boolean;
}

export async function getNotificationPreferences() {
  return apiFetch<NotificationPreferences>("/api/notifications/preferences");
}

export async function updateNotificationPreferences(prefs: NotificationPreferences) {
  return apiFetch<NotificationPreferences>("/api/notifications/preferences", {
    method: "PUT",
    body: JSON.stringify(prefs),
  });
}

export async function getSMTPStatus() {
  return apiFetch<SMTPStatus>("/api/notifications/smtp");
}

export async function testSMTP() {
  return apiFetch<{ status: string; message: string }>("/api/notifications/smtp/test", {
    method: "POST",
  });
}

// --- Onboarding ---

export interface OnboardingStatus {
  onboarding_completed: boolean;
  onboarding_step: number;
  onboarding_completed_at: string | null;
}

export async function getOnboardingStatus() {
  return apiFetch<OnboardingStatus>("/api/organizations/onboarding");
}

export async function updateOnboardingStep(step: number, completed = false) {
  return apiFetch<OnboardingStatus>("/api/organizations/onboarding", {
    method: "PATCH",
    body: JSON.stringify({ step, completed }),
  });
}

export async function updateOrgName(name: string, appUrl?: string) {
  return apiFetch<{ name: string; app_url: string | null }>("/api/organizations/name", {
    method: "PATCH",
    body: JSON.stringify({ name, app_url: appUrl || null }),
  });
}

// --- Health Admin ---

export interface HealthComponentStatus {
  status: "ok" | "degraded" | "down";
  latency_ms?: number;
  detail?: string;
}

export interface HealthLLMProvider {
  name: string;
  status: "ok" | "degraded" | "down";
  is_default: boolean;
  latency_ms: number;
}

export interface HealthAdminResponse {
  database: HealthComponentStatus;
  embeddings: HealthComponentStatus & { provider: string };
  llm_providers: HealthLLMProvider[];
  github_webhook: { status: "ok" | "not_configured" | "error"; last_received_at: string | null; detail: string };
  background_workers: { status: "ok" | "degraded" | "down"; active_jobs: number; failed_jobs_last_hour: number };
  email: { status: "ok" | "not_configured" | "error"; provider: string | null };
  storage: { chunks_total: number; repos_indexed: number; last_indexed_at: string | null };
}

export async function getHealthAdmin() {
  return apiFetch<HealthAdminResponse>("/api/health/admin");
}

// --- Products ---
import type { Product, ProductMember } from "./types";

export async function listProducts() {
  return apiFetch<Product[]>("/api/products");
}

export async function createProduct(data: { name: string; description?: string }) {
  return apiFetch<Product>("/api/products", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateProduct(id: string, data: { name?: string; description?: string }) {
  return apiFetch<Product>(`/api/products/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function archiveProduct(id: string) {
  return apiFetch<{ archived: boolean }>(`/api/products/${id}`, {
    method: "DELETE",
  });
}

export async function listProductMembers(productId: string) {
  return apiFetch<ProductMember[]>(`/api/products/${productId}/members`);
}

export async function addProductMember(productId: string, userId: string) {
  return apiFetch<{ id: string; product_id: string; user_id: string }>(
    `/api/products/${productId}/members`,
    { method: "POST", body: JSON.stringify({ user_id: userId }) },
  );
}

export async function removeProductMember(productId: string, userId: string) {
  return apiFetch<{ removed: boolean }>(
    `/api/products/${productId}/members/${userId}`,
    { method: "DELETE" },
  );
}

// --- Enterprise ---

export interface EnterpriseTestResult {
  success: boolean;
  message: string;
  version: string | null;
}

export interface EnterpriseStatus {
  configured: boolean;
  setup_complete: boolean;
  last_health_status: string | null;
  last_health_check: string | null;
  last_health_error: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface EnterpriseHealthResult {
  status: "ok" | "error";
  response_time_ms: number;
  error: string | null;
  previous_status: string | null;
}

export interface EnterpriseHealthLog {
  status: string;
  response_time_ms: number;
  error: string | null;
  checked_at: string | null;
}

export interface EnterpriseDBConfig {
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;
  ssl_mode?: string;
}

export async function enterpriseTestConnection(config: EnterpriseDBConfig) {
  return apiFetch<EnterpriseTestResult>("/api/enterprise/test-connection", {
    method: "POST",
    body: JSON.stringify(config),
  });
}

export async function enterpriseGetStatus() {
  return apiFetch<EnterpriseStatus>("/api/enterprise/status");
}

export async function enterpriseHealthCheck() {
  return apiFetch<EnterpriseHealthResult>("/api/enterprise/health-check", {
    method: "POST",
  });
}

export async function enterpriseHealthLog(limit = 20) {
  return apiFetch<EnterpriseHealthLog[]>(`/api/enterprise/health-log?limit=${limit}`);
}

export async function enterpriseSetupStream(
  config: EnterpriseDBConfig,
  onEvent: (event: Record<string, unknown>) => void,
  onDone: () => void,
  onError: (err: string) => void,
): Promise<void> {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/api/enterprise/setup`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "ngrok-skip-browser-warning": "true",
      ...authHeaders,
    },
    body: JSON.stringify(config),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    onError(body.detail || `Erro ${res.status}`);
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) {
    onError("Stream nao disponivel");
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data: ")) continue;
      const data = trimmed.slice(6);
      if (data === "[DONE]") {
        onDone();
        return;
      }
      try {
        onEvent(JSON.parse(data));
      } catch {
        // ignore parse errors
      }
    }
  }
  onDone();
}

// --- PDF Export ---

export async function downloadPDF(endpoint: string, filename: string): Promise<void> {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: { "ngrok-skip-browser-warning": "true", ...authHeaders },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Erro ${res.status}`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
