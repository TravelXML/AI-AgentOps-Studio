"""Searchable catalog of model IDs to autocomplete the Models page's `model` field against.

Sourced live from OpenRouter's public model list (https://openrouter.ai/api/v1/models), which
covers OpenAI/Anthropic/Google/Meta/DeepSeek/Qwen/Mistral/etc. in one response - no per-provider
API key is needed just to browse it. Falls back to a small curated static list if the live fetch
fails (offline dev, network egress blocked), so the picker still works without internet access.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
from pydantic import BaseModel

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
_CACHE_TTL_SECONDS = 3600.0

# Known-strong open/free model families, used to rank "top performing" free models - OpenRouter's
# public list carries no quality/usage field, so this is a curated capability proxy rather than a
# generic context-length sort (which would otherwise surface huge-context but obscure or
# anonymous "stealth" preview models ahead of well-known, reliable ones).
_FAMILY_PRIORITY: tuple[tuple[str, int], ...] = (
    ("deepseek-r1", 100),
    ("deepseek", 90),
    ("llama-4", 95),
    ("llama-3.3", 85),
    ("gpt-oss", 90),
    ("qwen3", 90),
    ("qwen-2.5", 80),
    ("qwen", 70),
    ("gemini-2.5", 90),
    ("gemini-2.0", 80),
    ("gemini", 70),
    ("glm", 75),
    ("mistral", 65),
    ("grok", 80),
    ("llama-3.1", 60),
    ("llama", 50),
)

# Vendors whose free listings are deliberately anonymous/rotating preview models - not a
# reliable "top free model" recommendation even when large-context, so they're excluded from the
# top-N ranking (still findable via plain search).
_UNRANKED_VENDORS = {"stealth"}


class CatalogEntry(BaseModel):
    id: str
    name: str
    vendor: str
    context_length: int | None = None
    is_free: bool = False
    pricing_prompt: str | None = None
    pricing_completion: str | None = None


_FALLBACK_CATALOG: list[CatalogEntry] = [
    # Free - used only if the live OpenRouter fetch fails.
    CatalogEntry(
        id="deepseek/deepseek-r1:free",
        name="DeepSeek: R1 (free)",
        vendor="deepseek",
        context_length=64000,
        is_free=True,
        pricing_prompt="0",
        pricing_completion="0",
    ),
    CatalogEntry(
        id="meta-llama/llama-3.3-70b-instruct:free",
        name="Meta: Llama 3.3 70B Instruct (free)",
        vendor="meta-llama",
        context_length=131000,
        is_free=True,
        pricing_prompt="0",
        pricing_completion="0",
    ),
    CatalogEntry(
        id="qwen/qwen-2.5-72b-instruct:free",
        name="Qwen: Qwen2.5 72B Instruct (free)",
        vendor="qwen",
        context_length=32000,
        is_free=True,
        pricing_prompt="0",
        pricing_completion="0",
    ),
    CatalogEntry(
        id="google/gemini-2.0-flash-exp:free",
        name="Google: Gemini 2.0 Flash Experimental (free)",
        vendor="google",
        context_length=1048000,
        is_free=True,
        pricing_prompt="0",
        pricing_completion="0",
    ),
    CatalogEntry(
        id="mistralai/mistral-small-3.1-24b-instruct:free",
        name="Mistral: Small 3.1 24B Instruct (free)",
        vendor="mistralai",
        context_length=96000,
        is_free=True,
        pricing_prompt="0",
        pricing_completion="0",
    ),
    CatalogEntry(
        id="meta-llama/llama-3.1-8b-instruct:free",
        name="Meta: Llama 3.1 8B Instruct (free)",
        vendor="meta-llama",
        context_length=131000,
        is_free=True,
        pricing_prompt="0",
        pricing_completion="0",
    ),
    # Paid - common search targets across the major hosted providers.
    CatalogEntry(
        id="openai/gpt-4o",
        name="OpenAI: GPT-4o",
        vendor="openai",
        context_length=128000,
        pricing_prompt="0.0000025",
        pricing_completion="0.00001",
    ),
    CatalogEntry(
        id="openai/gpt-4o-mini",
        name="OpenAI: GPT-4o-mini",
        vendor="openai",
        context_length=128000,
        pricing_prompt="0.00000015",
        pricing_completion="0.0000006",
    ),
    CatalogEntry(
        id="openai/o3-mini",
        name="OpenAI: o3-mini",
        vendor="openai",
        context_length=200000,
        pricing_prompt="0.0000011",
        pricing_completion="0.0000044",
    ),
    CatalogEntry(
        id="google/gemini-2.5-pro",
        name="Google: Gemini 2.5 Pro",
        vendor="google",
        context_length=1048000,
        pricing_prompt="0.00000125",
        pricing_completion="0.00001",
    ),
    CatalogEntry(
        id="google/gemini-2.0-flash-001",
        name="Google: Gemini 2.0 Flash",
        vendor="google",
        context_length=1048000,
        pricing_prompt="0.0000001",
        pricing_completion="0.0000004",
    ),
    CatalogEntry(
        id="anthropic/claude-3.5-sonnet",
        name="Anthropic: Claude 3.5 Sonnet",
        vendor="anthropic",
        context_length=200000,
        pricing_prompt="0.000003",
        pricing_completion="0.000015",
    ),
    CatalogEntry(
        id="anthropic/claude-opus-4.1",
        name="Anthropic: Claude Opus 4.1",
        vendor="anthropic",
        context_length=200000,
        pricing_prompt="0.000015",
        pricing_completion="0.000075",
    ),
]

# Maps this app's internal `provider` field to the vendor prefix OpenRouter uses in its model
# ids, so the picker can scope a search to "models available under this provider". `None` means
# no scoping is possible/desired (openrouter itself spans every vendor).
PROVIDER_VENDOR_MAP: dict[str, str | None] = {
    "openai": "openai",
    "anthropic": "anthropic",
    "gemini": "google",
    "groq": "groq",
    "openrouter": None,
    "nvidia_nim": "nvidia",
    "azure_openai": "openai",
    "bedrock": None,
    "ollama": None,
    "custom": None,
    "mock": None,
}

_cache: dict[str, Any] = {"entries": None, "fetched_at": 0.0}


def _is_chat_model(raw: dict[str, Any]) -> bool:
    """Excludes audio/image/video-generation models (e.g. Lyria music gen) that share OpenRouter's
    catalog with text chat models but can't serve as an agent's `complete()` provider."""
    architecture = raw.get("architecture") or {}
    output_modalities = architecture.get("output_modalities") or ["text"]
    non_text = ("audio", "image", "video")
    return "text" in output_modalities and not any(m in non_text for m in output_modalities)


def _parse_entry(raw: dict[str, Any]) -> CatalogEntry:
    model_id = raw["id"]
    vendor = model_id.split("/", 1)[0] if "/" in model_id else model_id
    pricing = raw.get("pricing") or {}
    prompt_price = pricing.get("prompt")
    completion_price = pricing.get("completion")
    is_free = model_id.endswith(":free") or (
        prompt_price in ("0", 0, "0.0") and completion_price in ("0", 0, "0.0")
    )
    return CatalogEntry(
        id=model_id,
        name=raw.get("name") or model_id,
        vendor=vendor,
        context_length=raw.get("context_length"),
        is_free=is_free,
        pricing_prompt=str(prompt_price) if prompt_price is not None else None,
        pricing_completion=str(completion_price) if completion_price is not None else None,
    )


async def get_catalog() -> list[CatalogEntry]:
    now = time.monotonic()
    if _cache["entries"] is not None and (now - _cache["fetched_at"]) < _CACHE_TTL_SECONDS:
        return _cache["entries"]

    entries: list[CatalogEntry]
    try:
        async with httpx.AsyncClient(timeout=5.0) as http_client:
            resp = await http_client.get(OPENROUTER_MODELS_URL)
            resp.raise_for_status()
            data = resp.json().get("data", [])
        entries = [_parse_entry(raw) for raw in data if _is_chat_model(raw)]
        if not entries:
            raise ValueError("OpenRouter returned an empty catalog")
    except Exception:
        entries = _FALLBACK_CATALOG

    _cache["entries"] = entries
    _cache["fetched_at"] = now
    return entries


def _strength_score(entry: CatalogEntry) -> tuple[int, int]:
    if entry.vendor in _UNRANKED_VENDORS:
        return (-1, 0)
    lowered = entry.id.lower()
    family_score = 0
    for family, score in _FAMILY_PRIORITY:
        if family in lowered:
            family_score = score
            break
    return (family_score, entry.context_length or 0)


def search_catalog(
    entries: list[CatalogEntry],
    query: str | None = None,
    vendor: str | None = None,
    free_only: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[CatalogEntry], int]:
    """Returns `(page, total)` - `total` is the count after filtering but before the
    limit/offset slice, so callers (the paginated browser) know how many pages exist."""
    results = entries
    if vendor:
        results = [e for e in results if e.vendor == vendor]
    if free_only:
        results = [e for e in results if e.is_free]
    if query:
        q = query.lower()
        results = [e for e in results if q in e.id.lower() or q in e.name.lower()]
    if free_only:
        # No relevance signal from a search term to preserve here - rank by capability proxy.
        results = sorted(results, key=_strength_score, reverse=True)
    else:
        # Stable, scannable order - otherwise pagination through the raw OpenRouter order
        # (roughly newest-first, not alphabetical) makes browsing feel random page to page.
        results = sorted(results, key=lambda e: e.id)
    total = len(results)
    return results[offset : offset + limit], total
