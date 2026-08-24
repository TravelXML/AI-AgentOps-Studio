"""Loads examples/*/flowspec.json into the local database via the running API. Two kinds of
example live here:
  - one flow per node type (Calculator Tool, Raw LLM Call, ...), for learning the platform.
  - a "customer-support" business template pack (business-*/flowspec.json) - realistic,
    multi-node flows (ticket triage, escalation, order lookup, refund policy, help-center RAG)
    meant to look like something you'd actually want to run, not just a node-type demo.

Some examples need something created before their flow makes sense, so this script does that
too: RAG flows need a knowledge base with a document in it (see KNOWLEDGE_BASES below); MCP flows
need a registered MCP server (registers the bundled demo-mcp service; skipped, not failed, if
it isn't reachable). Each such flowspec.json carries a `__SEEDED_..._ID__` placeholder in place
of the real id, substituted in after the dependency is created.

Usage: `make seed` (equivalent to `uv run python infrastructure/scripts/seed_examples.py`).
Requires the API to be reachable at AGENTQ_API_URL (default http://localhost:8000).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

API_URL = os.environ.get("AGENTQ_API_URL", "http://localhost:8000")
EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"

# Maps a flowspec.json placeholder to the (knowledge base name, document text) that backs it -
# each is created once (by name, so re-running `make seed` doesn't duplicate it) the first time a
# flow needing it is seeded.
KNOWLEDGE_BASES: dict[str, tuple[str, str]] = {
    "__SEEDED_KNOWLEDGE_BASE_ID__": (
        "AgentQ Docs",
        """AgentQ is a visual builder for AI agent workflows. A flow is made of nodes \
connected by edges: Input brings data in, Output returns the result, and everything in between \
does work on it - an Agent node calls a model with instructions and optional tools, a Router \
sends execution down one of several branches, a Supervisor delegates to sub-agents, a Tool node \
calls a function like a calculator or an HTTP request, an MCP node calls a tool on an external \
MCP server, a RAG node retrieves relevant context from a knowledge base, a Memory node persists \
conversation or semantic memory across runs, and a Guardrail node checks content for problems \
like PII or blocked keywords before letting it through.

Human approval works by pausing a run at a Human Approval node until someone clicks Approve or \
Reject on the trace page. The pause is backed by a real Postgres checkpoint, not just frontend \
state - restarting the API mid-approval does not lose the paused run.

Every run is recorded: which nodes executed, in what order, how long each step took, how many \
tokens and how much it cost, and what every intermediate output was. This is the flight recorder, \
and it's what the trace page shows for any run, including ones started for evaluations.""",
    ),
    "__SEEDED_SUPPORT_KB_ID__": (
        "Support Policies & FAQ",
        """Shipping: Standard shipping takes 5-7 business days. Express shipping (2 business \
days) is available at checkout for an additional fee. We do not ship to PO boxes.

Returns and refunds: Items can be returned within 30 days of delivery for a full refund, as \
long as they're unused and in original packaging. Refunds are processed within 5-7 business \
days of us receiving the return. Refunds of $100 or more require manager review before being \
issued; refunds under $100 are approved automatically. Shipping costs are non-refundable unless \
the return is due to our error.

Subscription cancellation: You can cancel your subscription at any time from Account Settings > \
Subscription. There is no cancellation fee. Cancelling stops future billing but does not refund \
the current billing period - you keep access until the period ends.

Warranty: Hardware products carry a 1-year manufacturer warranty covering defects, not accidental \
damage or normal wear. To file a warranty claim, contact support with your order number and a \
description of the issue.

Account security: Support will never ask for your password over chat, email, or phone. If \
someone claiming to be from our team asks for your password, it is not really us - do not share \
it, and report the message to support.""",
    ),
}


def _load_spec(example_dir: Path) -> dict | None:
    spec_path = example_dir / "flowspec.json"
    if not spec_path.exists():
        return None
    return json.loads(spec_path.read_text())


def _create_and_publish(client: httpx.Client, spec: dict) -> dict:
    payload = {"name": spec["name"], "description": spec.get("description", ""), "spec": spec}
    response = client.post("/api/v1/flows", json=payload)
    response.raise_for_status()
    flow = response.json()
    client.post(f"/api/v1/flows/{flow['id']}/publish")
    return flow


def _seed_knowledge_base(client: httpx.Client, name: str, document_text: str) -> str | None:
    existing = {kb["name"]: kb["id"] for kb in client.get("/api/v1/knowledge-bases").json()}
    if name in existing:
        return existing[name]

    kb = client.post(
        "/api/v1/knowledge-bases",
        json={"name": name, "description": f"Seeded for example flows that reference '{name}'."},
    ).json()
    doc_name = name.lower().replace(" ", "-").replace("&", "and") + ".txt"
    doc = client.post(
        f"/api/v1/knowledge-bases/{kb['id']}/documents",
        data={"name": doc_name, "text": document_text},
    ).json()
    if doc.get("status") != "ready":
        print(f"WARN  knowledge base '{name}' document did not become ready: {doc}", file=sys.stderr)
        return None
    return kb["id"]


def _seed_demo_mcp_server(client: httpx.Client) -> str | None:
    """Registers the bundled demo MCP server at the URL the *API process* can reach it at - not
    this script. The connectivity check that decides success happens API-side (inside `POST
    /api/v1/mcp-servers`) since this script and the API aren't necessarily on the same network.
    `http://demo-mcp:8100/mcp` (the compose service DNS name) is correct for the standard
    `docker compose up -d` deployment this project defaults to; if the API is instead running
    directly on the host (`make dev-api`), register the demo server manually from the MCP
    Servers page - `python infrastructure/scripts/demo_mcp_server.py` then
    `http://localhost:8100/mcp`."""
    for server in client.get("/api/v1/mcp-servers").json():
        if server["name"] == "demo-mcp":
            if server["status"] == "connected":
                return server["id"]
            refreshed = client.post(f"/api/v1/mcp-servers/{server['id']}/refresh").json()
            return refreshed["id"] if refreshed.get("status") == "connected" else None

    url = "http://demo-mcp:8100/mcp"
    server = client.post("/api/v1/mcp-servers", json={"name": "demo-mcp", "url": url}).json()
    return server["id"] if server.get("status") == "connected" else None


def main() -> int:
    client = httpx.Client(base_url=API_URL, timeout=30.0)

    try:
        client.get("/health").raise_for_status()
    except httpx.HTTPError as exc:
        print(f"API is not reachable at {API_URL}: {exc}", file=sys.stderr)
        print("Start it first: `make dev-api` or `docker compose up -d api`.", file=sys.stderr)
        return 1

    existing_flows = {f["name"] for f in client.get("/api/v1/flows").json()}
    kb_id_cache: dict[str, str] = {}
    mcp_server_id: str | None = None

    for example_dir in sorted(EXAMPLES_DIR.iterdir()):
        spec = _load_spec(example_dir)
        if spec is None:
            continue
        name = spec["name"]
        if name in existing_flows:
            print(f"skip  {name} (already exists)")
            continue

        raw = json.dumps(spec)
        kb_placeholder = next((p for p in KNOWLEDGE_BASES if p in raw), None)
        if kb_placeholder:
            if kb_placeholder not in kb_id_cache:
                kb_name, kb_text = KNOWLEDGE_BASES[kb_placeholder]
                kb_id = _seed_knowledge_base(client, kb_name, kb_text)
                if kb_id is None:
                    print(f"skip  {name} (could not seed its knowledge base)", file=sys.stderr)
                    continue
                kb_id_cache[kb_placeholder] = kb_id
            spec = json.loads(raw.replace(kb_placeholder, kb_id_cache[kb_placeholder]))
        elif "__SEEDED_MCP_SERVER_ID__" in raw:
            if mcp_server_id is None:
                mcp_server_id = _seed_demo_mcp_server(client)
            if mcp_server_id is None:
                print(
                    f"skip  {name} (demo-mcp not reachable from the API - "
                    "`docker compose up -d demo-mcp`, then re-run `make seed`; if the API runs "
                    "outside docker, register it manually from the MCP Servers page instead)",
                    file=sys.stderr,
                )
                continue
            spec = json.loads(raw.replace("__SEEDED_MCP_SERVER_ID__", mcp_server_id))

        try:
            flow = _create_and_publish(client, spec)
        except httpx.HTTPStatusError as exc:
            print(f"FAIL  {name}: {exc.response.status_code} {exc.response.text}", file=sys.stderr)
            continue
        print(f"seeded {name} ({flow['id']})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
