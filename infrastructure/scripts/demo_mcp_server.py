"""A minimal real MCP server for trying out AgentQ's MCP Servers page against something genuine
rather than a mock. Implements the same JSON-RPC 2.0 surface `agentq_runtime.McpClient` speaks
(initialize / notifications/initialized / tools/list / tools/call).

Two tools (echo, add) exist purely to demo the MCP node mechanics. Two more (lookup_order,
process_refund) back the business-template example flows (Order Status Lookup, Refund Policy
Engine) with deterministic mock data - same order_id always returns the same synthetic order, so
demos are reproducible without a real order-management system behind them.

Usage: `uv run python infrastructure/scripts/demo_mcp_server.py` (defaults to port 8100), then
register `http://localhost:8100/mcp` on the MCP Servers page.
"""

from __future__ import annotations

import json
import os

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

SESSION_ID = "demo-mcp-session"

TOOLS = [
    {
        "name": "echo",
        "description": "Echoes the given text back unchanged.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "add",
        "description": "Adds two numbers.",
        "inputSchema": {
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    },
    {
        "name": "lookup_order",
        "description": "Looks up an order's status, total, and purchase date by order id.",
        "inputSchema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    },
    {
        "name": "process_refund",
        "description": "Processes a refund for an order and returns a confirmation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "amount": {"type": "number"},
                "reason": {"type": "string"},
            },
            "required": ["order_id", "amount"],
        },
    },
]

_ORDER_STATUSES = ["processing", "shipped", "delivered"]
_ORDER_ITEMS = ["Wireless Keyboard", "Noise-Cancelling Headphones", "Standing Desk Mat", "USB-C Hub"]


def _mock_order(order_id: str) -> dict:
    """Deterministic synthetic order data - same order_id always resolves to the same order, so
    demo runs (and this project's own tests) are reproducible without a real backing store."""
    seed = sum(ord(c) for c in order_id) if order_id else 0
    return {
        "order_id": order_id,
        "status": _ORDER_STATUSES[seed % len(_ORDER_STATUSES)],
        "item": _ORDER_ITEMS[seed % len(_ORDER_ITEMS)],
        "total_usd": round(19.99 + (seed % 15) * 12.5, 2),
        "purchased_days_ago": seed % 45,
    }


def _result(req_id, result) -> JSONResponse:
    return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": result})


def _error(req_id, message: str) -> JSONResponse:
    return JSONResponse({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": message}})


async def handle_rpc(request: Request) -> JSONResponse:
    body = await request.json()
    method = body.get("method")
    req_id = body.get("id")

    if method == "initialize":
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "agentq-demo-mcp", "version": "0.1.0"},
                },
            },
            headers={"Mcp-Session-Id": SESSION_ID},
        )

    if method == "notifications/initialized":
        return JSONResponse({}, status_code=202)

    if method == "tools/list":
        return _result(req_id, {"tools": TOOLS})

    if method == "tools/call":
        params = body.get("params", {})
        name = params.get("name")
        args = params.get("arguments", {})
        if name == "echo":
            content = [{"type": "text", "text": str(args.get("text", ""))}]
        elif name == "add":
            content = [{"type": "text", "text": str(args.get("a", 0) + args.get("b", 0))}]
        elif name == "lookup_order":
            content = [{"type": "text", "text": json.dumps(_mock_order(str(args.get("order_id", ""))))}]
        elif name == "process_refund":
            order_id = str(args.get("order_id", ""))
            content = [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "order_id": order_id,
                            "refund_id": f"RF-{sum(ord(c) for c in order_id) % 100000:05d}",
                            "amount_usd": args.get("amount", 0),
                            "reason": args.get("reason", ""),
                            "status": "processed",
                        }
                    ),
                }
            ]
        else:
            return _result(
                req_id, {"isError": True, "content": [{"type": "text", "text": f"unknown tool '{name}'"}]}
            )
        return _result(req_id, {"content": content, "isError": False})

    return _error(req_id, f"unknown method '{method}'")


app = Starlette(routes=[Route("/mcp", handle_rpc, methods=["POST"])])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8100"))
    print(f"Demo MCP server on http://localhost:{port}/mcp - tools: echo, add, lookup_order, process_refund")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
