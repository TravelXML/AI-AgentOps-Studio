# Example flows

`make seed` loads all of these. Two groups:

## Node-type demos

One flow per node type, meant for learning the platform - minimal on purpose. See
[`docs/USER_GUIDE.md`](../docs/USER_GUIDE.md) for what each one teaches: `simple-agent`,
`llm-node`, `tool-agent`, `router-agent`, `supervisor-agent`, `human-approval-agent`,
`guardrail-agent`, `memory-agent`, `rag-agent`, `mcp-agent`.

## Customer support template pack (`business-*`)

Realistic, multi-node flows built to look like something you'd actually run - not node-type
demos. Each combines several node types the way a real support operation would.

| Flow | What it does | Nodes |
|---|---|---|
| **Support Ticket Triage** | Screens incoming messages for PII/abuse, then routes to whichever specialist team actually fits - billing, technical, account, or general. | Guardrail → 4-way Router → 4 specialist Agents |
| **Sentiment-Aware Escalation** | Detects anger/urgency via an explicit, auditable phrase list (not an opaque model call) and hands those straight to a human; everything else goes to an AI agent. | Rule Router → Human Approval / Agent |
| **Order Status Lookup** | Looks up a real order record and writes a friendly status reply from it. | MCP (`lookup_order`) → Agent |
| **Refund Policy Engine** | A real policy tier: refunds under $100 process immediately, larger ones pause for manager review - then both paths actually process the refund and confirm it. | Human Approval (conditional) → MCP (`process_refund`) → Agent |
| **Help Center Assistant** | Answers from your actual support policies/FAQ (seeded automatically), and says so honestly when something isn't covered instead of guessing. | RAG → Agent |

All five run out of the box with the free built-in mock model and the bundled demo MCP server -
nothing to configure. Swap in a real model (Models page) for real answers instead of MockLLM's
canned text, and point the MCP nodes at your real order/refund system in place of the bundled
demo one when you're ready to go from template to production.

Use these as a starting point: duplicate one, adjust the agent instructions to your actual policy,
repoint the MCP/RAG nodes at your real systems.
