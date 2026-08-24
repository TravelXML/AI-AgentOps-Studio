"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Plus, Upload } from "lucide-react";
import { useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { TextArea, TextInput } from "@/components/ui/field";
import { api, ApiError, type KnowledgeBase } from "@/lib/api-client";
import { formatRelativeTime } from "@/lib/utils";

function statusTone(status: string) {
  if (status === "ready") return "success" as const;
  if (status === "failed") return "danger" as const;
  return "warning" as const;
}

function DocumentsPanel({ kb }: { kb: KnowledgeBase }) {
  const queryClient = useQueryClient();
  const docsQuery = useQuery({ queryKey: ["documents", kb.id], queryFn: () => api.listDocuments(kb.id) });
  const [name, setName] = useState("");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const ingest = useMutation({
    mutationFn: () => api.ingestDocument(kb.id, { name: name || file?.name || "untitled", text, file: file ?? undefined }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", kb.id] });
      setName("");
      setText("");
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Upload failed."),
  });

  return (
    <div className="border-t border-border p-4">
      <div className="mb-3 grid grid-cols-1 gap-2 sm:grid-cols-[1fr_auto]">
        <TextInput placeholder="Document name" value={name} onChange={(e) => setName(e.target.value)} />
        <div className="flex items-center gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt,.md,.pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="max-w-[220px] text-xs text-ink-muted file:mr-2 file:rounded-md file:border-0 file:bg-surface-raised file:px-2 file:py-1 file:text-xs"
          />
        </div>
      </div>
      <TextArea
        rows={2}
        placeholder="…or paste text directly (used if no file is selected)"
        value={text}
        onChange={(e) => setText(e.target.value)}
        className="mb-2"
      />
      {error && <div className="mb-2 text-xs text-danger">{error}</div>}
      <Button
        variant="secondary"
        size="sm"
        disabled={(!text && !file) || ingest.isPending}
        onClick={() => {
          setError(null);
          ingest.mutate();
        }}
      >
        <Upload size={12} /> {ingest.isPending ? "Ingesting…" : "Add document"}
      </Button>

      <div className="mt-4 space-y-1.5">
        {(docsQuery.data ?? []).length === 0 ? (
          <p className="text-xs text-ink-faint">No documents yet.</p>
        ) : (
          (docsQuery.data ?? []).map((doc) => (
            <div key={doc.id} className="flex items-center justify-between rounded-md border border-border px-2.5 py-1.5 text-sm">
              <span className="flex min-w-0 items-center gap-1.5 truncate">
                <FileText size={12} className="shrink-0 text-ink-faint" />
                {doc.name}
              </span>
              <span className="flex shrink-0 items-center gap-2 text-xs">
                {doc.status === "ready" && <span className="text-ink-faint">{doc.chunk_count} chunks</span>}
                {doc.status === "failed" && doc.error && (
                  <span className="max-w-[220px] truncate text-danger" title={doc.error}>
                    {doc.error}
                  </span>
                )}
                <Badge tone={statusTone(doc.status)}>{doc.status}</Badge>
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default function KnowledgePage() {
  const queryClient = useQueryClient();
  const kbQuery = useQuery({ queryKey: ["knowledge-bases"], queryFn: api.listKnowledgeBases });
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  const createKb = useMutation({
    mutationFn: (n: string) => api.createKnowledgeBase({ name: n }),
    onSuccess: (kb) => {
      queryClient.invalidateQueries({ queryKey: ["knowledge-bases"] });
      setCreating(false);
      setName("");
      setExpanded(kb.id);
    },
  });

  return (
    <div className="scrollbar-thin h-full overflow-y-auto p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-ink">Knowledge</h1>
          <p className="text-sm text-ink-muted">
            Document ingestion + pgvector retrieval for RAG nodes. Upload text, markdown, or PDF -
            chunks are embedded and stored automatically.
          </p>
        </div>
        {!creating ? (
          <Button variant="primary" onClick={() => setCreating(true)}>
            <Plus size={14} /> New Knowledge Base
          </Button>
        ) : (
          <div className="flex items-center gap-2">
            <TextInput
              autoFocus
              placeholder="Knowledge base name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && name && createKb.mutate(name)}
              className="w-56"
            />
            <Button variant="primary" disabled={!name || createKb.isPending} onClick={() => createKb.mutate(name)}>
              Create
            </Button>
            <Button variant="ghost" onClick={() => setCreating(false)}>
              Cancel
            </Button>
          </div>
        )}
      </div>

      {(kbQuery.data ?? []).length === 0 ? (
        <Card>
          <CardBody className="py-10 text-center text-sm text-ink-faint">
            No knowledge bases yet - create one, then reference its id from a RAG node&rsquo;s config.
          </CardBody>
        </Card>
      ) : (
        <div className="space-y-3">
          {(kbQuery.data ?? []).map((kb) => (
            <Card key={kb.id}>
              <CardHeader
                className="flex cursor-pointer items-center justify-between"
                onClick={() => setExpanded(expanded === kb.id ? null : kb.id)}
              >
                <div>
                  <span className="text-sm font-medium">{kb.name}</span>
                  {kb.description && <span className="ml-2 text-xs text-ink-faint">{kb.description}</span>}
                </div>
                <div className="flex items-center gap-3">
                  <code className="text-[11px] text-ink-faint">{kb.id}</code>
                  <span className="text-xs text-ink-faint">{formatRelativeTime(kb.created_at)}</span>
                </div>
              </CardHeader>
              {expanded === kb.id && <DocumentsPanel kb={kb} />}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
