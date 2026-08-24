"""Operational metrics (section 48). Real counters/histograms via prometheus_client - no
fictional numbers. Exposed at GET /metrics in Prometheus text format."""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Histogram

registry = CollectorRegistry()


class Metrics:
    def __init__(self, registry: CollectorRegistry) -> None:
        self.workflow_runs_total = Counter(
            "workflow_runs_total",
            "Total workflow runs started",
            ["status"],
            registry=registry,
        )
        self.workflow_run_duration_seconds = Histogram(
            "workflow_run_duration_seconds",
            "Workflow run duration",
            registry=registry,
        )
        self.workflow_failures_total = Counter(
            "workflow_failures_total",
            "Total workflow run failures",
            registry=registry,
        )
        self.agent_node_duration_seconds = Histogram(
            "agent_node_duration_seconds",
            "Agent node execution duration",
            ["node_id"],
            registry=registry,
        )
        self.llm_requests_total = Counter(
            "llm_requests_total",
            "Total LLM requests",
            ["provider", "model"],
            registry=registry,
        )
        self.llm_tokens_total = Counter(
            "llm_tokens_total",
            "Total LLM tokens",
            ["provider", "model", "kind"],
            registry=registry,
        )
        self.llm_api_cost_total = Counter(
            "llm_api_cost_total",
            "Total estimated LLM API cost (USD)",
            ["provider", "model"],
            registry=registry,
        )
        self.tool_calls_total = Counter(
            "tool_calls_total",
            "Total tool calls",
            ["tool_id"],
            registry=registry,
        )
        self.tool_failures_total = Counter(
            "tool_failures_total",
            "Total tool call failures",
            ["tool_id"],
            registry=registry,
        )
        self.evaluation_runs_total = Counter(
            "evaluation_runs_total",
            "Total evaluation runs",
            registry=registry,
        )


metrics = Metrics(registry)
