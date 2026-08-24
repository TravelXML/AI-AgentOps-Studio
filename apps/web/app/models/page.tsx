"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bot,
  Boxes,
  Cloud,
  Cpu,
  Gem,
  HardDrive,
  type LucideIcon,
  Route,
  Sparkles,
  Wrench,
  Zap,
} from "lucide-react";
import { useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { FieldGroup, Label, Select, TextInput } from "@/components/ui/field";
import { ModelCatalogBrowser } from "@/components/ui/model-catalog-browser";
import { ModelCombobox } from "@/components/ui/model-combobox";
import { api, type CatalogModel } from "@/lib/api-client";

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "")
    .slice(0, 40);
}

interface ProviderMeta {
  id: string;
  name: string;
  tagline: string;
  icon: LucideIcon;
  needsKey: boolean;
}

const PROVIDER_META: ProviderMeta[] = [
  { id: "openrouter", name: "OpenRouter", tagline: "400+ models on one key - free-tier models included", icon: Route, needsKey: true },
  { id: "openai", name: "OpenAI", tagline: "GPT-4o, o3, and more", icon: Sparkles, needsKey: true },
  { id: "anthropic", name: "Anthropic", tagline: "Claude models", icon: Bot, needsKey: true },
  { id: "gemini", name: "Gemini", tagline: "Google's Gemini models", icon: Gem, needsKey: true },
  { id: "groq", name: "Groq", tagline: "Very fast inference for open models", icon: Zap, needsKey: true },
  { id: "ollama", name: "Ollama", tagline: "Run models locally - no API key, no internet", icon: HardDrive, needsKey: false },
  { id: "azure_openai", name: "Azure OpenAI", tagline: "OpenAI models via your Azure deployment", icon: Cloud, needsKey: true },
  { id: "bedrock", name: "Amazon Bedrock", tagline: "AWS-hosted foundation models", icon: Boxes, needsKey: true },
  { id: "nvidia_nim", name: "NVIDIA NIM", tagline: "NVIDIA-hosted inference microservices", icon: Cpu, needsKey: true },
  { id: "custom", name: "Custom endpoint", tagline: "Any OpenAI-compatible API", icon: Wrench, needsKey: false },
];

const PROVIDER_BY_ID = new Map(PROVIDER_META.map((p) => [p.id, p]));

function ProviderCard({ provider, onClick }: { provider: ProviderMeta; onClick: () => void }) {
  const Icon = provider.icon;
  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex flex-col items-start gap-2 rounded-lg border border-border bg-surface p-3 text-left transition-[transform,box-shadow,border-color] duration-150 ease-out hover:-translate-y-0.5 hover:border-accent/50 hover:shadow-md active:translate-y-0 active:scale-[0.98]"
    >
      <span className="flex h-8 w-8 items-center justify-center rounded-md bg-accent/10 text-accent transition-transform duration-150 group-hover:scale-110">
        <Icon size={16} />
      </span>
      <span>
        <div className="text-sm font-medium text-ink">{provider.name}</div>
        <div className="text-[11px] leading-snug text-ink-faint">{provider.tagline}</div>
      </span>
    </button>
  );
}

export default function ModelsPage() {
  const queryClient = useQueryClient();
  const modelsQuery = useQuery({ queryKey: ["models"], queryFn: api.listModels });
  const [form, setForm] = useState({ model_key: "", provider: "ollama", model: "", base_url: "", api_key: "" });
  const [showForm, setShowForm] = useState(false);
  const [showBrowser, setShowBrowser] = useState(false);
  const formRef = useRef<HTMLDivElement>(null);
  const apiKeyRef = useRef<HTMLInputElement>(null);

  function pickModel(catalogModel: CatalogModel) {
    setForm((f) => ({
      ...f,
      model: catalogModel.id,
      model_key: f.model_key || slugify(catalogModel.name),
    }));
    apiKeyRef.current?.focus();
  }

  const createModel = useMutation({
    mutationFn: () =>
      api.createModel({
        model_key: form.model_key,
        provider: form.provider,
        model: form.model,
        base_url: form.base_url || null,
        api_key: form.api_key || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["models"] });
      setShowForm(false);
      setForm({ model_key: "", provider: "ollama", model: "", base_url: "", api_key: "" });
    },
  });

  const openFormFor = (providerId: string) => {
    setForm((f) => ({ ...f, provider: providerId }));
    setShowForm(true);
    setShowBrowser(false);
    requestAnimationFrame(() => formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
  };

  const selectedProvider = PROVIDER_BY_ID.get(form.provider);

  return (
    <div className="scrollbar-thin h-full overflow-y-auto p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold text-ink">Models</h1>
        <p className="text-sm text-ink-muted">
          Connect a model provider, then reference it by key from any Agent, LLM, Router, or
          Supervisor node. The app runs with none of these connected -{" "}
          <code className="text-xs">default</code> resolves to a free built-in mock model until you
          add one.
        </p>
      </div>

      <div className="mb-6">
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-faint">
          Add a connector
        </h2>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
          {PROVIDER_META.map((p) => (
            <ProviderCard key={p.id} provider={p} onClick={() => openFormFor(p.id)} />
          ))}
        </div>
      </div>

      {showForm && (
        <div ref={formRef}>
          <Card className="mb-6">
            <CardHeader className="flex items-center gap-2">
              {selectedProvider && (
                <span className="flex h-6 w-6 items-center justify-center rounded-md bg-accent/10 text-accent">
                  <selectedProvider.icon size={13} />
                </span>
              )}
              <span className="text-sm font-medium">Connect {selectedProvider?.name ?? "a model"}</span>
            </CardHeader>
            <CardBody>
              <FieldGroup>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>Key (referenced by agents)</Label>
                    <TextInput
                      placeholder="fast"
                      value={form.model_key}
                      onChange={(e) => setForm({ ...form, model_key: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label>Provider</Label>
                    <Select value={form.provider} onChange={(e) => setForm({ ...form, provider: e.target.value })}>
                      {PROVIDER_META.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name}
                        </option>
                      ))}
                    </Select>
                  </div>
                </div>
                <div>
                  <Label>Model (LiteLLM identifier)</Label>
                  <ModelCombobox
                    provider={form.provider}
                    value={form.model}
                    onChange={(model, catalogModel) =>
                      setForm((f) => ({
                        ...f,
                        model,
                        model_key: f.model_key || (catalogModel ? slugify(catalogModel.name) : f.model_key),
                      }))
                    }
                  />
                  <div className="mt-1 flex items-center justify-between">
                    <p className="text-[11px] text-ink-faint">
                      Search pulls live from OpenRouter&apos;s catalog (covers OpenAI, Gemini, Anthropic,
                      and free-tier models) - or type any LiteLLM-style identifier directly.
                    </p>
                    <button
                      type="button"
                      onClick={() => setShowBrowser((v) => !v)}
                      className="shrink-0 whitespace-nowrap text-[11px] font-medium text-accent hover:underline"
                    >
                      {showBrowser ? "Hide" : "Browse all models"}
                    </button>
                  </div>
                  {showBrowser && (
                    <div className="mt-2">
                      <ModelCatalogBrowser
                        provider={form.provider}
                        selectedModelId={form.model}
                        onSelect={pickModel}
                      />
                    </div>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>Base URL {selectedProvider?.needsKey === false ? "" : "(optional)"}</Label>
                    <TextInput
                      placeholder={form.provider === "ollama" ? "http://localhost:11434" : "https://..."}
                      value={form.base_url}
                      onChange={(e) => setForm({ ...form, base_url: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label>
                      API key {selectedProvider?.needsKey === false ? "(optional)" : ""} - encrypted at rest
                    </Label>
                    <TextInput
                      ref={apiKeyRef}
                      type="password"
                      value={form.api_key}
                      onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                    />
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="primary"
                    disabled={!form.model_key || !form.model || createModel.isPending}
                    onClick={() => createModel.mutate()}
                  >
                    {createModel.isPending ? "Saving…" : "Save connector"}
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
          Configured models
        </h2>
        <Card>
          <CardBody className="p-0">
            {(modelsQuery.data ?? []).length === 0 ? (
              <p className="px-4 py-10 text-center text-sm text-ink-faint">
                No models configured - agents use <code>default</code> (the free built-in mock model)
              </p>
            ) : (
              <div className="divide-y divide-border">
                {(modelsQuery.data ?? []).map((m) => {
                  const meta = PROVIDER_BY_ID.get(m.provider);
                  const Icon = meta?.icon ?? Wrench;
                  return (
                    <div key={m.id} className="flex items-center gap-3 px-4 py-3">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-accent/10 text-accent">
                        <Icon size={14} />
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-sm font-medium text-ink">{m.model_key}</div>
                        <div className="truncate text-xs text-ink-faint">
                          {meta?.name ?? m.provider} · {m.model}
                        </div>
                      </div>
                      <Badge tone={m.has_secret ? "success" : "neutral"}>
                        {m.has_secret ? "credential configured" : "no credential"}
                      </Badge>
                    </div>
                  );
                })}
              </div>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
