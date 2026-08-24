"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";
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

import { cn } from "@/lib/utils";
import type { AgentQNode, NodeExecutionStatus } from "@/lib/canvas-store";
import type { NodeType } from "@/lib/flowspec";

const ICON_BY_TYPE: Record<NodeType, LucideIcon> = {
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

const STATUS_RING: Record<NodeExecutionStatus, string> = {
  idle: "ring-1 ring-border",
  queued: "ring-2 ring-ink-faint",
  running: "ring-2 ring-accent shadow-[0_0_0_4px_rgb(var(--color-accent)/0.15)] animate-pulse",
  success: "ring-2 ring-success",
  failed: "ring-2 ring-danger",
  waiting: "ring-2 ring-warning",
  skipped: "ring-1 ring-border opacity-60",
};

const STATUS_DOT: Record<NodeExecutionStatus, string> = {
  idle: "bg-ink-faint",
  queued: "bg-ink-faint",
  running: "bg-accent animate-pulse",
  success: "bg-success",
  failed: "bg-danger",
  waiting: "bg-warning",
  skipped: "bg-ink-faint",
};

export function AgentQNodeView({ data, selected }: NodeProps<AgentQNode>) {
  const Icon = ICON_BY_TYPE[data.nodeType];
  const isTerminalInput = data.nodeType === "input";
  const isTerminalOutput = data.nodeType === "output";

  return (
    <div
      className={cn(
        "min-w-[180px] rounded-lg border border-border bg-surface shadow-panel transition-shadow",
        STATUS_RING[data.status],
        selected && "ring-2 ring-accent"
      )}
    >
      {!isTerminalInput && (
        <Handle type="target" position={Position.Left} className="!h-2.5 !w-2.5 !bg-ink-faint" />
      )}
      <div className="flex items-center gap-2 px-3 py-2">
        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-accent/10 text-accent">
          <Icon size={14} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-[13px] font-medium text-ink">{data.label}</div>
          <div className="truncate text-[11px] text-ink-faint">{data.nodeType}</div>
        </div>
        <span className={cn("h-2 w-2 shrink-0 rounded-full", STATUS_DOT[data.status])} />
      </div>
      {!isTerminalOutput && (
        <Handle type="source" position={Position.Right} className="!h-2.5 !w-2.5 !bg-ink-faint" />
      )}
    </div>
  );
}
