"use client";

import { useQuery } from "@tanstack/react-query";
import { Search, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { TextInput } from "@/components/ui/field";
import { api, type CatalogModel } from "@/lib/api-client";
import { cn } from "@/lib/utils";

function formatPrice(model: CatalogModel): string {
  if (model.is_free) return "free";
  if (!model.pricing_prompt) return "";
  const perMillion = Number(model.pricing_prompt) * 1_000_000;
  if (Number.isNaN(perMillion)) return "";
  return `$${perMillion < 1 ? perMillion.toFixed(2) : perMillion.toFixed(1)}/M in`;
}

function ModelOption({ model, onSelect }: { model: CatalogModel; onSelect: (model: CatalogModel) => void }) {
  return (
    <button
      type="button"
      onMouseDown={(e) => e.preventDefault()}
      onClick={() => onSelect(model)}
      className="flex w-full items-center justify-between gap-3 rounded-md px-2.5 py-1.5 text-left text-sm transition-colors duration-100 hover:bg-accent/10 active:bg-accent/20"
    >
      <div className="min-w-0">
        <div className="truncate text-ink">{model.name}</div>
        <div className="truncate text-xs text-ink-faint">{model.id}</div>
      </div>
      <div className="flex shrink-0 items-center gap-2 text-xs">
        {model.context_length ? (
          <span className="text-ink-faint">{Math.round(model.context_length / 1000)}k ctx</span>
        ) : null}
        <span className={cn("font-medium", model.is_free ? "text-success" : "text-ink-muted")}>
          {formatPrice(model)}
        </span>
      </div>
    </button>
  );
}

/** Searchable model-id field: free-text (any value is accepted as-is) backed by a live
 * OpenRouter-sourced catalog for autocomplete, scoped to the selected provider's vendor. */
export function ModelCombobox({
  provider,
  value,
  onChange,
  placeholder,
}: {
  provider: string;
  value: string;
  onChange: (value: string, model?: CatalogModel) => void;
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const [debouncedQuery, setDebouncedQuery] = useState(value);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(value), 250);
    return () => clearTimeout(t);
  }, [value]);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const topFreeQuery = useQuery({
    queryKey: ["model-catalog-top-free", provider],
    queryFn: () => api.searchModelCatalog({ provider, free_only: true, limit: 5 }),
    staleTime: 5 * 60 * 1000,
  });

  const searchQuery = useQuery({
    queryKey: ["model-catalog-search", provider, debouncedQuery],
    queryFn: () => api.searchModelCatalog({ provider, q: debouncedQuery, limit: 20 }),
    enabled: open && debouncedQuery.length > 0,
    staleTime: 60 * 1000,
  });

  function select(model: CatalogModel) {
    onChange(model.id, model);
    setOpen(false);
  }

  const showTopFree = open && debouncedQuery.length === 0 && (topFreeQuery.data?.length ?? 0) > 0;
  const showSearchResults = open && debouncedQuery.length > 0;

  return (
    <div ref={containerRef} className="relative">
      <TextInput
        placeholder={placeholder ?? "ollama/llama3.1 or gpt-4o-mini"}
        value={value}
        onFocus={() => setOpen(true)}
        onChange={(e) => onChange(e.target.value)}
      />
      {open && (
        <div className="absolute z-20 mt-1 max-h-72 w-full overflow-y-auto rounded-md border border-border bg-surface p-1 shadow-lg">
          {showTopFree && (
            <div className="mb-1 border-b border-border pb-1">
              <div className="flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium uppercase tracking-wide text-ink-faint">
                <Sparkles size={11} /> Top free models
              </div>
              {topFreeQuery.data!.map((m) => (
                <ModelOption key={m.id} model={m} onSelect={select} />
              ))}
              <div className="px-2.5 pt-1 text-[11px] text-ink-faint">Type to search all models…</div>
            </div>
          )}
          {showSearchResults &&
            (searchQuery.isFetching && searchQuery.data === undefined ? (
              <div className="px-2.5 py-3 text-center text-xs text-ink-faint">Searching…</div>
            ) : (searchQuery.data ?? []).length === 0 ? (
              <div className="px-2.5 py-3 text-center text-xs text-ink-faint">
                No catalog matches - the typed value will still be used as-is
              </div>
            ) : (
              searchQuery.data!.map((m) => <ModelOption key={m.id} model={m} onSelect={select} />)
            ))}
          {!showTopFree && !showSearchResults && (
            <div className="flex items-center gap-1.5 px-2.5 py-3 text-xs text-ink-faint">
              <Search size={12} /> Start typing to search OpenAI, Gemini, Anthropic, and OpenRouter models…
            </div>
          )}
        </div>
      )}
    </div>
  );
}
