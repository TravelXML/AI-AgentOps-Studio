"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";

import { api, type CatalogModel } from "@/lib/api-client";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 24;

function formatPrice(model: CatalogModel): string {
  if (model.is_free) return "free";
  if (!model.pricing_prompt) return "";
  const perMillion = Number(model.pricing_prompt) * 1_000_000;
  if (Number.isNaN(perMillion)) return "";
  return `$${perMillion < 1 ? perMillion.toFixed(2) : perMillion.toFixed(1)}/M`;
}

/** Pages through the full model catalog for a provider (hundreds of entries for OpenRouter) -
 * click a card to fill the model field, then the caller just needs an API key to configure it. */
export function ModelCatalogBrowser({
  provider,
  selectedModelId,
  onSelect,
}: {
  provider: string;
  selectedModelId?: string;
  onSelect: (model: CatalogModel) => void;
}) {
  const [page, setPage] = useState(0);
  const [query, setQuery] = useState("");
  const [freeOnly, setFreeOnly] = useState(false);

  const browseQuery = useQuery({
    queryKey: ["model-catalog-browse", provider, page, query, freeOnly],
    queryFn: () =>
      api.browseModelCatalog({
        provider,
        q: query || undefined,
        free_only: freeOnly,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
    staleTime: 60 * 1000,
  });

  const total = browseQuery.data?.total ?? 0;
  const items = browseQuery.data?.items ?? [];
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="rounded-md border border-border">
      <div className="flex items-center gap-2 border-b border-border bg-surface-raised px-2.5 py-2">
        <input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setPage(0);
          }}
          placeholder="Filter…"
          className="min-w-0 flex-1 rounded border border-border bg-surface px-2 py-1 text-xs placeholder:text-ink-faint focus:outline-none focus:ring-1 focus:ring-accent/40"
        />
        <label className="flex shrink-0 items-center gap-1.5 text-xs text-ink-muted">
          <input
            type="checkbox"
            checked={freeOnly}
            onChange={(e) => {
              setFreeOnly(e.target.checked);
              setPage(0);
            }}
            className="accent-accent"
          />
          Free only
        </label>
      </div>

      <div className="scrollbar-thin grid max-h-64 grid-cols-2 gap-1.5 overflow-y-auto p-2 sm:grid-cols-3">
        {browseQuery.isFetching && items.length === 0 ? (
          <div className="col-span-full py-6 text-center text-xs text-ink-faint">Loading…</div>
        ) : items.length === 0 ? (
          <div className="col-span-full py-6 text-center text-xs text-ink-faint">No matches.</div>
        ) : (
          items.map((m) => (
            <button
              key={m.id}
              type="button"
              onClick={() => onSelect(m)}
              className={cn(
                "flex flex-col items-start gap-0.5 rounded-md border px-2 py-1.5 text-left transition-colors duration-100",
                m.id === selectedModelId
                  ? "border-accent bg-accent/10"
                  : "border-transparent hover:border-border hover:bg-surface-raised"
              )}
            >
              <span className="w-full truncate text-xs font-medium text-ink">{m.name}</span>
              <span className="flex w-full items-center justify-between gap-1">
                <span className="truncate text-[10px] text-ink-faint">{m.vendor}</span>
                <span className={cn("shrink-0 text-[10px] font-medium", m.is_free ? "text-success" : "text-ink-faint")}>
                  {formatPrice(m)}
                </span>
              </span>
            </button>
          ))
        )}
      </div>

      <div className="flex items-center justify-between border-t border-border px-2.5 py-1.5 text-[11px] text-ink-faint">
        <span>
          {total > 0 ? `${total.toLocaleString()} models` : " "}
        </span>
        <div className="flex items-center gap-1">
          <button
            type="button"
            disabled={page === 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            className="rounded p-0.5 transition-colors hover:bg-surface-raised disabled:pointer-events-none disabled:opacity-30"
          >
            <ChevronLeft size={14} />
          </button>
          <span>
            Page {page + 1} of {pageCount}
          </span>
          <button
            type="button"
            disabled={page + 1 >= pageCount}
            onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
            className="rounded p-0.5 transition-colors hover:bg-surface-raised disabled:pointer-events-none disabled:opacity-30"
          >
            <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
