export type Role = "admin" | "dev" | "suporte";

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  avatar_url?: string;
  is_active: boolean;
  created_at: string;
  last_activity?: string;
}

export interface Conversation {
  id: string;
  repo_name: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  model_used?: string;
  tokens_used?: number;
  cost_usd?: number;
  provider_name?: string;
  provider?: string;
  created_at: string;
}

export interface Source {
  file_path: string;
  chunk_name: string;
  chunk_type: "function" | "class" | "module";
  content_preview: string;
  start_line?: number;
}

export interface Repository {
  name: string;
  chunks_count: number;
  last_indexed?: string;
  status: "indexed" | "outdated" | "not_indexed";
  total_questions?: number;
  total_cost?: number;
}

export interface Invite {
  id: string;
  token: string;
  role: Role;
  email?: string;
  created_at: string;
  expires_at: string;
  status: "pending" | "used" | "expired";
  used_by?: string;
}

export interface MetricsSummary {
  total_questions: number;
  total_cost_brl: number;
  avg_cost_per_question_brl: number;
  active_users_7d: number;
}

export interface DailyUsage {
  date: string;
  questions: number;
  cost_brl: number;
}

export interface UserUsage {
  user_id: string;
  name: string;
  role: Role;
  total_questions: number;
  total_cost_brl: number;
  last_activity: string;
}

export interface ModelUsage {
  model: string;
  questions: number;
  cost_usd: number;
  percentage: number;
}

export type LLMProviderType = "openai" | "anthropic" | "google" | "groq" | "ollama";

export interface LLMProvider {
  id: string;
  name: string;
  provider: LLMProviderType;
  model_id: string;
  api_key_masked: string;
  base_url?: string | null;
  is_active: boolean;
  is_default: boolean;
  last_tested_at?: string | null;
  last_test_status: "ok" | "error" | "untested";
  last_test_error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface LLMProviderActive {
  id: string;
  name: string;
  provider: LLMProviderType;
  model_id: string;
  is_default: boolean;
  last_test_status: "ok" | "error" | "untested";
}

// --- Monitor de Erros ---

export interface MonitoredProject {
  id: string;
  name: string;
  description?: string;
  token_preview: string;
  is_active: boolean;
  logs_today: number;
  open_alerts: number;
  last_log_at?: string;
  created_at: string;
}

export interface MonitoredProjectDetail {
  id: string;
  name: string;
  description?: string;
  token_preview: string;
  is_active: boolean;
  created_by: string;
  created_at?: string;
  updated_at?: string;
}

export interface MonitoredProjectCreated {
  id: string;
  name: string;
  description?: string;
  token: string;
  token_preview: string;
}

export type LogLevel = "debug" | "info" | "warning" | "error" | "critical";
export type AlertSeverity = "low" | "medium" | "high" | "critical";
export type AlertStatus = "open" | "acknowledged" | "resolved";

export interface LogEntry {
  id: string;
  project_id: string;
  level: LogLevel;
  message: string;
  source?: string;
  received_at: string;
  occurred_at?: string;
  is_analyzed: boolean;
  stack_trace?: string;
  metadata?: Record<string, unknown>;
}

export interface ErrorAlertSummary {
  id: string;
  project_id: string;
  project_name: string;
  title: string;
  severity: AlertSeverity;
  affected_component?: string;
  status: AlertStatus;
  created_at: string;
}

export interface ErrorAlertDetail extends ErrorAlertSummary {
  explanation: string;
  suggested_actions?: string[];
  log_entry?: LogEntry;
  acknowledged_by?: string;
  acknowledged_at?: string;
  resolved_by?: string;
  resolved_at?: string;
}

export interface AlertWebhook {
  id: string;
  name: string;
  url: string;
  is_active: boolean;
  created_at: string;
}

// --- Memoria Tecnica ---

export type KnowledgeSourceType = "pr" | "commit" | "issue" | "discussion" | "code" | "document" | "adr";
export type DecisionType = "arquitetura" | "dependencia" | "padrao" | "correcao" | "refatoracao";

export interface KnowledgeEntry {
  id: string;
  title: string;
  summary?: string;
  source_type: KnowledgeSourceType;
  source_url?: string;
  source_date?: string;
  decision_type?: DecisionType;
  file_paths?: string[];
  components?: string[];
  created_at: string;
}

export interface KnowledgeEntryDetail extends KnowledgeEntry {
  content: string;
  repo_id?: string;
  source_id?: string;
  created_by?: string;
  extracted_at?: string;
  updated_at?: string;
}

export interface KnowledgeSearchResult {
  id: string;
  title: string;
  summary: string;
  source_type: KnowledgeSourceType;
  source_url?: string;
  source_date?: string;
  decision_type?: string;
  score: number;
}

export interface KnowledgeDocument {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  processed: boolean;
  entry_id?: string;
  uploaded_by_name?: string;
  created_at: string;
}

export interface KnowledgeWiki {
  id: string;
  repo_id?: string;
  component_name: string;
  component_path: string;
  generation_version: number;
  last_generated_at?: string;
  created_at: string;
}

export interface KnowledgeWikiDetail extends KnowledgeWiki {
  content: string;
  updated_at?: string;
}

export interface WikiSuggestion {
  path: string;
  name: string;
  repo_name: string | null;
  source: "code" | "knowledge";
  chunk_count: number;
}

export interface KnowledgeStats {
  total_entries: number;
  prs_commits: number;
  documents: number;
  adrs: number;
  issues: number;
  wikis: number;
}

// --- Documentacao Automatica ---

export interface RepoDocStatus {
  readme?: {
    generated_at: string | null;
    pushed_to_github: boolean;
    pushed_at: string | null;
    content_hash: string | null;
  };
  onboarding_guide?: {
    generated_at: string | null;
    pushed_to_github: boolean;
    pushed_at: string | null;
    content_hash: string | null;
  };
}

export interface RepoDoc {
  id: string;
  content: string;
  generated_at: string | null;
  pushed_to_github?: boolean;
  pushed_at?: string | null;
  content_hash: string | null;
  generation_trigger: string;
}

export interface OnboardingProgress {
  started: boolean;
  steps_total: number;
  steps_completed: number;
  completed_steps: string[];
  started_at?: string | null;
  completed_at?: string | null;
}

export interface OnboardingStepResult {
  steps_total: number;
  steps_completed: number;
  completed_steps: string[];
  is_complete: boolean;
}

// --- Revisao de Codigo ---

export type ReviewSourceType = "pr" | "manual";
export type ReviewStatus = "pending" | "analyzing" | "completed" | "failed";
export type ReviewVerdict = "approved" | "approved_with_warnings" | "needs_changes" | "rejected";
export type FindingCategory = "bug" | "security" | "performance" | "consistency" | "pattern";
export type FindingSeverity = "critical" | "high" | "medium" | "low" | "info";

export interface CodeReviewSummary {
  id: string;
  source_type: ReviewSourceType;
  pr_number?: number;
  pr_title?: string;
  pr_url?: string;
  pr_author?: string;
  status: ReviewStatus;
  overall_score?: number;
  overall_verdict?: ReviewVerdict;
  summary?: string;
  repo_id?: string;
  language?: string;
  github_comment_posted: boolean;
  created_at: string;
  updated_at?: string;
}

export interface ReviewFinding {
  id: string;
  category: FindingCategory;
  severity: FindingSeverity;
  title: string;
  description: string;
  suggestion?: string;
  file_path?: string;
  line_start?: number;
  line_end?: number;
  code_snippet?: string;
}

export interface CodeReviewDetail extends CodeReviewSummary {
  submitted_by?: string;
  code_snippet?: string;
  diff?: string;
  files_changed?: string[];
  findings: ReviewFinding[];
}

export interface ReviewStats {
  total_reviews: number;
  avg_score?: number;
  this_month: number;
  approval_rate?: number;
  critical_findings: number;
  weekly_trend: Array<{
    week: string;
    avg_score?: number;
    count: number;
  }>;
  findings_by_category: Record<string, number>;
}

// --- Regras de Negocio ---

export type RuleType = "calculation" | "validation" | "permission" | "integration" | "conditional";

export interface BusinessRuleSummary {
  id: string;
  repo_name: string;
  rule_type: RuleType;
  title: string;
  plain_english: string;
  confidence: number;
  changed_in_last_push: boolean;
  affected_files: string[] | null;
  extracted_at: string | null;
}

export interface BusinessRuleDetail extends BusinessRuleSummary {
  description: string;
  conditions: Array<{ if?: string; then?: string; except?: string; and?: string }> | null;
  affected_functions: string[] | null;
  is_active: boolean;
  last_verified_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  changes: Array<{
    change_type: string;
    previous_description: string | null;
    new_description: string | null;
    detected_at: string | null;
  }>;
  simulations: Array<{
    id: string;
    input_values: Record<string, unknown>;
    result: string;
    created_at: string | null;
  }>;
}

export interface RulesListResponse {
  rules: BusinessRuleSummary[];
  total: number;
  page: number;
  per_page: number;
}

export interface RuleChangeAlert {
  id: string;
  rule_id: string;
  rule_title: string;
  repo_name: string;
  change_type: string;
  previous_description: string | null;
  new_description: string | null;
  detected_at: string | null;
  acknowledged: boolean;
}

export interface RuleSimulationResult {
  simulation_id: string;
  rule_id: string;
  rule_title: string;
  input_values: Record<string, unknown>;
  result: string;
}

export interface RuleExtractStatus {
  total_rules: number;
  last_extracted: string | null;
  changed_since_push: number;
}

// --- Code Generation ---

export interface CodeGenRequest {
  description: string;
  type: string;
  repo_name: string;
  file_path?: string;
  use_context?: boolean;
}

export interface CodeGenHistoryItem {
  id: string;
  repo_name: string;
  title: string;
  request_type: string;
  created_at: string | null;
}

export interface CodeGenHistoryResponse {
  generations: CodeGenHistoryItem[];
  total: number;
  page: number;
}

export interface CodeGenDetail {
  id: string;
  repo_name: string;
  request_description: string;
  request_type: string;
  file_path: string | null;
  use_context: boolean;
  context_used: Record<string, unknown> | null;
  generated_code: string | null;
  explanation: string | null;
  model_used: string | null;
  tokens_used: number | null;
  cost_usd: number | null;
  created_at: string | null;
}

// --- MCP Token ---

export interface McpTokenStatus {
  has_token: boolean;
  token_id?: string;
  created_at?: string;
}

export interface McpTokenGenerated {
  token: string;
  id: string;
}

export interface McpHealth {
  status: string;
  tools: number;
  version: string;
}

// --- Incidents ---

export type IncidentSeverity = "low" | "medium" | "high" | "critical";
export type IncidentStatus = "open" | "investigating" | "mitigated" | "resolved";

export interface Incident {
  id: string;
  org_id: string;
  alert_id: string | null;
  project_id: string;
  project_name: string;
  title: string;
  description: string | null;
  severity: IncidentSeverity;
  status: IncidentStatus;
  declared_by: string;
  declared_by_name: string;
  declared_at: string;
  mitigated_at: string | null;
  resolved_at: string | null;
  resolution_summary: string | null;
  postmortem: string | null;
  postmortem_generated_at: string | null;
  share_token: string | null;
  similar_incidents: unknown;
  timeline?: IncidentTimelineEvent[];
  hypotheses?: IncidentHypothesis[];
}

export interface IncidentTimelineEvent {
  id: string;
  incident_id: string;
  event_type: string;
  content: string;
  created_by: string | null;
  author_name: string | null;
  is_ai_generated: boolean;
  metadata: unknown;
  created_at: string;
}

export interface IncidentHypothesis {
  id: string;
  incident_id: string;
  hypothesis: string;
  reasoning: string;
  confidence: number;
  status: "open" | "confirmed" | "discarded";
  confirmed_by: string | null;
  confirmed_by_name: string | null;
  created_at: string;
}

export interface IncidentListResponse {
  incidents: Incident[];
  total: number;
  page: number;
}

export interface IncidentStats {
  active: number;
  resolved_month: number;
  total: number;
  avg_resolution_hours: number | null;
  avg_resolution_hours_7d: number | null;
  mttr_trend: number | null;
  most_affected_project: string | null;
  most_affected_count: number;
}

export interface SimilarIncident {
  similar_incident_id: string;
  similarity_score: number;
  title: string;
  severity: string;
  resolved_at: string | null;
  resolution_summary: string | null;
  project_name: string;
}

export interface PublicPostmortem {
  title: string;
  severity: string;
  project_name: string;
  declared_at: string | null;
  resolved_at: string | null;
  postmortem: string;
  postmortem_generated_at: string | null;
}

// --- Impact Analysis ---

export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface ImpactAnalysis {
  id: string;
  org_id: string;
  repo_name: string;
  requested_by: string;
  change_description: string;
  affected_files: string[] | null;
  risk_level: RiskLevel | null;
  risk_summary: string | null;
  status: "pending" | "analyzing" | "completed" | "failed";
  findings?: ImpactFinding[];
  created_at: string;
  updated_at: string;
}

export interface ImpactFinding {
  id: string;
  analysis_id: string;
  finding_type: "dependency" | "business_rule" | "pattern_break" | "similar_change";
  severity: RiskLevel;
  title: string;
  description: string;
  affected_component: string | null;
  file_path: string | null;
  recommendation: string;
  created_at: string;
}

export interface ImpactHistoryResponse {
  analyses: ImpactAnalysis[];
  total: number;
  page: number;
}

// --- Executive Dashboard ---

export interface ExecutiveHighlight {
  type: "positive" | "negative" | "neutral";
  text: string;
}

export interface ExecutiveRisk {
  severity: "low" | "medium" | "high";
  description: string;
  recommendation: string;
}

export interface ExecutiveRecommendation {
  priority: number;
  action: string;
  reason: string;
}

export interface ExecutiveSnapshot {
  id: string;
  org_id: string;
  generated_at: string;
  period_start: string;
  period_end: string;
  health_score: number;
  summary: string | null;
  highlights: ExecutiveHighlight[];
  risks: ExecutiveRisk[];
  recommendations: ExecutiveRecommendation[];
  metrics: Record<string, unknown>;
}

export interface ExecutiveRealtimeMetrics {
  systems_monitored: number;
  alerts_open: number;
  incidents_open: number;
  repos_indexed: number;
}

// --- Security Analyzer ---

export interface SecurityScan {
  id: string;
  org_id: string;
  repo_name: string;
  requested_by: string;
  status: "pending" | "analyzing" | "completed" | "failed";
  security_score?: number;
  total_findings: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  scanners_run: string[];
  duration_seconds?: number;
  created_at: string;
  updated_at?: string;
}

export interface SecurityFinding {
  id: string;
  scan_id: string;
  scanner: "secrets" | "vulnerabilities" | "dependencies" | "config" | "patterns";
  severity: "critical" | "high" | "medium" | "low" | "info";
  category: string;
  title: string;
  description: string;
  file_path?: string;
  line_start?: number;
  line_end?: number;
  code_snippet?: string;
  recommendation?: string;
  cwe_id?: string;
  created_at: string;
}

export interface DependencyAlert {
  id: string;
  scan_id: string;
  package_name: string;
  current_version?: string;
  ecosystem?: string;
  vulnerability_id?: string;
  severity: string;
  summary?: string;
  fixed_version?: string;
  created_at: string;
}

export interface SecurityStats {
  recent_scans: SecurityScan[];
  avg_score?: number;
  total_critical_findings: number;
}

// --- DAST Scanner ---

export type DASTProbeType =
  | "sql_injection" | "auth_bypass" | "rate_limit" | "cors"
  | "security_headers" | "idor" | "xss" | "brute_force"
  | "sensitive_exposure" | "http_methods";

export interface DASTScan {
  id: string;
  org_id: string;
  requested_by: string;
  target_url: string;
  target_env: "development" | "staging";
  status: "pending" | "running" | "completed" | "failed";
  probes_total: number;
  probes_completed: number;
  vulnerabilities_confirmed: number;
  risk_level?: "low" | "medium" | "high" | "critical";
  summary?: string;
  duration_seconds?: number;
  created_at: string;
  updated_at?: string;
}

export interface DASTFinding {
  id: string;
  scan_id: string;
  probe_type: DASTProbeType;
  severity: "critical" | "high" | "medium" | "low" | "info";
  title: string;
  description: string;
  result: string;
  confirmed: boolean;
  endpoint: string;
  payload_used?: string;
  response_code?: number;
  recommendation: string;
  created_at: string;
}
