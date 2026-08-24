"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Redo2, XCircle } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { api, resumeRun, replayRun, type RunStep } from "@/lib/api-client";
import { formatCost, formatDuration } from "@/lib/utils";

function statusTone(status: string) {
  if (status === "SUCCEEDED") return "success" as const;
  if (status === "FAILED") return "danger" as const;
  if (status === "WAITING_FOR_HUMAN" || status === "RUNNING") return "warning" as const;
  return "neutral" as const;
}

export default function TracePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const runId = params.id;

  const runQuery = useQuery({
    queryKey: ["run", runId],
    queryFn: () => api.getRun(runId),
    refetchInterval: (query) =>
      query.state.data && ["RUNNING", "WAITING_FOR_HUMAN"].includes(query.state.data.status) ? 2000 : false,
  });

  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);
  const [resuming, setResuming] = useState(false);
  const [replaying, setReplaying] = useState(false);

  const run = runQuery.data;
  const selectedStep = run?.steps.find((s) => s.id === selectedStepId) ?? run?.steps[run.steps.length - 1];

  async function handleDecision(approved: boolean) {
    setResuming(true);
    try {
      const stream = resumeRun(runId, approved);
      for await (const _event of stream) {
        void _event; // draining stream; UI updates via polling
      }
      queryClient.invalidateQueries({ queryKey: ["run", runId] });
    } finally {
      setResuming(false);
    }
  }

  async function handleReplay() {
    setReplaying(true);
    try {
      const stream = replayRun(runId);
      let next = await stream.next();
      while (!next.done) next = await stream.next();
      if (next.value) router.push(`/runs/${next.value}`);
    } finally {
      setReplaying(false);
    }
  }

  if (runQuery.isLoading) return <div className="p-6 text-sm text-ink-faint">Loading trace…</div>;
  if (!run) return <div className="p-6 text-sm text-danger">Run not found.</div>;

  const totalCost = run.steps.reduce((s, step) => s + step.estimated_cost_usd, 0);
  const totalTokens = run.steps.reduce((s, step) => s + step.total_tokens, 0);

  return (
    <div className="scrollbar-thin grid h-full grid-cols-[1fr_360px] overflow-hidden">
      <div className="scrollbar-thin overflow-y-auto p-6">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-semibold text-ink">Run {run.id.slice(0, 8)}</h1>
              <Badge
                tone={statusTone(run.status)}
                pulse={run.status === "RUNNING" || run.status === "WAITING_FOR_HUMAN"}
              >
                {run.status.replace(/_/g, " ")}
              </Badge>
            </div>
            <p className="text-xs text-ink-faint">
              {totalTokens} tokens · {formatCost(totalCost)} · created {new Date(run.created_at).toLocaleString()}
            </p>
          </div>
          <Button size="sm" variant="secondary" onClick={handleReplay} disabled={replaying}>
            <Redo2 size={13} /> {replaying ? "Replaying…" : "Replay"}
          </Button>
        </div>

        {run.status === "WAITING_FOR_HUMAN" && (
          <Card className="mb-4 border-warning/40 bg-warning/5">
            <CardBody className="flex items-center justify-between py-3">
              <span className="text-sm text-ink">Waiting for human approval</span>
              <div className="flex gap-2">
                <Button size="sm" variant="primary" disabled={resuming} onClick={() => handleDecision(true)}>
                  <CheckCircle2 size={13} /> Approve
                </Button>
                <Button size="sm" variant="danger" disabled={resuming} onClick={() => handleDecision(false)}>
                  <XCircle size={13} /> Reject
                </Button>
              </div>
            </CardBody>
          </Card>
        )}

        {run.error && (
          <Card className="mb-4 border-danger/40 bg-danger/5">
            <CardBody className="py-3 text-sm text-danger">{run.error}</CardBody>
          </Card>
        )}

        <Card>
          <CardHeader>
            <span className="text-sm font-medium">Execution Steps</span>
          </CardHeader>
          <CardBody className="p-0">
            <div className="divide-y divide-border">
              {run.steps.map((step) => (
                <StepRow
                  key={step.id}
                  step={step}
                  selected={step.id === selectedStep?.id}
                  onSelect={() => setSelectedStepId(step.id)}
                />
              ))}
            </div>
          </CardBody>
        </Card>

        <Card className="mt-4">
          <CardHeader>
            <span className="text-sm font-medium">Final Output</span>
          </CardHeader>
          <CardBody>
            <pre className="scrollbar-thin overflow-auto text-xs text-ink-muted">
              {JSON.stringify(run.output, null, 2) ?? "null"}
            </pre>
          </CardBody>
        </Card>
      </div>

      <div className="scrollbar-thin overflow-y-auto border-l border-border bg-surface">
        {selectedStep ? <StepDetail step={selectedStep} /> : (
          <div className="p-6 text-sm text-ink-faint">Select a step to inspect it.</div>
        )}
      </div>
    </div>
  );
}

function StepRow({ step, selected, onSelect }: { step: RunStep; selected: boolean; onSelect: () => void }) {
  return (
    <button
      onClick={onSelect}
      className={`flex w-full items-center justify-between px-4 py-2.5 text-left text-sm hover:bg-surface-raised ${selected ? "bg-accent/5" : ""}`}
    >
      <div className="flex items-center gap-2">
        <Badge tone={statusTone(step.status === "SUCCEEDED" ? "SUCCEEDED" : step.status === "FAILED" ? "FAILED" : "RUNNING")}>
          {step.status}
        </Badge>
        <span className="text-ink">{step.node_id}</span>
        <span className="text-xs text-ink-faint">{step.node_type}</span>
      </div>
      <span className="text-xs text-ink-faint">{formatDuration(step.latency_ms)}</span>
    </button>
  );
}

function StepDetail({ step }: { step: RunStep }) {
  return (
    <div className="p-4">
      <div className="mb-3">
        <div className="text-[11px] uppercase tracking-wide text-ink-faint">{step.node_type}</div>
        <div className="text-sm font-medium text-ink">{step.node_id}</div>
      </div>

      <DetailSection title="Metadata">
        <KeyValue label="Status" value={step.status} />
        <KeyValue label="Model" value={step.model ?? "-"} />
        <KeyValue label="Provider" value={step.provider ?? "-"} />
      </DetailSection>

      <DetailSection title="Timing">
        <KeyValue label="Started" value={step.started_at ? new Date(step.started_at).toLocaleTimeString() : "-"} />
        <KeyValue label="Latency" value={formatDuration(step.latency_ms)} />
      </DetailSection>

      <DetailSection title="Tokens & Cost">
        <KeyValue label="Prompt tokens" value={String(step.input_tokens)} />
        <KeyValue label="Completion tokens" value={String(step.output_tokens)} />
        <KeyValue label="Total tokens" value={String(step.total_tokens)} />
        <KeyValue label="Est. API cost" value={formatCost(step.estimated_cost_usd)} />
      </DetailSection>

      {step.routing_decision && (
        <DetailSection title="Routing Decision">
          <KeyValue label="Target" value={String(step.routing_decision.target ?? "-")} />
          <p className="mt-1 text-xs text-ink-muted">{String(step.routing_decision.reason ?? "")}</p>
        </DetailSection>
      )}

      {step.tool_id && (
        <DetailSection title="Tool Call">
          <KeyValue label="Tool" value={step.tool_id} />
          <pre className="scrollbar-thin mt-1 overflow-auto rounded bg-surface-raised p-2 text-[11px]">
            {JSON.stringify(step.tool_arguments, null, 2)}
          </pre>
        </DetailSection>
      )}

      <DetailSection title="Output">
        <pre className="scrollbar-thin overflow-auto rounded bg-surface-raised p-2 text-[11px]">
          {JSON.stringify(step.output_data, null, 2) ?? "-"}
        </pre>
      </DetailSection>

      {step.error && (
        <DetailSection title="Errors">
          <p className="text-xs text-danger">{step.error}</p>
        </DetailSection>
      )}
    </div>
  );
}

function DetailSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-ink-faint">{title}</div>
      {children}
    </div>
  );
}

function KeyValue({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-0.5 text-xs">
      <span className="text-ink-faint">{label}</span>
      <span className="font-medium text-ink">{value}</span>
    </div>
  );
}
