"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Code2, Copy, Download, Redo2, Rocket, Save, Undo2 } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiSnippetsModal } from "@/components/canvas/api-snippets-modal";
import { FlowCanvas } from "@/components/canvas/flow-canvas";
import { Inspector } from "@/components/canvas/inspector";
import { NodeLibrary } from "@/components/canvas/node-library";
import { RunPanel } from "@/components/canvas/run-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type ValidationIssue } from "@/lib/api-client";
import { useCanvasStore } from "@/lib/canvas-store";

export default function FlowBuilderPage() {
  const params = useParams<{ id: string }>();
  const flowId = params.id;

  const flowQuery = useQuery({ queryKey: ["flow", flowId], queryFn: () => api.getFlow(flowId) });
  const versionQuery = useQuery({
    queryKey: ["flow-version", flowId],
    queryFn: () => api.getLatestVersion(flowId),
    enabled: !!flowQuery.data,
    retry: false,
  });

  const loadFlow = useCanvasStore((s) => s.loadFlow);
  const newFlow = useCanvasStore((s) => s.newFlow);
  const dirty = useCanvasStore((s) => s.dirty);
  const markClean = useCanvasStore((s) => s.markClean);
  const toFlowSpec = useCanvasStore((s) => s.toFlowSpec);
  const duplicateSelected = useCanvasStore((s) => s.duplicateSelected);
  const selectedNodeId = useCanvasStore((s) => s.selectedNodeId);
  const undo = useCanvasStore((s) => s.undo);
  const redo = useCanvasStore((s) => s.redo);
  const canUndo = useCanvasStore((s) => s.past.length > 0);
  const canRedo = useCanvasStore((s) => s.future.length > 0);

  function handleExport() {
    const blob = new Blob([JSON.stringify(toFlowSpec(), null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(flowQuery.data?.name ?? "flow").toLowerCase().replace(/[^a-z0-9]+/g, "-")}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [issues, setIssues] = useState<ValidationIssue[]>([]);
  const [validated, setValidated] = useState(false);
  const [apiModalOpen, setApiModalOpen] = useState(false);

  useEffect(() => {
    if (!flowQuery.data) return;
    if (versionQuery.data) {
      loadFlow(flowId, flowQuery.data.name, versionQuery.data.spec);
    } else if (versionQuery.isError) {
      newFlow();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flowQuery.data, versionQuery.data, versionQuery.isError]);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "d") {
        e.preventDefault();
        if (selectedNodeId) duplicateSelected();
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        handleSave();
      }
      // Only intercept undo/redo on the canvas itself - leave it to the browser's native
      // text-field undo/redo when focus is inside an input, textarea, or select (e.g. editing
      // a node's instructions in the Inspector).
      const target = e.target as HTMLElement | null;
      const isTypingTarget =
        target?.tagName === "INPUT" || target?.tagName === "TEXTAREA" || target?.tagName === "SELECT";
      if (!isTypingTarget && (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "z") {
        e.preventDefault();
        if (e.shiftKey) redo();
        else undo();
      }
      if (!isTypingTarget && (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "y") {
        e.preventDefault();
        redo();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedNodeId]);

  async function handleValidate(): Promise<boolean> {
    const spec = toFlowSpec();
    const result = await api.validateFlow(flowId, spec);
    setIssues(result.issues);
    setValidated(true);
    return result.valid;
  }

  async function handleSave() {
    setSaving(true);
    try {
      const spec = toFlowSpec();
      await api.saveVersion(flowId, spec);
      markClean();
      await handleValidate();
    } finally {
      setSaving(false);
    }
  }

  async function handlePublish() {
    setPublishing(true);
    try {
      if (dirty) await handleSave();
      const ok = await handleValidate();
      if (ok) await api.publishFlow(flowId);
    } finally {
      setPublishing(false);
    }
  }

  const errorCount = issues.filter((i) => i.severity === "error").length;

  return (
    <div className="flex h-full flex-col">
      <header className="flex h-12 shrink-0 items-center justify-between border-b border-border bg-surface px-4">
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-ink">{flowQuery.data?.name ?? "Loading…"}</span>
          {dirty ? <Badge tone="warning">unsaved</Badge> : <Badge tone="success">saved</Badge>}
          {validated &&
            (errorCount > 0 ? (
              <Badge tone="danger">
                <AlertTriangle size={11} /> {errorCount} issue{errorCount === 1 ? "" : "s"}
              </Badge>
            ) : (
              <Badge tone="success">
                <CheckCircle2 size={11} /> valid
              </Badge>
            ))}
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="ghost" disabled={!canUndo} onClick={undo} title="Undo (Ctrl+Z)">
            <Undo2 size={13} />
          </Button>
          <Button size="sm" variant="ghost" disabled={!canRedo} onClick={redo} title="Redo (Ctrl+Shift+Z)">
            <Redo2 size={13} />
          </Button>
          <div className="mx-1 h-5 w-px bg-border" />
          <Button size="sm" variant="ghost" onClick={handleValidate}>
            Validate
          </Button>
          <Button size="sm" variant="ghost" disabled={!selectedNodeId} onClick={duplicateSelected}>
            <Copy size={13} /> Duplicate
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setApiModalOpen(true)}>
            <Code2 size={13} /> API
          </Button>
          <Button size="sm" variant="ghost" onClick={handleExport} title="Download this flow as FlowSpec JSON">
            <Download size={13} /> Export
          </Button>
          <Button size="sm" variant="secondary" onClick={handleSave} disabled={saving}>
            <Save size={13} /> {saving ? "Saving…" : "Save"}
          </Button>
          <Button size="sm" variant="primary" onClick={handlePublish} disabled={publishing}>
            <Rocket size={13} /> {publishing ? "Publishing…" : "Deploy"}
          </Button>
        </div>
      </header>

      {issues.length > 0 && (
        <div className="max-h-24 shrink-0 overflow-y-auto border-b border-border bg-warning/5 px-4 py-1.5 text-xs">
          {issues.map((issue, i) => (
            <div key={i} className={issue.severity === "error" ? "text-danger" : "text-warning"}>
              {issue.message}
            </div>
          ))}
        </div>
      )}

      <div className="grid min-h-0 flex-1 grid-cols-[220px_1fr_300px] grid-rows-[1fr_260px]">
        <div className="row-span-1 border-r border-border bg-surface">
          <NodeLibrary />
        </div>
        <div className="relative row-span-1 bg-canvas">
          <FlowCanvas />
        </div>
        <div className="row-span-2 border-l border-border bg-surface">
          <Inspector />
        </div>
        <div className="col-span-2 border-t border-border bg-surface">
          <RunPanel flowId={flowId} inputFields={versionQuery.data?.spec.inputs ?? []} />
        </div>
      </div>

      <ApiSnippetsModal
        open={apiModalOpen}
        onClose={() => setApiModalOpen(false)}
        flowId={flowId}
        inputFields={versionQuery.data?.spec.inputs ?? []}
      />
    </div>
  );
}
