/**
 * TypeScript mirror of packages/flowspec (Pydantic). Hand-maintained for MVP - see
 * docs/architecture/flowspec.md for the plan to generate this from the backend's OpenAPI schema
 * instead, per spec section 82 (typed contracts, no manual drift).
 */
import { z } from "zod";

export const NodeType = z.enum([
  "input",
  "output",
  "agent",
  "llm",
  "router",
  "supervisor",
  "tool",
  "mcp",
  "rag",
  "memory",
  "human_approval",
  "guardrail",
]);
export type NodeType = z.infer<typeof NodeType>;

export const Position = z.object({ x: z.number(), y: z.number() });
export type Position = z.infer<typeof Position>;

export const InputField = z.object({
  name: z.string(),
  type: z.enum(["string", "number", "boolean", "json"]).default("string"),
  required: z.boolean().default(true),
  description: z.string().default(""),
});
export type InputField = z.infer<typeof InputField>;

export const RetryConfig = z.object({
  max_attempts: z.number().int().min(1).max(10).default(1),
  backoff_seconds: z.number().min(0).default(1),
});

export const InputNodeConfig = z.object({
  mode: z.enum(["text", "json", "structured"]).default("text"),
  fields: z.array(InputField).default([]),
});

export const OutputNodeConfig = z.object({
  format: z.enum(["text", "json"]).default("text"),
  source_node: z.string().nullable().default(null),
});

export const AgentNodeConfig = z.object({
  name: z.string(),
  description: z.string().default(""),
  instructions: z.string().default("You are a helpful assistant."),
  model: z.string().default("default"),
  temperature: z.number().min(0).max(2).default(0.2),
  max_tokens: z.number().int().min(1).max(200000).default(1024),
  tools: z.array(z.string()).default([]),
  memory: z.string().nullable().default(null),
  structured_output: z.record(z.any()).nullable().default(null),
  retries: RetryConfig.default({ max_attempts: 1, backoff_seconds: 1 }),
  timeout_seconds: z.number().gt(0).default(60),
});

export const LLMNodeConfig = z.object({
  model: z.string().default("default"),
  prompt_template: z.string().default("{input}"),
  temperature: z.number().min(0).max(2).default(0.2),
  max_tokens: z.number().int().min(1).max(200000).default(1024),
});

export const RouterRule = z.object({ when: z.string(), target: z.string() });
export type RouterRule = z.infer<typeof RouterRule>;

export const RouterNodeConfig = z.object({
  mode: z.enum(["expression", "rule", "llm"]).default("rule"),
  rules: z.array(RouterRule).default([]),
  default_target: z.string().nullable().default(null),
  llm_instructions: z.string().nullable().default(null),
  model: z.string().default("default"),
});

export const SupervisorNodeConfig = z.object({
  agents: z.array(z.string()).default([]),
  routing_instructions: z.string().default("Delegate to the most appropriate agent."),
  max_delegation_depth: z.number().int().min(1).max(20).default(3),
  max_iterations: z.number().int().min(1).max(50).default(6),
  fallback_agent: z.string().nullable().default(null),
  model: z.string().default("default"),
});

export const ToolNodeConfig = z.object({
  tool_id: z.string(),
  arguments: z.record(z.any()).default({}),
});

export const MCPNodeConfig = z.object({
  server_id: z.string(),
  tool_name: z.string(),
  arguments: z.record(z.any()).default({}),
});

export const RAGNodeConfig = z.object({
  knowledge_base_id: z.string(),
  top_k: z.number().int().min(1).max(50).default(4),
  embedding_model: z.string().nullable().default(null),
  min_score: z.number().min(0).max(1).default(0),
});

export const MemoryNodeConfig = z.object({
  memory_type: z.enum(["conversation", "semantic"]).default("conversation"),
  scope: z.enum(["run", "agent", "workspace"]).default("agent"),
  ttl_seconds: z.number().nullable().default(null),
});

export const HumanApprovalNodeConfig = z.object({
  condition: z.string().nullable().default(null),
  approvers: z.array(z.string()).default([]),
  timeout_seconds: z.number().nullable().default(null),
  message_template: z.string().default("Approval required to continue."),
});

export const GuardrailCheck = z.object({
  type: z.enum([
    "pii_detection",
    "blocked_keywords",
    "prompt_injection_heuristic",
    "max_input_size",
    "output_validation",
    "json_schema",
  ]),
  config: z.record(z.any()).default({}),
});

export const GuardrailNodeConfig = z.object({
  stage: z.enum(["pre", "post"]).default("pre"),
  checks: z.array(GuardrailCheck).default([]),
  on_fail: z.enum(["block", "warn"]).default("block"),
});

const nodeConfigByType = {
  input: InputNodeConfig,
  output: OutputNodeConfig,
  agent: AgentNodeConfig,
  llm: LLMNodeConfig,
  router: RouterNodeConfig,
  supervisor: SupervisorNodeConfig,
  tool: ToolNodeConfig,
  mcp: MCPNodeConfig,
  rag: RAGNodeConfig,
  memory: MemoryNodeConfig,
  human_approval: HumanApprovalNodeConfig,
  guardrail: GuardrailNodeConfig,
} as const;

export const FlowNode = z.object({
  id: z.string(),
  type: NodeType,
  position: Position.default({ x: 0, y: 0 }),
  label: z.string().default(""),
  config: z.record(z.any()).default({}),
});
export type FlowNode = z.infer<typeof FlowNode>;

export const FlowEdge = z.object({
  id: z.string(),
  source: z.string(),
  target: z.string(),
  condition: z.string().nullable().default(null),
});
export type FlowEdge = z.infer<typeof FlowEdge>;

export const FlowSpec = z.object({
  schema_version: z.number().default(1),
  id: z.string(),
  name: z.string(),
  version: z.number().default(1),
  description: z.string().default(""),
  inputs: z.array(InputField).default([]),
  nodes: z.array(FlowNode).default([]),
  edges: z.array(FlowEdge).default([]),
  variables: z.record(z.any()).default({}),
  policies: z.record(z.any()).default({}),
  metadata: z.record(z.any()).default({}),
});
export type FlowSpec = z.infer<typeof FlowSpec>;

export function defaultConfigFor(type: NodeType): Record<string, unknown> {
  const schema = nodeConfigByType[type];
  const parsed = schema.safeParse(type === "agent" ? { name: "Agent" } : type === "tool" ? { tool_id: "" } : type === "mcp" ? { server_id: "", tool_name: "" } : type === "rag" ? { knowledge_base_id: "" } : {});
  return parsed.success ? parsed.data : {};
}

export const NODE_CATEGORY: Record<NodeType, string> = {
  input: "CORE",
  output: "CORE",
  agent: "AI",
  llm: "AI",
  router: "CONTROL",
  supervisor: "AGENTS",
  tool: "TOOLS",
  mcp: "TOOLS",
  rag: "KNOWLEDGE",
  memory: "KNOWLEDGE",
  human_approval: "CONTROL",
  guardrail: "SECURITY",
};

export const NODE_LABEL: Record<NodeType, string> = {
  input: "Input",
  output: "Output",
  agent: "Agent",
  llm: "LLM",
  router: "Router",
  supervisor: "Supervisor",
  tool: "Tool",
  mcp: "MCP",
  rag: "RAG",
  memory: "Memory",
  human_approval: "Human Approval",
  guardrail: "Guardrail",
};
