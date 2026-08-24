"use client";

import { Send } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TextArea, TextInput } from "@/components/ui/field";
import { runFlow, type RunEventPayload } from "@/lib/api-client";
import { useCanvasStore, type NodeExecutionStatus } from "@/lib/canvas-store";
import type { InputField } from "@/lib/flowspec";
import { cn } from "@/lib/utils";

const EVENT_TO_NODE_STATUS: Partial<Record<string, NodeExecutionStatus>> = {
  "node.started": "running",
  "node.completed": "success",
  "node.failed": "failed",
};

type Tab = "playground" | "run" | "output" | "errors";

interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "error";
  content: string;
}

function outputToText(value: unknown): string {
  if (typeof value === "string") return value;
  if (value === null || value === undefined) return "(empty output)";
  return JSON.stringify(value, null, 2);
}

export function RunPanel({ flowId, inputFields }: { flowId: string | null; inputFields: InputField[] }) {
  const [tab, setTab] = useState<Tab>("playground");
  const [inputText, setInputText] = useState('{\n  "query": "Hello, AgentQ!"\n}');
  const [chatInput, setChatInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [running, setRunning] = useState(false);
  const [events, setEvents] = useState<RunEventPayload[]>([]);
  const [runId, setRunId] = useState<string | null>(null);
  const [output, setOutput] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const setNodeStatus = useCanvasStore((s) => s.setNodeStatus);
  const resetExecutionState = useCanvasStore((s) => s.resetExecutionState);

  const errorEvents = events.filter((e) => e.type === "node.failed" || e.type === "run.failed");
  const primaryFieldName = inputFields[0]?.name ?? "message";

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, running]);

  /** Streams one run and updates canvas node status / events / trace link as a side effect.
   * Returns the resolved output text (or error text) so callers - the raw JSON runner and the
   * chat playground - can each render it their own way. */
  async function executeRun(inputs: Record<string, unknown>): Promise<{ text: string; failed: boolean }> {
    if (!flowId) {
      const text = "Save the flow before running it.";
      setError(text);
      return { text, failed: true };
    }

    setRunning(true);
    setError(null);
    setEvents([]);
    setOutput(null);
    resetExecutionState();

    let finalOutput: unknown = null;
    let failure: string | null = null;
    try {
      const stream = runFlow(flowId, inputs);
      let next = await stream.next();
      while (!next.done) {
        const event = next.value;
        setEvents((prev) => [...prev, event]);
        if (event.node_id && EVENT_TO_NODE_STATUS[event.type]) {
          setNodeStatus(event.node_id, EVENT_TO_NODE_STATUS[event.type]!);
        }
        if (event.type === "run.waiting" && event.node_id) {
          setNodeStatus(event.node_id, "waiting");
        }
        if (event.type === "node.completed") {
          finalOutput = event.data.output;
        }
        if (event.type === "run.failed") {
          failure = (event.data.error as string) ?? "Run failed.";
          setError(failure);
        }
        next = await stream.next();
      }
      if (next.value) setRunId(next.value);
    } catch (err) {
      failure = err instanceof Error ? err.message : "Run failed.";
      setError(failure);
    } finally {
      setRunning(false);
    }

    if (failure) return { text: failure, failed: true };
    setOutput(finalOutput);
    return { text: outputToText(finalOutput), failed: false };
  }

  async function handleRun() {
    let inputs: Record<string, unknown>;
    try {
      inputs = JSON.parse(inputText);
    } catch {
      setError("Input must be valid JSON.");
      return;
    }
    setTab("run");
    await executeRun(inputs);
  }

  async function handleChatSend() {
    const text = chatInput.trim();
    if (!text || running) return;
    setChatInput("");
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", content: text }]);
    const result = await executeRun({ [primaryFieldName]: text });
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: result.failed ? "error" : "assistant", content: result.text },
    ]);
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border px-3">
        <div className="flex">
          {(["playground", "run", "output", "errors"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                "border-b-2 px-3 py-2 text-xs font-medium uppercase tracking-wide transition-colors",
                tab === t ? "border-accent text-ink" : "border-transparent text-ink-faint hover:text-ink-muted"
              )}
            >
              {t}
              {t === "errors" && errorEvents.length > 0 && (
                <span className="ml-1.5 rounded-full bg-danger/15 px-1.5 py-0.5 text-[10px] text-danger">
                  {errorEvents.length}
                </span>
              )}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 py-1.5">
          {runId && (
            <Link href={`/runs/${runId}`} className="text-xs text-accent hover:underline">
              Open trace →
            </Link>
          )}
          {tab === "run" && (
            <Button size="sm" variant="primary" onClick={handleRun} disabled={running}>
              {running ? "Running…" : "▶ Run"}
            </Button>
          )}
        </div>
      </div>

      <div className="scrollbar-thin flex-1 overflow-y-auto p-3">
        {tab === "playground" && (
          <div className="flex h-full flex-col">
            <div className="scrollbar-thin flex-1 space-y-2 overflow-y-auto px-1">
              {messages.length === 0 && (
                <p className="px-2 py-6 text-center text-sm text-ink-faint">
                  Try this flow conversationally - sent as{" "}
                  <code className="text-xs">{`{ "${primaryFieldName}": "..." }`}</code>.
                </p>
              )}
              {messages.map((m) => (
                <div key={m.id} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
                  <div
                    className={cn(
                      "max-w-[80%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm",
                      m.role === "user" && "bg-accent text-accent-ink",
                      m.role === "assistant" && "border border-border bg-surface-raised text-ink",
                      m.role === "error" && "border border-danger/30 bg-danger/10 text-danger"
                    )}
                  >
                    {m.content}
                  </div>
                </div>
              ))}
              {running && (
                <div className="flex justify-start">
                  <div className="flex items-center gap-1 rounded-lg border border-border bg-surface-raised px-3 py-2.5">
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-ink-faint [animation-delay:-0.3s]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-ink-faint [animation-delay:-0.15s]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-ink-faint" />
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
            <div className="flex items-center gap-2 border-t border-border pt-2">
              <TextInput
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleChatSend();
                  }
                }}
                placeholder={flowId ? `Message (as "${primaryFieldName}")` : "Save the flow first"}
                disabled={running || !flowId}
              />
              <Button
                size="sm"
                variant="primary"
                onClick={handleChatSend}
                disabled={running || !chatInput.trim() || !flowId}
              >
                <Send size={13} />
              </Button>
            </div>
          </div>
        )}

        {tab === "run" && (
          <div className="grid h-full grid-cols-[240px_1fr] gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-ink-muted">Input JSON</label>
              <TextArea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                className="h-32 font-mono text-xs"
              />
            </div>
            <div className="scrollbar-thin overflow-y-auto rounded-md border border-border bg-surface-raised p-2 font-mono text-xs">
              {events.length === 0 && <p className="text-ink-faint">No run yet.</p>}
              {events.map((e, i) => (
                <div key={i} className="flex gap-2 py-0.5">
                  <span className="text-ink-faint">{new Date(e.timestamp).toLocaleTimeString()}</span>
                  <span
                    className={cn(
                      e.type.includes("failed") && "text-danger",
                      e.type === "run.completed" && "text-success",
                      e.type === "run.waiting" && "text-warning"
                    )}
                  >
                    {e.type}
                  </span>
                  {e.node_id && <span className="text-ink-muted">{e.node_id}</span>}
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === "output" && (
          <pre className="scrollbar-thin overflow-auto rounded-md border border-border bg-surface-raised p-3 text-xs">
            {outputToText(output)}
          </pre>
        )}

        {tab === "errors" && (
          <div className="space-y-2">
            {errorEvents.length === 0 && <p className="text-sm text-ink-faint">No errors.</p>}
            {errorEvents.map((e, i) => (
              <div key={i} className="rounded-md border border-danger/30 bg-danger/5 p-2 text-xs">
                <div className="mb-1 flex items-center gap-2">
                  <Badge tone="danger">{e.type}</Badge>
                  {e.node_id && <span className="text-ink-muted">{e.node_id}</span>}
                </div>
                <pre className="whitespace-pre-wrap text-ink-muted">{JSON.stringify(e.data, null, 2)}</pre>
              </div>
            ))}
          </div>
        )}
      </div>

      {error && tab !== "playground" && (
        <div className="border-t border-danger/30 bg-danger/5 px-3 py-1.5 text-xs text-danger">{error}</div>
      )}
    </div>
  );
}
