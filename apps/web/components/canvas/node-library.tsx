"use client";

import {
  ArrowRightLeft,
  Bot,
  Database,
  FileInput,
  FileOutput,
  GitBranch,
  ShieldCheck,
  Sparkles,
  UserCheck,
  Users,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import { useMemo, useState } from "react";

import { NODE_CATEGORY, NODE_LABEL, type NodeType } from "@/lib/flowspec";
import { cn } from "@/lib/utils";

const CATEGORY_ORDER = ["CORE", "AI", "AGENTS", "KNOWLEDGE", "TOOLS", "CONTROL", "SECURITY"] as const;

const ICON: Record<NodeType, LucideIcon> = {
  input: FileInput,
  output: FileOutput,
  agent: Bot,
  llm: Sparkles,
  router: GitBranch,
  supervisor: Users,
  tool: Wrench,
  mcp: ArrowRightLeft,
  rag: Database,
  memory: Database,
  human_approval: UserCheck,
  guardrail: ShieldCheck,
};

const NODE_DESCRIPTION: Record<NodeType, string> = {
  input: "Where a run's data enters the flow",
  output: "What a run returns when it finishes",
  agent: "An LLM with instructions, a model, and optional tools",
  llm: "A single raw model call, no agent framing",
  router: "Send execution down one of several branches by rule or LLM decision",
  supervisor: "Delegates a task to one of several sub-agents",
  tool: "Calls an HTTP endpoint, calculator, or other built-in function",
  mcp: "Calls a tool exposed by a registered MCP server",
  rag: "Retrieves relevant chunks from a knowledge base before the agent responds",
  memory: "Persists conversation or semantic memory across runs",
  human_approval: "Pauses the run until a person approves or rejects",
  guardrail: "Checks input/output against PII, keyword, or schema rules",
};

const ALL_TYPES = Object.keys(NODE_LABEL) as NodeType[];

export function NodeLibrary() {
  const [query, setQuery] = useState("");

  const grouped = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = ALL_TYPES.filter((t) => !q || NODE_LABEL[t].toLowerCase().includes(q));
    const map = new Map<string, NodeType[]>();
    for (const category of CATEGORY_ORDER) map.set(category, []);
    for (const type of filtered) {
      const category = NODE_CATEGORY[type];
      map.set(category, [...(map.get(category) ?? []), type]);
    }
    return map;
  }, [query]);

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border p-3">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search nodes…"
          aria-label="Search nodes"
          className="w-full rounded-md border border-border bg-surface px-2.5 py-1.5 text-sm placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-accent/40"
        />
      </div>
      <div className="scrollbar-thin flex-1 overflow-y-auto p-3">
        {CATEGORY_ORDER.map((category) => {
          const types = grouped.get(category) ?? [];
          if (types.length === 0) return null;
          return (
            <div key={category} className="mb-4">
              <div className="mb-1.5 px-1 text-[10px] font-semibold uppercase tracking-wider text-ink-faint">
                {category}
              </div>
              <div className="space-y-1">
                {types.map((type) => {
                  const Icon = ICON[type];
                  return (
                    <div
                      key={type}
                      draggable
                      title={NODE_DESCRIPTION[type]}
                      onDragStart={(e) => {
                        e.dataTransfer.setData("application/agentq-node-type", type);
                        e.dataTransfer.effectAllowed = "move";
                      }}
                      className={cn(
                        "flex cursor-grab items-start gap-2 rounded-md border border-transparent px-2 py-1.5 text-ink",
                        "transition-[transform,border-color,background-color] duration-150 ease-out",
                        "hover:border-accent/40 hover:bg-accent/5 hover:translate-x-0.5",
                        "active:cursor-grabbing active:scale-[0.98]"
                      )}
                    >
                      <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-accent/10 text-accent">
                        <Icon size={13} />
                      </span>
                      <span className="min-w-0">
                        <div className="text-sm leading-tight">{NODE_LABEL[type]}</div>
                        <div className="truncate text-[11px] leading-tight text-ink-faint">
                          {NODE_DESCRIPTION[type]}
                        </div>
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
