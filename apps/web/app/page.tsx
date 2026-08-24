"use client";

import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, CircleDollarSign, type LucideIcon, Timer, Workflow, Zap } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { formatCost, formatRelativeTime } from "@/lib/utils";

function StatTile({
  label,
  value,
  sub,
  icon: Icon,
}: {
  label: string;
  value: string;
  sub?: string;
  icon: LucideIcon;
}) {
  return (
    <Card>
      <CardBody className="py-4">
        <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-ink-faint">
          <Icon size={12} />
          {label}
        </div>
        <div className="mt-1.5 text-2xl font-semibold text-ink">{value}</div>
        {sub && <div className="mt-0.5 text-xs text-ink-faint">{sub}</div>}
      </CardBody>
    </Card>
  );
}

export default function DashboardPage() {
  const runsQuery = useQuery({ queryKey: ["runs", "dashboard"], queryFn: () => api.listRuns({ limit: 50 }) });
  const flowsQuery = useQuery({ queryKey: ["flows"], queryFn: api.listFlows });

  const runs = runsQuery.data ?? [];
  const today = new Date().toDateString();
  const runsToday = runs.filter((r) => new Date(r.created_at).toDateString() === today);
  const succeeded = runs.filter((r) => r.status === "SUCCEEDED").length;
  const successRate = runs.length > 0 ? `${Math.round((succeeded / runs.length) * 100)}%` : "-";
  const durations = runs
    .filter((r) => r.started_at && r.completed_at)
    .map((r) => new Date(r.completed_at!).getTime() - new Date(r.started_at!).getTime());
  const avgLatency = durations.length > 0 ? `${Math.round(durations.reduce((a, b) => a + b, 0) / durations.length)} ms` : "-";
  const costToday = runsToday.reduce(
    (sum, r) => sum + r.steps.reduce((s, step) => s + step.estimated_cost_usd, 0),
    0
  );

  return (
    <div className="scrollbar-thin h-full overflow-y-auto p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold text-ink">AI Control Center</h1>
        <p className="text-sm text-ink-muted">Production status for your agent workflows.</p>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-5">
        <StatTile label="Active Flows" value={String(flowsQuery.data?.length ?? "-")} icon={Workflow} />
        <StatTile label="Runs Today" value={String(runsToday.length)} icon={Zap} />
        <StatTile
          label="Success Rate"
          value={successRate}
          sub={`${runs.length} runs total`}
          icon={CheckCircle2}
        />
        <StatTile label="Avg Latency" value={avgLatency} icon={Timer} />
        <StatTile
          label="API Cost Today"
          value={formatCost(costToday)}
          sub="local models excluded from cost"
          icon={CircleDollarSign}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex items-center justify-between">
            <span className="text-sm font-medium">Recent Runs</span>
            <Link href="/runs" className="text-xs text-accent hover:underline">
              View all
            </Link>
          </CardHeader>
          <CardBody className="p-0">
            {runs.length === 0 ? (
              <p className="px-4 py-6 text-center text-sm text-ink-faint">
                No runs yet - open a flow and click Run to see it here
              </p>
            ) : (
              <div className="divide-y divide-border">
                {runs.slice(0, 8).map((r) => {
                  const flowName = (flowsQuery.data ?? []).find((f) => f.id === r.flow_id)?.name;
                  return (
                    <Link
                      key={r.id}
                      href={`/runs/${r.id}`}
                      className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm hover:bg-surface-raised"
                    >
                      <span className="truncate text-ink">{flowName ?? "Unknown flow"}</span>
                      <span className="flex shrink-0 items-center gap-3">
                        <StatusBadge status={r.status} />
                        <span className="text-xs text-ink-faint">{formatRelativeTime(r.created_at)}</span>
                      </span>
                    </Link>
                  );
                })}
              </div>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <span className="text-sm font-medium">Flows</span>
          </CardHeader>
          <CardBody className="p-0">
            {(flowsQuery.data ?? []).length === 0 ? (
              <p className="px-4 py-6 text-center text-sm text-ink-faint">No flows yet - create one to get started</p>
            ) : (
              <div className="divide-y divide-border">
                {(flowsQuery.data ?? []).slice(0, 8).map((f) => (
                  <Link
                    key={f.id}
                    href={`/flows/${f.id}`}
                    className="flex items-center justify-between px-4 py-2.5 text-sm hover:bg-surface-raised"
                  >
                    <span className="truncate">{f.name}</span>
                    <Badge tone={f.status === "published" ? "success" : "neutral"}>{f.status}</Badge>
                  </Link>
                ))}
              </div>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const tone =
    status === "SUCCEEDED"
      ? "success"
      : status === "FAILED"
        ? "danger"
        : status === "WAITING_FOR_HUMAN"
          ? "warning"
          : "neutral";
  return (
    <Badge tone={tone} pulse={status === "RUNNING" || status === "WAITING_FOR_HUMAN"}>
      {status.replace(/_/g, " ")}
    </Badge>
  );
}
