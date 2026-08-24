"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Label, TextInput } from "@/components/ui/field";
import { api } from "@/lib/api-client";
import { formatRelativeTime } from "@/lib/utils";

function ToolPolicyPanel() {
  const queryClient = useQueryClient();
  const policyQuery = useQuery({ queryKey: ["policy"], queryFn: api.getPolicy });
  const [value, setValue] = useState("");

  useEffect(() => {
    if (policyQuery.data) setValue(policyQuery.data.denied_tools.join(", "));
  }, [policyQuery.data]);

  const save = useMutation({
    mutationFn: () =>
      api.updatePolicy(
        value
          .split(",")
          .map((v) => v.trim())
          .filter(Boolean)
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["policy"] }),
  });

  return (
    <Card className="mb-6">
      <CardHeader className="flex items-center gap-2">
        <ShieldAlert size={14} className="text-accent" />
        <span className="text-sm font-medium">Tool Policy</span>
      </CardHeader>
      <CardBody>
        <p className="mb-2 text-xs text-ink-muted">
          Denied tool ids - any Tool or MCP node using one of these is blocked at run time,
          workspace-wide. Enter built-in tool ids (e.g. <code className="text-xs">http_post</code>)
          or MCP tool names, comma-separated.
        </p>
        <Label>Denied tools</Label>
        <TextInput
          placeholder="http_post, some_mcp_tool"
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
        <Button variant="secondary" size="sm" className="mt-2" disabled={save.isPending} onClick={() => save.mutate()}>
          {save.isPending ? "Saving…" : "Save policy"}
        </Button>
      </CardBody>
    </Card>
  );
}

function AuditLogPanel() {
  const logQuery = useQuery({ queryKey: ["audit-log"], queryFn: api.listAuditLog });

  return (
    <Card>
      <CardHeader>
        <span className="text-sm font-medium">Audit Log</span>
      </CardHeader>
      <CardBody className="p-0">
        {(logQuery.data ?? []).length === 0 ? (
          <p className="px-4 py-6 text-center text-sm text-ink-faint">No audited actions yet.</p>
        ) : (
          <div className="max-h-[480px] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-surface">
                <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-ink-faint">
                  <th className="px-4 py-2 font-medium">Action</th>
                  <th className="px-4 py-2 font-medium">Resource</th>
                  <th className="px-4 py-2 font-medium">Actor</th>
                  <th className="px-4 py-2 font-medium">When</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {(logQuery.data ?? []).map((entry) => (
                  <tr key={entry.id}>
                    <td className="px-4 py-2">
                      <Badge tone="neutral">{entry.action}</Badge>
                    </td>
                    <td className="px-4 py-2 font-mono text-xs text-ink-muted">
                      {entry.resource_type}:{entry.resource_id.slice(0, 8)}
                    </td>
                    <td className="px-4 py-2 text-xs text-ink-faint">{entry.actor}</td>
                    <td className="px-4 py-2 text-xs text-ink-faint">{formatRelativeTime(entry.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

export default function SettingsPage() {
  return (
    <div className="scrollbar-thin h-full overflow-y-auto p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold text-ink">Settings</h1>
        <p className="text-sm text-ink-muted">
          Workspace tool policy and the audit trail of actions taken in it. Model configuration
          lives under Models; members/roles are not implemented yet (single dev workspace).
        </p>
      </div>

      <ToolPolicyPanel />
      <AuditLogPanel />
    </div>
  );
}
