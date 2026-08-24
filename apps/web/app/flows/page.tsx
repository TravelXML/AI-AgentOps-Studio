"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Sparkles, Upload } from "lucide-react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Label, Select, TextArea, TextInput } from "@/components/ui/field";
import { api, ApiError } from "@/lib/api-client";
import { FlowSpec } from "@/lib/flowspec";
import { formatRelativeTime } from "@/lib/utils";

function GenerateWithAiPanel({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const modelsQuery = useQuery({ queryKey: ["models"], queryFn: api.listModels });
  const [description, setDescription] = useState("");
  const [model, setModel] = useState("default");
  const [error, setError] = useState<string | null>(null);

  const generate = useMutation({
    mutationFn: async () => {
      const { spec } = await api.generateFlow({ description, model });
      return api.createFlow({ name: spec.name, description: spec.description, spec });
    },
    onSuccess: (flow) => {
      queryClient.invalidateQueries({ queryKey: ["flows"] });
      router.push(`/flows/${flow.id}`);
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Generation failed.");
    },
  });

  return (
    <Card className="mb-6">
      <CardHeader className="flex items-center gap-2">
        <Sparkles size={14} className="text-accent" />
        <span className="text-sm font-medium">Generate a flow with AI</span>
      </CardHeader>
      <CardBody>
        <div className="space-y-3">
          <div>
            <Label>Describe the agent workflow you want</Label>
            <TextArea
              autoFocus
              rows={3}
              placeholder="e.g. A support agent that answers billing questions directly and routes everything else to a human for approval before responding."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div className="max-w-xs">
            <Label>Model</Label>
            <Select value={model} onChange={(e) => setModel(e.target.value)}>
              <option value="default">default (MockLLM - will not produce a valid flow)</option>
              {(modelsQuery.data ?? []).map((m) => (
                <option key={m.id} value={m.model_key}>
                  {m.model_key} ({m.provider})
                </option>
              ))}
            </Select>
            <p className="mt-1 text-[11px] text-ink-faint">
              Generation needs a real model that can follow structured-output instructions - add one
              under <Link href="/models" className="text-accent hover:underline">Models</Link> first.
            </p>
          </div>
          {error && (
            <div className="rounded-md border border-danger/30 bg-danger/5 px-3 py-2 text-xs text-danger">
              {error}
            </div>
          )}
          <div className="flex items-center gap-2">
            <Button
              variant="primary"
              disabled={!description.trim() || generate.isPending}
              onClick={() => {
                setError(null);
                generate.mutate();
              }}
            >
              {generate.isPending ? "Generating…" : "Generate"}
            </Button>
            <Button variant="ghost" onClick={onClose}>
              Cancel
            </Button>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

export default function FlowsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const flowsQuery = useQuery({ queryKey: ["flows"], queryFn: api.listFlows });
  const [creating, setCreating] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [name, setName] = useState("");
  const [importError, setImportError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const createFlow = useMutation({
    mutationFn: (n: string) => api.createFlow({ name: n }),
    onSuccess: (flow) => {
      queryClient.invalidateQueries({ queryKey: ["flows"] });
      router.push(`/flows/${flow.id}`);
    },
  });

  const importFlow = useMutation({
    mutationFn: (spec: FlowSpec) => api.createFlow({ name: spec.name, description: spec.description, spec }),
    onSuccess: (flow) => {
      queryClient.invalidateQueries({ queryKey: ["flows"] });
      router.push(`/flows/${flow.id}`);
    },
    onError: (err) => setImportError(err instanceof ApiError ? err.message : "Import failed."),
  });

  async function handleImportFile(file: File) {
    setImportError(null);
    let raw: unknown;
    try {
      raw = JSON.parse(await file.text());
    } catch {
      setImportError("That file isn't valid JSON.");
      return;
    }
    const parsed = FlowSpec.safeParse(raw);
    if (!parsed.success) {
      setImportError(`Not a valid FlowSpec file: ${parsed.error.issues[0]?.message ?? "schema mismatch"}.`);
      return;
    }
    importFlow.mutate(parsed.data);
  }

  return (
    <div className="scrollbar-thin h-full overflow-y-auto p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-ink">Flows</h1>
          <p className="text-sm text-ink-muted">Visual agent workflows in this project.</p>
        </div>
        {!creating && !generating ? (
          <div className="flex items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept="application/json,.json"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleImportFile(file);
                e.target.value = "";
              }}
            />
            <Button variant="secondary" onClick={() => fileInputRef.current?.click()} disabled={importFlow.isPending}>
              <Upload size={14} /> {importFlow.isPending ? "Importing…" : "Import"}
            </Button>
            <Button variant="secondary" onClick={() => setGenerating(true)}>
              <Sparkles size={14} /> Generate with AI
            </Button>
            <Button variant="primary" onClick={() => setCreating(true)}>
              <Plus size={14} /> New Flow
            </Button>
          </div>
        ) : creating ? (
          <div className="flex items-center gap-2">
            <TextInput
              autoFocus
              placeholder="Flow name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && name && createFlow.mutate(name)}
              className="w-56"
            />
            <Button variant="primary" disabled={!name || createFlow.isPending} onClick={() => createFlow.mutate(name)}>
              Create
            </Button>
            <Button variant="ghost" onClick={() => setCreating(false)}>
              Cancel
            </Button>
          </div>
        ) : null}
      </div>

      {importError && (
        <div className="mb-4 rounded-md border border-danger/30 bg-danger/5 px-3 py-2 text-xs text-danger">
          {importError}
        </div>
      )}

      {generating && <GenerateWithAiPanel onClose={() => setGenerating(false)} />}

      {flowsQuery.isLoading && <p className="text-sm text-ink-faint">Loading…</p>}

      {flowsQuery.data && flowsQuery.data.length === 0 && (
        <Card>
          <CardBody className="py-10 text-center text-sm text-ink-faint">
            No flows yet. Create one, generate one with AI, or click Import to load a FlowSpec
            JSON file - including any of the examples under the repository&rsquo;s{" "}
            <code className="text-xs">examples/</code> directory.
          </CardBody>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {(flowsQuery.data ?? []).map((flow) => (
          <Link key={flow.id} href={`/flows/${flow.id}`} className="block">
            <Card className="h-full cursor-pointer transition-[transform,box-shadow,border-color] duration-150 ease-out hover:-translate-y-0.5 hover:border-accent/50 hover:shadow-md active:translate-y-0 active:scale-[0.99]">
              <CardBody>
                <div className="mb-2 flex items-center justify-between">
                  <span className="truncate text-sm font-medium text-ink">{flow.name}</span>
                  <Badge tone={flow.status === "published" ? "success" : "neutral"}>{flow.status}</Badge>
                </div>
                <p className="mb-3 line-clamp-2 text-xs text-ink-muted">{flow.description || "No description"}</p>
                <div className="flex items-center justify-between text-[11px] text-ink-faint">
                  <span>v{flow.latest_version ?? "-"}</span>
                  <span>Updated {formatRelativeTime(flow.updated_at)}</span>
                </div>
              </CardBody>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
