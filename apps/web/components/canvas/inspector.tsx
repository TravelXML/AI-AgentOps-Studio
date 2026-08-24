"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FieldGroup, Label, Select, TextArea, TextInput } from "@/components/ui/field";
import { type AgentQNode, useCanvasStore } from "@/lib/canvas-store";
import {
  api,
  type KnowledgeBase,
  type McpServerInfo,
  type ModelConfigInfo,
  type ToolInfo,
} from "@/lib/api-client";

// Sentinel value for the "+ Add new…" entry appended to registry dropdowns (models, MCP
// servers, knowledge bases) - selecting it opens the relevant settings page in a new tab (so the
// canvas and current node selection aren't lost) instead of actually changing the field's value.
const ADD_NEW_VALUE = "__add_new__";

function handleRegistrySelect(rawValue: string, addNewHref: string, onSelect: (value: string) => void) {
  if (rawValue === ADD_NEW_VALUE) {
    window.open(addNewHref, "_blank", "noopener");
    return;
  }
  onSelect(rawValue);
}

// Same query keys the Models / MCP Servers / Knowledge pages use, so adding a connector there
// (which calls queryClient.invalidateQueries on these exact keys) is reflected here too - an
// open canvas tab doesn't go on showing an empty dropdown forever after you configure something
// elsewhere. react-query's default refetch-on-window-focus also covers the case where the first
// fetch failed transiently (e.g. hit while a fix was still deploying) and nothing else refetches it.
function useModelsAndTools() {
  const models = useQuery({ queryKey: ["models"], queryFn: api.listModels }).data ?? [];
  const tools = useQuery({ queryKey: ["tools"], queryFn: api.listTools }).data ?? [];
  return { models, tools };
}

function useKnowledgeBases() {
  return useQuery({ queryKey: ["knowledge-bases"], queryFn: api.listKnowledgeBases }).data ?? [];
}

function useMcpServers() {
  return useQuery({ queryKey: ["mcp-servers"], queryFn: api.listMcpServers }).data ?? [];
}

export function Inspector() {
  const node = useCanvasStore((s) => s.nodes.find((n) => n.id === s.selectedNodeId));
  const updateNodeConfig = useCanvasStore((s) => s.updateNodeConfig);
  const updateNodeLabel = useCanvasStore((s) => s.updateNodeLabel);
  const removeSelected = useCanvasStore((s) => s.removeSelected);
  const { models, tools } = useModelsAndTools();
  const knowledgeBases = useKnowledgeBases();
  const mcpServers = useMcpServers();

  if (!node) {
    return (
      <div className="flex h-full items-center justify-center px-6 text-center text-sm text-ink-faint">
        Select a node to configure it.
      </div>
    );
  }

  const setConfig = (patch: Record<string, unknown>) =>
    updateNodeConfig(node.id, { ...node.data.config, ...patch });

  return (
    <div className="scrollbar-thin h-full overflow-y-auto">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div>
          <div className="text-[11px] uppercase tracking-wide text-ink-faint">{node.data.nodeType}</div>
          <div className="text-sm font-medium text-ink">Inspector</div>
        </div>
        <Button variant="ghost" size="sm" onClick={removeSelected}>
          Delete
        </Button>
      </div>

      <div className="space-y-4 p-4">
        <FieldGroup>
          <div>
            <Label>Node ID</Label>
            <code className="block truncate text-xs text-ink-faint">{node.id}</code>
          </div>
          <div>
            <Label>Label</Label>
            <TextInput value={node.data.label} onChange={(e) => updateNodeLabel(node.id, e.target.value)} />
          </div>
        </FieldGroup>

        {node.data.nodeType === "input" && <InputConfig node={node} setConfig={setConfig} />}
        {node.data.nodeType === "output" && <OutputConfig node={node} setConfig={setConfig} />}
        {node.data.nodeType === "agent" && <AgentConfig node={node} setConfig={setConfig} models={models} tools={tools} />}
        {node.data.nodeType === "llm" && <LLMConfig node={node} setConfig={setConfig} models={models} />}
        {node.data.nodeType === "router" && <RouterConfig node={node} setConfig={setConfig} models={models} />}
        {node.data.nodeType === "supervisor" && <SupervisorConfig node={node} setConfig={setConfig} models={models} />}
        {node.data.nodeType === "tool" && <ToolConfig node={node} setConfig={setConfig} tools={tools} />}
        {node.data.nodeType === "human_approval" && <ApprovalConfig node={node} setConfig={setConfig} />}
        {node.data.nodeType === "rag" && (
          <RAGConfig node={node} setConfig={setConfig} knowledgeBases={knowledgeBases} />
        )}
        {node.data.nodeType === "memory" && <MemoryConfig node={node} setConfig={setConfig} />}
        {node.data.nodeType === "mcp" && (
          <McpConfig node={node} setConfig={setConfig} servers={mcpServers} />
        )}
        {node.data.nodeType === "guardrail" && <GuardrailConfig node={node} setConfig={setConfig} />}
      </div>
    </div>
  );
}

function InputConfig({ node, setConfig }: { node: AgentQNode; setConfig: (p: Record<string, unknown>) => void }) {
  const mode = (node.data.config.mode as string) ?? "text";
  return (
    <FieldGroup>
      <div>
        <Label>Input mode</Label>
        <Select value={mode} onChange={(e) => setConfig({ mode: e.target.value })}>
          <option value="text">Text</option>
          <option value="json">JSON</option>
          <option value="structured">Structured fields</option>
        </Select>
      </div>
    </FieldGroup>
  );
}

function OutputConfig({ node, setConfig }: { node: AgentQNode; setConfig: (p: Record<string, unknown>) => void }) {
  const format = (node.data.config.format as string) ?? "text";
  return (
    <FieldGroup>
      <div>
        <Label>Output format</Label>
        <Select value={format} onChange={(e) => setConfig({ format: e.target.value })}>
          <option value="text">Text</option>
          <option value="json">JSON</option>
        </Select>
      </div>
    </FieldGroup>
  );
}

function AgentConfig({
  node,
  setConfig,
  models,
  tools,
}: {
  node: AgentQNode;
  setConfig: (p: Record<string, unknown>) => void;
  models: ModelConfigInfo[];
  tools: ToolInfo[];
}) {
  const cfg = node.data.config;
  return (
    <FieldGroup>
      <div>
        <Label>Name</Label>
        <TextInput value={(cfg.name as string) ?? ""} onChange={(e) => setConfig({ name: e.target.value })} />
      </div>
      <div>
        <Label>Description</Label>
        <TextInput
          value={(cfg.description as string) ?? ""}
          onChange={(e) => setConfig({ description: e.target.value })}
        />
      </div>
      <div>
        <Label>System instructions</Label>
        <TextArea
          value={(cfg.instructions as string) ?? ""}
          onChange={(e) => setConfig({ instructions: e.target.value })}
        />
      </div>
      <ModelPicker value={(cfg.model as string) ?? "default"} onChange={(v) => setConfig({ model: v })} models={models} />
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label>Temperature</Label>
          <TextInput
            type="number"
            step="0.1"
            min={0}
            max={2}
            value={(cfg.temperature as number) ?? 0.2}
            onChange={(e) => setConfig({ temperature: Number(e.target.value) })}
          />
        </div>
        <div>
          <Label>Max tokens</Label>
          <TextInput
            type="number"
            min={1}
            value={(cfg.max_tokens as number) ?? 1024}
            onChange={(e) => setConfig({ max_tokens: Number(e.target.value) })}
          />
        </div>
      </div>
      <div>
        <Label>Tools</Label>
        <div className="flex flex-wrap gap-1.5">
          {tools.map((t) => {
            const selected = ((cfg.tools as string[]) ?? []).includes(t.id);
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => {
                  const current = (cfg.tools as string[]) ?? [];
                  setConfig({
                    tools: selected ? current.filter((id) => id !== t.id) : [...current, t.id],
                  });
                }}
              >
                <Badge tone={selected ? "accent" : "neutral"}>{t.name}</Badge>
              </button>
            );
          })}
          {tools.length === 0 && <span className="text-xs text-ink-faint">No tools registered.</span>}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label>Retries</Label>
          <TextInput
            type="number"
            min={1}
            value={((cfg.retries as { max_attempts?: number })?.max_attempts as number) ?? 1}
            onChange={(e) =>
              setConfig({ retries: { ...(cfg.retries as object), max_attempts: Number(e.target.value) } })
            }
          />
        </div>
        <div>
          <Label>Timeout (s)</Label>
          <TextInput
            type="number"
            min={1}
            value={(cfg.timeout_seconds as number) ?? 60}
            onChange={(e) => setConfig({ timeout_seconds: Number(e.target.value) })}
          />
        </div>
      </div>
    </FieldGroup>
  );
}

function LLMConfig({
  node,
  setConfig,
  models,
}: {
  node: AgentQNode;
  setConfig: (p: Record<string, unknown>) => void;
  models: ModelConfigInfo[];
}) {
  const cfg = node.data.config;
  return (
    <FieldGroup>
      <ModelPicker value={(cfg.model as string) ?? "default"} onChange={(v) => setConfig({ model: v })} models={models} />
      <div>
        <Label>Prompt template</Label>
        <TextArea
          value={(cfg.prompt_template as string) ?? "{input}"}
          onChange={(e) => setConfig({ prompt_template: e.target.value })}
        />
      </div>
    </FieldGroup>
  );
}

function RouterConfig({
  node,
  setConfig,
  models,
}: {
  node: AgentQNode;
  setConfig: (p: Record<string, unknown>) => void;
  models: ModelConfigInfo[];
}) {
  const cfg = node.data.config;
  const rules = (cfg.rules as { when: string; target: string }[]) ?? [];
  const mode = (cfg.mode as string) ?? "rule";
  return (
    <FieldGroup>
      <div>
        <Label>Mode</Label>
        <Select value={mode} onChange={(e) => setConfig({ mode: e.target.value })}>
          <option value="rule">Rule (ordered conditions)</option>
          <option value="expression">Expression</option>
          <option value="llm">LLM</option>
        </Select>
      </div>
      {mode === "llm" && (
        <>
          <ModelPicker value={(cfg.model as string) ?? "default"} onChange={(v) => setConfig({ model: v })} models={models} />
          <div>
            <Label>Routing instructions</Label>
            <TextArea
              value={(cfg.llm_instructions as string) ?? ""}
              onChange={(e) => setConfig({ llm_instructions: e.target.value })}
            />
          </div>
        </>
      )}
      {mode !== "llm" && (
        <div>
          <Label>Rules (evaluated in order)</Label>
          <div className="space-y-2">
            {rules.map((rule, i) => (
              <div key={i} className="flex items-center gap-1.5">
                <TextInput
                  placeholder="input.intent == 'billing'"
                  value={rule.when}
                  onChange={(e) => {
                    const next = [...rules];
                    next[i] = { ...rule, when: e.target.value };
                    setConfig({ rules: next });
                  }}
                />
                <TextInput
                  placeholder="target node id"
                  value={rule.target}
                  onChange={(e) => {
                    const next = [...rules];
                    next[i] = { ...rule, target: e.target.value };
                    setConfig({ rules: next });
                  }}
                />
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setConfig({ rules: rules.filter((_, idx) => idx !== i) })}
                >
                  ✕
                </Button>
              </div>
            ))}
            <Button size="sm" onClick={() => setConfig({ rules: [...rules, { when: "", target: "" }] })}>
              + Add rule
            </Button>
          </div>
        </div>
      )}
      <div>
        <Label>Default target</Label>
        <TextInput
          value={(cfg.default_target as string) ?? ""}
          onChange={(e) => setConfig({ default_target: e.target.value || null })}
        />
      </div>
    </FieldGroup>
  );
}

function SupervisorConfig({
  node,
  setConfig,
  models,
}: {
  node: AgentQNode;
  setConfig: (p: Record<string, unknown>) => void;
  models: ModelConfigInfo[];
}) {
  const cfg = node.data.config;
  const agents = (cfg.agents as string[]) ?? [];
  return (
    <FieldGroup>
      <div>
        <Label>Available agent node IDs (comma separated)</Label>
        <TextInput
          value={agents.join(", ")}
          onChange={(e) =>
            setConfig({
              agents: e.target.value
                .split(",")
                .map((s) => s.trim())
                .filter(Boolean),
            })
          }
        />
      </div>
      <div>
        <Label>Routing instructions</Label>
        <TextArea
          value={(cfg.routing_instructions as string) ?? ""}
          onChange={(e) => setConfig({ routing_instructions: e.target.value })}
        />
      </div>
      <ModelPicker value={(cfg.model as string) ?? "default"} onChange={(v) => setConfig({ model: v })} models={models} />
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label>Max iterations</Label>
          <TextInput
            type="number"
            min={1}
            value={(cfg.max_iterations as number) ?? 6}
            onChange={(e) => setConfig({ max_iterations: Number(e.target.value) })}
          />
        </div>
        <div>
          <Label>Fallback agent</Label>
          <TextInput
            value={(cfg.fallback_agent as string) ?? ""}
            onChange={(e) => setConfig({ fallback_agent: e.target.value || null })}
          />
        </div>
      </div>
    </FieldGroup>
  );
}

function ToolConfig({
  node,
  setConfig,
  tools,
}: {
  node: AgentQNode;
  setConfig: (p: Record<string, unknown>) => void;
  tools: ToolInfo[];
}) {
  const cfg = node.data.config;
  return (
    <FieldGroup>
      <div>
        <Label>Tool</Label>
        <Select value={(cfg.tool_id as string) ?? ""} onChange={(e) => setConfig({ tool_id: e.target.value })}>
          <option value="">Select a tool…</option>
          {tools.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </Select>
      </div>
      <div>
        <Label>Arguments (JSON)</Label>
        <JsonField
          value={(cfg.arguments as Record<string, unknown>) ?? {}}
          onChange={(v) => setConfig({ arguments: v })}
        />
      </div>
    </FieldGroup>
  );
}

function ApprovalConfig({ node, setConfig }: { node: AgentQNode; setConfig: (p: Record<string, unknown>) => void }) {
  const cfg = node.data.config;
  return (
    <FieldGroup>
      <div>
        <Label>Message shown to approver</Label>
        <TextArea
          value={(cfg.message_template as string) ?? ""}
          onChange={(e) => setConfig({ message_template: e.target.value })}
        />
      </div>
      <div>
        <Label>Condition (optional - skip approval when false)</Label>
        <TextInput
          placeholder="variables.amount > 500"
          value={(cfg.condition as string) ?? ""}
          onChange={(e) => setConfig({ condition: e.target.value || null })}
        />
      </div>
    </FieldGroup>
  );
}

function RAGConfig({
  node,
  setConfig,
  knowledgeBases,
}: {
  node: AgentQNode;
  setConfig: (p: Record<string, unknown>) => void;
  knowledgeBases: KnowledgeBase[];
}) {
  const cfg = node.data.config;
  return (
    <FieldGroup>
      <div>
        <Label>Knowledge base</Label>
        <Select
          value={(cfg.knowledge_base_id as string) ?? ""}
          onChange={(e) =>
            handleRegistrySelect(e.target.value, "/knowledge", (v) => setConfig({ knowledge_base_id: v }))
          }
        >
          <option value="">Select a knowledge base…</option>
          {knowledgeBases.map((kb) => (
            <option key={kb.id} value={kb.id}>
              {kb.name}
            </option>
          ))}
          <option value={ADD_NEW_VALUE}>+ Create new knowledge base…</option>
        </Select>
        {knowledgeBases.length === 0 && (
          <p className="mt-1 text-[11px] text-ink-faint">
            No knowledge bases yet - pick &quot;+ Create new knowledge base…&quot; above, or create
            one under Knowledge first.
          </p>
        )}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label>Top K</Label>
          <TextInput
            type="number"
            min={1}
            max={50}
            value={(cfg.top_k as number) ?? 4}
            onChange={(e) => setConfig({ top_k: Number(e.target.value) })}
          />
        </div>
        <div>
          <Label>Min score</Label>
          <TextInput
            type="number"
            step="0.05"
            min={0}
            max={1}
            value={(cfg.min_score as number) ?? 0}
            onChange={(e) => setConfig({ min_score: Number(e.target.value) })}
          />
        </div>
      </div>
      <div>
        <Label>Embedding model key (optional - defaults to MockEmbedding)</Label>
        <TextInput
          placeholder="default"
          value={(cfg.embedding_model as string) ?? ""}
          onChange={(e) => setConfig({ embedding_model: e.target.value || null })}
        />
      </div>
    </FieldGroup>
  );
}

function MemoryConfig({
  node,
  setConfig,
}: {
  node: AgentQNode;
  setConfig: (p: Record<string, unknown>) => void;
}) {
  const cfg = node.data.config;
  return (
    <FieldGroup>
      <div>
        <Label>Memory type</Label>
        <Select
          value={(cfg.memory_type as string) ?? "conversation"}
          onChange={(e) => setConfig({ memory_type: e.target.value })}
        >
          <option value="conversation">Conversation (replays the transcript)</option>
          <option value="semantic">Semantic (embeds + recalls relevant facts)</option>
        </Select>
      </div>
      <div>
        <Label>Scope</Label>
        <Select value={(cfg.scope as string) ?? "agent"} onChange={(e) => setConfig({ scope: e.target.value })}>
          <option value="run">Run - cleared at the end of each run</option>
          <option value="agent">Agent - persists across runs, keyed by this node</option>
          <option value="workspace">Workspace - shared across the whole workspace</option>
        </Select>
      </div>
      <div>
        <Label>TTL seconds (optional)</Label>
        <TextInput
          type="number"
          placeholder="no expiry"
          value={(cfg.ttl_seconds as number) ?? ""}
          onChange={(e) => setConfig({ ttl_seconds: e.target.value ? Number(e.target.value) : null })}
        />
      </div>
    </FieldGroup>
  );
}

function McpConfig({
  node,
  setConfig,
  servers,
}: {
  node: AgentQNode;
  setConfig: (p: Record<string, unknown>) => void;
  servers: McpServerInfo[];
}) {
  const cfg = node.data.config;
  const selected = servers.find((s) => s.id === cfg.server_id);
  return (
    <FieldGroup>
      <div>
        <Label>MCP server</Label>
        <Select
          value={(cfg.server_id as string) ?? ""}
          onChange={(e) =>
            handleRegistrySelect(e.target.value, "/mcp-servers", (v) =>
              setConfig({ server_id: v, tool_name: "" })
            )
          }
        >
          <option value="">Select a server…</option>
          {servers.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name} ({s.status})
            </option>
          ))}
          <option value={ADD_NEW_VALUE}>+ Register new MCP server…</option>
        </Select>
        {servers.length === 0 && (
          <p className="mt-1 text-[11px] text-ink-faint">
            No MCP servers yet - pick &quot;+ Register new MCP server…&quot; above, or register one
            under MCP Servers first.
          </p>
        )}
      </div>
      <div>
        <Label>Tool</Label>
        <Select
          value={(cfg.tool_name as string) ?? ""}
          onChange={(e) => setConfig({ tool_name: e.target.value })}
          disabled={!selected}
        >
          <option value="">Select a tool…</option>
          {(selected?.tools ?? []).map((t) => (
            <option key={t.name} value={t.name}>
              {t.name}
            </option>
          ))}
        </Select>
      </div>
      <div>
        <Label>Arguments (JSON - supports {"{{input.field}}"} templating)</Label>
        <JsonField
          value={(cfg.arguments as Record<string, unknown>) ?? {}}
          onChange={(v) => setConfig({ arguments: v })}
        />
      </div>
    </FieldGroup>
  );
}

const GUARDRAIL_CHECK_LABELS: Record<string, string> = {
  pii_detection: "PII detection (email/phone/SSN/credit card)",
  blocked_keywords: "Blocked keywords",
  prompt_injection_heuristic: "Prompt-injection heuristic",
  max_input_size: "Max input size",
  output_validation: "Output validation (non-empty)",
  json_schema: "JSON schema",
};

type GuardrailCheck = { type: string; config: Record<string, unknown> };

function GuardrailConfig({
  node,
  setConfig,
}: {
  node: AgentQNode;
  setConfig: (p: Record<string, unknown>) => void;
}) {
  const cfg = node.data.config;
  const checks = ((cfg.checks as GuardrailCheck[] | undefined) ?? []).slice();
  const checksByType = new Map(checks.map((c) => [c.type, c]));

  const toggle = (type: string) => {
    const next = checksByType.has(type)
      ? checks.filter((c) => c.type !== type)
      : [...checks, { type, config: {} }];
    setConfig({ checks: next });
  };

  const updateCheckConfig = (type: string, key: string, value: unknown) => {
    const next = checks.map((c) => (c.type === type ? { ...c, config: { ...c.config, [key]: value } } : c));
    setConfig({ checks: next });
  };

  return (
    <FieldGroup>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label>Stage</Label>
          <Select value={(cfg.stage as string) ?? "pre"} onChange={(e) => setConfig({ stage: e.target.value })}>
            <option value="pre">Pre (before the node runs)</option>
            <option value="post">Post (after the node runs)</option>
          </Select>
        </div>
        <div>
          <Label>On violation</Label>
          <Select value={(cfg.on_fail as string) ?? "block"} onChange={(e) => setConfig({ on_fail: e.target.value })}>
            <option value="block">Block the run</option>
            <option value="warn">Warn only</option>
          </Select>
        </div>
      </div>
      <div>
        <Label>Checks</Label>
        <div className="space-y-2">
          {Object.entries(GUARDRAIL_CHECK_LABELS).map(([type, label]) => {
            const check = checksByType.get(type);
            return (
              <div key={type} className="rounded-md border border-border px-2.5 py-1.5">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={!!check}
                    onChange={() => toggle(type)}
                    className="accent-accent"
                  />
                  {label}
                </label>
                {check && type === "blocked_keywords" && (
                  <TextInput
                    className="mt-1.5 text-xs"
                    placeholder="comma-separated keywords"
                    onChange={(e) =>
                      updateCheckConfig(
                        type,
                        "keywords",
                        e.target.value.split(",").map((k) => k.trim()).filter(Boolean)
                      )
                    }
                  />
                )}
                {check && type === "max_input_size" && (
                  <TextInput
                    type="number"
                    className="mt-1.5 text-xs"
                    placeholder="max characters"
                    onChange={(e) => updateCheckConfig(type, "max_chars", Number(e.target.value))}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </FieldGroup>
  );
}

function ModelPicker({
  value,
  onChange,
  models,
}: {
  value: string;
  onChange: (v: string) => void;
  models: ModelConfigInfo[];
}) {
  return (
    <div>
      <Label>Model</Label>
      <Select value={value} onChange={(e) => handleRegistrySelect(e.target.value, "/models", onChange)}>
        <option value="default">default (MockLLM)</option>
        {models.map((m) => (
          <option key={m.id} value={m.model_key}>
            {m.model_key} ({m.provider})
          </option>
        ))}
        <option value={ADD_NEW_VALUE}>+ Connect new model…</option>
      </Select>
    </div>
  );
}

function JsonField({
  value,
  onChange,
}: {
  value: Record<string, unknown>;
  onChange: (v: Record<string, unknown>) => void;
}) {
  const [text, setText] = useState(() => JSON.stringify(value, null, 2));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setText(JSON.stringify(value, null, 2));
  }, [value]);

  return (
    <div>
      <TextArea
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          try {
            const parsed = JSON.parse(e.target.value);
            setError(null);
            onChange(parsed);
          } catch {
            setError("Invalid JSON");
          }
        }}
        className="font-mono text-xs"
      />
      {error && <p className="mt-1 text-xs text-danger">{error}</p>}
    </div>
  );
}
