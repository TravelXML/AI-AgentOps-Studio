"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Plug, Plus, RefreshCw, Wrench } from "lucide-react";
import { useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { FieldGroup, Label, TextInput } from "@/components/ui/field";
import { api, ApiError, type McpServerInfo } from "@/lib/api-client";

function statusTone(status: string) {
  if (status === "connected") return "success" as const;
  if (status === "error") return "danger" as const;
  return "neutral" as const;
}

function ServerCard({ server }: { server: McpServerInfo }) {
  const queryClient = useQueryClient();
  const refresh = useMutation({
    mutationFn: () => api.refreshMcpServer(server.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["mcp-servers"] }),
  });

  return (
    <Card>
      <CardHeader className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">{server.name}</span>
            <Badge tone={statusTone(server.status)}>{server.status}</Badge>
          </div>
          <div className="mt-0.5 text-xs text-ink-faint">{server.url}</div>
        </div>
        <div className="flex items-center gap-2">
          <code className="text-[11px] text-ink-faint">{server.id}</code>
          <Button variant="ghost" size="sm" disabled={refresh.isPending} onClick={() => refresh.mutate()}>
            <RefreshCw size={12} className={refresh.isPending ? "animate-spin" : ""} /> Refresh
          </Button>
        </div>
      </CardHeader>
      <CardBody>
        {server.status === "error" && server.last_error && (
          <p className="mb-2 text-xs text-danger">{server.last_error}</p>
        )}
        {server.tools.length === 0 ? (
          <p className="text-xs text-ink-faint">No tools discovered.</p>
        ) : (
          <div className="space-y-1.5">
            {server.tools.map((t) => (
              <div key={t.name} className="flex items-start gap-2 rounded-md border border-border px-2.5 py-1.5">
                <Wrench size={12} className="mt-0.5 shrink-0 text-accent" />
                <div className="min-w-0">
                  <div className="font-mono text-xs text-ink">{t.name}</div>
                  {t.description && <div className="text-xs text-ink-faint">{t.description}</div>}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardBody>
    </Card>
  );
}

export default function McpServersPage() {
  const queryClient = useQueryClient();
  const serversQuery = useQuery({ queryKey: ["mcp-servers"], queryFn: api.listMcpServers });
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", url: "", api_key: "" });
  const [error, setError] = useState<string | null>(null);
  const formRef = useRef<HTMLDivElement>(null);

  const register = useMutation({
    mutationFn: () =>
      api.registerMcpServer({ name: form.name, url: form.url, api_key: form.api_key || null }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mcp-servers"] });
      setShowForm(false);
      setForm({ name: "", url: "", api_key: "" });
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Registration failed."),
  });

  const openFormFor = (prefill: { name: string; url: string }) => {
    setError(null);
    setForm({ ...prefill, api_key: "" });
    setShowForm(true);
    requestAnimationFrame(() => formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
  };

  const demoAlreadyRegistered = (serversQuery.data ?? []).some((s) => s.name === "demo-mcp");

  return (
    <div className="scrollbar-thin h-full overflow-y-auto p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold text-ink">MCP Servers</h1>
        <p className="text-sm text-ink-muted">
          Register an MCP server by URL - its tools are discovered over a real JSON-RPC handshake
          and become callable from an MCP node on the canvas.
        </p>
      </div>

      <div className="mb-6">
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-faint">
          Add a connector
        </h2>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <button
            type="button"
            disabled={demoAlreadyRegistered}
            onClick={() => openFormFor({ name: "demo-mcp", url: "http://demo-mcp:8100/mcp" })}
            className="group flex flex-col items-start gap-2 rounded-lg border border-border bg-surface p-3 text-left transition-[transform,box-shadow,border-color] duration-150 ease-out hover:-translate-y-0.5 hover:border-accent/50 hover:shadow-md active:translate-y-0 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-60"
          >
            <span className="flex h-8 w-8 items-center justify-center rounded-md bg-accent/10 text-accent transition-transform duration-150 group-hover:scale-110">
              {demoAlreadyRegistered ? <Check size={16} /> : <Plug size={16} />}
            </span>
            <span>
              <div className="text-sm font-medium text-ink">Demo MCP Server</div>
              <div className="text-[11px] leading-snug text-ink-faint">
                {demoAlreadyRegistered
                  ? "Already connected"
                  : "Bundled with this app (echo, add) - one click, no setup"}
              </div>
            </span>
          </button>
          <button
            type="button"
            onClick={() => openFormFor({ name: "", url: "" })}
            className="group flex flex-col items-start gap-2 rounded-lg border border-dashed border-border bg-surface p-3 text-left transition-[transform,box-shadow,border-color] duration-150 ease-out hover:-translate-y-0.5 hover:border-accent/50 hover:shadow-md active:translate-y-0 active:scale-[0.98]"
          >
            <span className="flex h-8 w-8 items-center justify-center rounded-md bg-accent/10 text-accent transition-transform duration-150 group-hover:scale-110">
              <Plus size={16} />
            </span>
            <span>
              <div className="text-sm font-medium text-ink">Custom server</div>
              <div className="text-[11px] leading-snug text-ink-faint">
                Any MCP server you have a URL for - self-hosted or a provider&apos;s hosted endpoint
              </div>
            </span>
          </button>
        </div>
        <p className="mt-2 text-[11px] text-ink-faint">
          There&apos;s no public registry of MCP servers built in yet - unlike model providers,
          there isn&apos;t one stable catalog to pull from. The demo server above is real and
          bundled with this app so the MCP node has something to try immediately; everything else
          needs a URL you already have.
        </p>
      </div>

      {showForm && (
        <div ref={formRef}>
          <Card className="mb-6">
            <CardHeader>
              <span className="text-sm font-medium">Register MCP Server</span>
            </CardHeader>
            <CardBody>
              <FieldGroup>
                <div>
                  <Label>Name</Label>
                  <TextInput
                    placeholder="demo-tools"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                  />
                </div>
                <div>
                  <Label>URL</Label>
                  <TextInput
                    placeholder="http://localhost:8100/mcp"
                    value={form.url}
                    onChange={(e) => setForm({ ...form, url: e.target.value })}
                  />
                </div>
                <div>
                  <Label>Bearer token (optional - encrypted at rest)</Label>
                  <TextInput
                    type="password"
                    value={form.api_key}
                    onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                  />
                </div>
                {error && <div className="text-xs text-danger">{error}</div>}
                <div className="flex items-center gap-2">
                  <Button
                    variant="primary"
                    disabled={!form.name || !form.url || register.isPending}
                    onClick={() => {
                      setError(null);
                      register.mutate();
                    }}
                  >
                    {register.isPending ? "Connecting…" : "Register & discover tools"}
                  </Button>
                  <Button variant="ghost" onClick={() => setShowForm(false)}>
                    Cancel
                  </Button>
                </div>
              </FieldGroup>
            </CardBody>
          </Card>
        </div>
      )}

      <div>
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-faint">
          Connected servers
        </h2>
        {(serversQuery.data ?? []).length === 0 ? (
          <Card>
            <CardBody className="py-10 text-center text-sm text-ink-faint">
              No MCP servers registered yet.
            </CardBody>
          </Card>
        ) : (
          <div className="space-y-3">
            {(serversQuery.data ?? []).map((s) => (
              <ServerCard key={s.id} server={s} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
