"""PolicyEngine (Phase 6): enforces a workspace's tool-call policy before a Tool/MCP node
actually executes. A deny-list, checked once per tool call - simple on purpose; scoping (per-flow,
per-role) is future work, not modeled here.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class PolicyViolation(RuntimeError):
    pass


@dataclass
class ToolPolicy:
    denied_tools: set[str] = field(default_factory=set)

    def check(self, tool_id: str) -> None:
        if tool_id in self.denied_tools:
            raise PolicyViolation(f"tool '{tool_id}' is denied by workspace policy")
