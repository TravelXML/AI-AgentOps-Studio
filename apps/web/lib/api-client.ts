import type { FlowSpec } from "./flowspec";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  code: string;
  status: number;
  details: unknown[];

  constructor(status: number, code: string, message: string, details: unknown[] = []) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const err = body?.error;
    throw new ApiError(response.status, err?.code ?? "UNKNOWN", err?.message ?? response.statusText, err?.details ?? []);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  created_at: string;
}

export interface Flow {
  id: string;
  project_id: string;
  name: string;
  description: string;
  status: "draft" | "published" | "archived";
  latest_version: number | null;
  created_at: string;
  updated_at: string;
}

export interface FlowVersion {
  id: string;
  flow_id: string;
  version: number;
  spec: FlowSpec;
  created_at: string;
}

export interface ValidationIssue {
  code: string;
  message: string;
  node_id: string | null;
  edge_id: string | null;
  severity: "error" | "warning";
}

export interface ValidateFlowResponse {
  valid: boolean;
  issues: ValidationIssue[];
}

export interface RunStep {
  id: string;
  node_id: string;
  node_type: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  latency_ms: number | null;
  model: string | null;
  provider: string | null;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
  tool_id: string | null;
  tool_arguments: Record<string, unknown> | null;
  tool_result: unknown;
  routing_decision: Record<string, unknown> | null;
  output_data: unknown;
  error: string | null;
}

export interface Run {
  id: string;
  flow_id: string;
  flow_version_id: string;
  status: string;
  inputs: Record<string, unknown>;
  output: unknown;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  steps: RunStep[];
}

export interface RunEventPayload {
  id?: string;
  type: string;
  run_id: string;
  node_id: string | null;
  step_id?: string | null;
  data: Record<string, unknown>;
  timestamp: string;
  created_at?: string;
}

export interface ToolInfo {
  id: string;
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  permissions: string[];
}

export interface CatalogModel {
  id: string;
  name: string;
  vendor: string;
  context_length: number | null;
  is_free: boolean;
  pricing_prompt: string | null;
  pricing_completion: string | null;
}

export interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  created_at: string;
}

export interface KbDocument {
  id: string;
  knowledge_base_id: string;
  name: string;
  status: "processing" | "ready" | "failed";
  chunk_count: number;
  error: string | null;
  created_at: string;
}

export interface McpTool {
  name: string;
  description?: string;
  inputSchema?: Record<string, unknown>;
}

export interface McpServerInfo {
  id: string;
  name: string;
  url: string;
  status: "unknown" | "connected" | "error";
  last_error: string | null;
  tools: McpTool[];
  has_secret: boolean;
  created_at: string;
}

export interface Dataset {
  id: string;
  name: string;
  description: string;
  test_case_count: number;
  created_at: string;
}

export interface TestCase {
  id: string;
  inputs: Record<string, unknown>;
  expected_output: unknown;
}

export type EvaluatorType = "exact_match" | "contains" | "regex" | "schema" | "latency" | "cost" | "llm_judge";

export interface EvaluatorConfig {
  type: EvaluatorType;
  config: Record<string, unknown>;
}

export interface EvaluationResult {
  id: string;
  test_case_id: string;
  run_id: string | null;
  passed: boolean;
  evaluator_results: { evaluator: string; passed: boolean; detail: string }[];
  actual_output: unknown;
  error: string | null;
}

export interface EvaluationRun {
  id: string;
  flow_id: string;
  dataset_id: string;
  evaluators: EvaluatorConfig[];
  status: "running" | "completed" | "failed";
  total_cases: number;
  passed_cases: number;
  created_at: string;
  results: EvaluationResult[];
}

export interface AuditLogEntry {
  id: string;
  actor: string;
  action: string;
  resource_type: string;
  resource_id: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ModelConfigInfo {
  id: string;
  model_key: string;
  provider: string;
  model: string;
  base_url: string | null;
  has_secret: boolean;
  temperature_default: number;
  timeout_seconds: number;
  max_retries: number;
  created_at: string;
}

export const api = {
  listProjects: () => request<Project[]>("/api/v1/projects"),
  listFlows: () => request<Flow[]>("/api/v1/flows"),
  getFlow: (id: string) => request<Flow>(`/api/v1/flows/${id}`),
  createFlow: (payload: { name: string; description?: string; project_id?: string; spec?: FlowSpec }) =>
    request<Flow>("/api/v1/flows", { method: "POST", body: JSON.stringify(payload) }),
  getLatestVersion: (flowId: string) => request<FlowVersion>(`/api/v1/flows/${flowId}/versions/latest`),
  saveVersion: (flowId: string, spec: FlowSpec) =>
    request<FlowVersion>(`/api/v1/flows/${flowId}/versions`, {
      method: "POST",
      body: JSON.stringify({ spec }),
    }),
  validateFlow: (flowId: string, spec: FlowSpec) =>
    request<ValidateFlowResponse>(`/api/v1/flows/${flowId}/validate`, {
      method: "POST",
      body: JSON.stringify({ spec }),
    }),
  publishFlow: (flowId: string) => request<Flow>(`/api/v1/flows/${flowId}/publish`, { method: "POST" }),
  listRuns: (params?: { flow_id?: string; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.flow_id) qs.set("flow_id", params.flow_id);
    if (params?.limit) qs.set("limit", String(params.limit));
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<Run[]>(`/api/v1/runs${suffix}`);
  },
  getRun: (runId: string) => request<Run>(`/api/v1/runs/${runId}`),
  getRunEvents: (runId: string) => request<RunEventPayload[]>(`/api/v1/runs/${runId}/events`),
  listTools: () => request<ToolInfo[]>("/api/v1/tools"),
  listModels: () => request<ModelConfigInfo[]>("/api/v1/models"),
  createModel: (payload: {
    model_key: string;
    provider: string;
    model: string;
    base_url?: string | null;
    api_key?: string | null;
  }) => request<ModelConfigInfo>("/api/v1/models", { method: "POST", body: JSON.stringify(payload) }),
  generateFlow: (payload: { description: string; model: string }) =>
    request<{ spec: FlowSpec; attempts: number }>("/api/v1/architect/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listKnowledgeBases: () => request<KnowledgeBase[]>("/api/v1/knowledge-bases"),
  createKnowledgeBase: (payload: { name: string; description?: string }) =>
    request<KnowledgeBase>("/api/v1/knowledge-bases", { method: "POST", body: JSON.stringify(payload) }),
  listDocuments: (kbId: string) => request<KbDocument[]>(`/api/v1/knowledge-bases/${kbId}/documents`),
  ingestDocument: async (
    kbId: string,
    payload: { name: string; text?: string; file?: File; embedding_model?: string }
  ) => {
    const form = new FormData();
    form.set("name", payload.name);
    if (payload.file) form.set("file", payload.file);
    if (payload.text) form.set("text", payload.text);
    if (payload.embedding_model) form.set("embedding_model", payload.embedding_model);
    const response = await fetch(`${API_URL}/api/v1/knowledge-bases/${kbId}/documents`, {
      method: "POST",
      body: form,
    });
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new ApiError(
        response.status,
        body?.error?.code ?? "UPLOAD_FAILED",
        body?.error?.message ?? response.statusText
      );
    }
    return (await response.json()) as KbDocument;
  },
  listMcpServers: () => request<McpServerInfo[]>("/api/v1/mcp-servers"),
  registerMcpServer: (payload: { name: string; url: string; api_key?: string | null }) =>
    request<McpServerInfo>("/api/v1/mcp-servers", { method: "POST", body: JSON.stringify(payload) }),
  refreshMcpServer: (serverId: string) =>
    request<McpServerInfo>(`/api/v1/mcp-servers/${serverId}/refresh`, { method: "POST" }),
  listDatasets: () => request<Dataset[]>("/api/v1/evaluations/datasets"),
  createDataset: (payload: { name: string; description?: string }) =>
    request<Dataset>("/api/v1/evaluations/datasets", { method: "POST", body: JSON.stringify(payload) }),
  listTestCases: (datasetId: string) => request<TestCase[]>(`/api/v1/evaluations/datasets/${datasetId}/cases`),
  addTestCases: (datasetId: string, cases: { inputs: Record<string, unknown>; expected_output?: unknown }[]) =>
    request<TestCase[]>(`/api/v1/evaluations/datasets/${datasetId}/cases`, {
      method: "POST",
      body: JSON.stringify({ cases }),
    }),
  listEvaluationRuns: () => request<EvaluationRun[]>("/api/v1/evaluations/runs"),
  getEvaluationRun: (id: string) => request<EvaluationRun>(`/api/v1/evaluations/runs/${id}`),
  runEvaluation: (payload: {
    flow_id: string;
    dataset_id: string;
    evaluators: EvaluatorConfig[];
    judge_model?: string;
  }) => request<EvaluationRun>("/api/v1/evaluations/runs", { method: "POST", body: JSON.stringify(payload) }),
  getPolicy: () => request<{ denied_tools: string[] }>("/api/v1/settings/policy"),
  updatePolicy: (denied_tools: string[]) =>
    request<{ denied_tools: string[] }>("/api/v1/settings/policy", {
      method: "PUT",
      body: JSON.stringify({ denied_tools }),
    }),
  listAuditLog: () => request<AuditLogEntry[]>("/api/v1/settings/audit-log"),
  searchModelCatalog: (params: { q?: string; provider?: string; free_only?: boolean; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q);
    if (params.provider) qs.set("provider", params.provider);
    if (params.free_only) qs.set("free_only", "true");
    if (params.limit) qs.set("limit", String(params.limit));
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<CatalogModel[]>(`/api/v1/models/catalog${suffix}`);
  },
  /** Same endpoint as searchModelCatalog, but reads the `X-Total-Count` header so callers can
   * page through the full catalog instead of just the first page. */
  browseModelCatalog: async (params: {
    q?: string;
    provider?: string;
    free_only?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<{ items: CatalogModel[]; total: number }> => {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q);
    if (params.provider) qs.set("provider", params.provider);
    if (params.free_only) qs.set("free_only", "true");
    if (params.limit) qs.set("limit", String(params.limit));
    if (params.offset) qs.set("offset", String(params.offset));
    const response = await fetch(`${API_URL}/api/v1/models/catalog?${qs.toString()}`);
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      const err = body?.error;
      throw new ApiError(response.status, err?.code ?? "UNKNOWN", err?.message ?? response.statusText);
    }
    const items = (await response.json()) as CatalogModel[];
    const total = Number(response.headers.get("X-Total-Count") ?? items.length);
    return { items, total };
  },
};

async function* parseSse(response: Response): AsyncGenerator<RunEventPayload> {
  if (!response.body) return;
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.split("\n").find((l) => l.startsWith("data: "));
      if (line) {
        yield JSON.parse(line.slice("data: ".length)) as RunEventPayload;
      }
    }
  }
}

export async function* runFlow(
  flowId: string,
  inputs: Record<string, unknown>
): AsyncGenerator<RunEventPayload, string | null> {
  const response = await fetch(`${API_URL}/api/v1/flows/${flowId}/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ inputs }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, body?.error?.code ?? "RUN_FAILED", body?.error?.message ?? response.statusText);
  }
  const runId = response.headers.get("x-run-id");
  yield* parseSse(response);
  return runId;
}

export async function* resumeRun(
  runId: string,
  approved: boolean,
  note?: string
): AsyncGenerator<RunEventPayload> {
  const response = await fetch(`${API_URL}/api/v1/runs/${runId}/resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approved, note }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, body?.error?.code ?? "RESUME_FAILED", body?.error?.message ?? response.statusText);
  }
  yield* parseSse(response);
}

export async function* replayRun(runId: string): AsyncGenerator<RunEventPayload, string | null> {
  const response = await fetch(`${API_URL}/api/v1/runs/${runId}/replay`, { method: "POST" });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, body?.error?.code ?? "REPLAY_FAILED", body?.error?.message ?? response.statusText);
  }
  const newRunId = response.headers.get("x-run-id");
  yield* parseSse(response);
  return newRunId;
}
