"use client";

import { Check, Copy } from "lucide-react";
import { useState } from "react";

import { Modal } from "@/components/ui/modal";
import { API_URL } from "@/lib/api-client";
import type { InputField } from "@/lib/flowspec";
import { cn } from "@/lib/utils";

type Lang = "curl" | "python" | "javascript";

function sampleInputs(fields: InputField[]): Record<string, unknown> {
  if (fields.length === 0) return { message: "Hello!" };
  const out: Record<string, unknown> = {};
  for (const f of fields) {
    out[f.name] = f.type === "number" ? 0 : f.type === "boolean" ? true : f.type === "json" ? {} : "Hello!";
  }
  return out;
}

function buildSnippet(lang: Lang, flowId: string, inputs: Record<string, unknown>): string {
  const url = `${API_URL}/api/v1/flows/${flowId}/runs`;
  const body = JSON.stringify({ inputs }, null, 2);

  if (lang === "curl") {
    const inline = JSON.stringify({ inputs });
    return [
      "# -N streams the response as it arrives, instead of buffering it all first",
      `curl -N -X POST "${url}" \\`,
      `  -H "Content-Type: application/json" \\`,
      `  -d '${inline}'`,
    ].join("\n");
  }

  if (lang === "python") {
    return [
      "import httpx",
      "",
      "# Requires: pip install httpx",
      `with httpx.stream(`,
      `    "POST",`,
      `    "${url}",`,
      `    json=${body.replace(/^/gm, "    ").trimStart()},`,
      `) as response:`,
      `    for line in response.iter_lines():`,
      `        if line.startswith("data: "):`,
      `            print(line.removeprefix("data: "))`,
    ].join("\n");
  }

  return [
    `const response = await fetch("${url}", {`,
    `  method: "POST",`,
    `  headers: { "Content-Type": "application/json" },`,
    `  body: JSON.stringify(${body.replace(/^/gm, "  ").trimStart()}),`,
    `});`,
    ``,
    `// Response is Server-Sent Events (one JSON run event per "data: " line)`,
    `const reader = response.body.getReader();`,
    `const decoder = new TextDecoder();`,
    `let buffer = "";`,
    `while (true) {`,
    `  const { done, value } = await reader.read();`,
    `  if (done) break;`,
    `  buffer += decoder.decode(value, { stream: true });`,
    `  const parts = buffer.split("\\n\\n");`,
    `  buffer = parts.pop() ?? "";`,
    `  for (const part of parts) {`,
    `    const line = part.split("\\n").find((l) => l.startsWith("data: "));`,
    `    if (line) console.log(JSON.parse(line.slice(6)));`,
    `  }`,
    `}`,
  ].join("\n");
}

function CodeBlock({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="relative">
      <pre className="scrollbar-thin overflow-x-auto rounded-md border border-border bg-surface-raised p-3 font-mono text-xs leading-relaxed text-ink">
        {code}
      </pre>
      <button
        onClick={() => {
          navigator.clipboard.writeText(code);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        }}
        className="absolute right-2 top-2 flex items-center gap-1 rounded-md border border-border bg-surface px-2 py-1 text-[11px] text-ink-muted transition-colors hover:border-accent/50 hover:text-accent"
      >
        {copied ? <Check size={12} className="text-success" /> : <Copy size={12} />}
        {copied ? "Copied" : "Copy"}
      </button>
    </div>
  );
}

export function ApiSnippetsModal({
  open,
  onClose,
  flowId,
  inputFields,
}: {
  open: boolean;
  onClose: () => void;
  flowId: string;
  inputFields: InputField[];
}) {
  const [lang, setLang] = useState<Lang>("curl");
  const inputs = sampleInputs(inputFields);

  return (
    <Modal open={open} onClose={onClose} title="API access">
      <p className="mb-3 text-xs text-ink-muted">
        Call this flow the same way the app does - <code className="text-xs">POST /flows/{"{id}"}/runs</code>,
        streamed as Server-Sent Events. Swap the sample field{inputFields.length > 1 ? "s" : ""} for real
        values.
      </p>
      <div className="mb-3 flex gap-1 rounded-md border border-border bg-surface-raised p-1">
        {(["curl", "python", "javascript"] as Lang[]).map((l) => (
          <button
            key={l}
            onClick={() => setLang(l)}
            className={cn(
              "flex-1 rounded px-2 py-1 text-xs font-medium capitalize transition-colors",
              lang === l ? "bg-accent text-accent-ink" : "text-ink-muted hover:text-ink"
            )}
          >
            {l}
          </button>
        ))}
      </div>
      <CodeBlock code={buildSnippet(lang, flowId, inputs)} />
    </Modal>
  );
}
