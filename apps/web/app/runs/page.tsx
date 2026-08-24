"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardBody } from "@/components/ui/card";
import { api, type Run } from "@/lib/api-client";
import { cn, formatCost, formatDuration, formatRelativeTime } from "@/lib/utils";

function statusTone(status: string) {
  if (status === "SUCCEEDED") return "success" as const;
  if (status === "FAILED") return "danger" as const;
  if (status === "WAITING_FOR_HUMAN" || status === "RUNNING") return "warning" as const;
  return "neutral" as const;
}

function runDurationMs(run: Run): number | null {
  if (!run.started_at || !run.completed_at) return null;
  return new Date(run.completed_at).getTime() - new Date(run.started_at).getTime();
}

function runCostUsd(run: Run): number {
  return run.steps.reduce((sum, s) => sum + (s.estimated_cost_usd || 0), 0);
}

export default function RunsPage() {
  const runsQuery = useQuery({ queryKey: ["runs", "all"], queryFn: () => api.listRuns({ limit: 100 }) });
  const flowsQuery = useQuery({ queryKey: ["flows"], queryFn: api.listFlows });
  const runs = runsQuery.data ?? [];
  const flowNameById = new Map((flowsQuery.data ?? []).map((f) => [f.id, f.name]));

  return (
    <div className="scrollbar-thin h-full overflow-y-auto p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold text-ink">Runs</h1>
        <p className="text-sm text-ink-muted">
          Every workflow execution across this workspace - the flight recorder&apos;s index. Click a run for
          per-step timing, tokens, and cost.
        </p>
      </div>

      <Card>
        <CardBody className="p-0">
          {runs.length === 0 ? (
            <p className="px-4 py-10 text-center text-sm text-ink-faint">
              No runs yet - open a flow and click Run to see it here
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-ink-faint">
                  <th className="px-4 py-2 font-medium">Flow / Run</th>
                  <th className="px-4 py-2 font-medium">Status</th>
                  <th className="px-4 py-2 font-medium">Steps</th>
                  <th className="px-4 py-2 font-medium">Duration</th>
                  <th className="px-4 py-2 font-medium">Cost</th>
                  <th className="px-4 py-2 font-medium">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {runs.map((r) => {
                  const cost = runCostUsd(r);
                  return (
                    <tr key={r.id} className="hover:bg-surface-raised">
                      <td className="px-4 py-2.5">
                        <Link href={`/runs/${r.id}`} className="group block">
                          <div className="font-medium text-ink group-hover:text-accent">
                            {flowNameById.get(r.flow_id) ?? "Unknown flow"}
                          </div>
                          <div className="font-mono text-[11px] text-ink-faint">{r.id.slice(0, 12)}</div>
                        </Link>
                      </td>
                      <td className="px-4 py-2.5">
                        <Badge
                          tone={statusTone(r.status)}
                          pulse={r.status === "RUNNING" || r.status === "WAITING_FOR_HUMAN"}
                        >
                          {r.status.replace(/_/g, " ")}
                        </Badge>
                      </td>
                      <td className="px-4 py-2.5 text-ink-muted">{r.steps.length}</td>
                      <td className="px-4 py-2.5 text-ink-muted">{formatDuration(runDurationMs(r))}</td>
                      <td className={cn("px-4 py-2.5", cost > 0 ? "text-ink-muted" : "text-ink-faint")}>
                        {formatCost(cost)}
                      </td>
                      <td className="px-4 py-2.5 text-ink-faint">{formatRelativeTime(r.created_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
