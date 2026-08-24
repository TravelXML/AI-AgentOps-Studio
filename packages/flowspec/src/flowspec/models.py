"""FlowSpec: the framework-neutral workflow specification.

The visual canvas persists FlowSpec, never LangGraph (or any other runtime's)
implementation details. A WorkflowCompiler turns a validated FlowSpec into a
runtime-specific executable graph. See docs/architecture/flowspec.md.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

FLOWSPEC_SCHEMA_VERSION = 1


class NodeType(StrEnum):
    INPUT = "input"
    OUTPUT = "output"
    AGENT = "agent"
    LLM = "llm"
    ROUTER = "router"
    SUPERVISOR = "supervisor"
    TOOL = "tool"
    MCP = "mcp"
    RAG = "rag"
    MEMORY = "memory"
    HUMAN_APPROVAL = "human_approval"
    GUARDRAIL = "guardrail"


class Position(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: float
    y: float


class InputField(BaseModel):
    """One field of an Input node's schema, e.g. {"name": "query", "type": "string"}."""

    model_config = ConfigDict(extra="forbid")
    name: str
    type: Literal["string", "number", "boolean", "json"] = "string"
    required: bool = True
    description: str = ""


# --- Node config models -----------------------------------------------------


class InputNodeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["text", "json", "structured"] = "text"
    fields: list[InputField] = Field(default_factory=list)


class OutputNodeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: Literal["text", "json"] = "text"
    source_node: str | None = None
    """Optional explicit upstream node id whose result becomes flow output. If unset, uses the
    single upstream predecessor."""


class RetryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_attempts: int = Field(default=1, ge=1, le=10)
    backoff_seconds: float = Field(default=1.0, ge=0)


class AgentNodeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    description: str = ""
    instructions: str = "You are a helpful assistant."
    model: str = "default"
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=1024, ge=1, le=200_000)
    tools: list[str] = Field(default_factory=list)
    memory: str | None = None
    structured_output: dict[str, Any] | None = None
    retries: RetryConfig = Field(default_factory=RetryConfig)
    timeout_seconds: float = Field(default=60.0, gt=0)


class LLMNodeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str = "default"
    prompt_template: str = "{input}"
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=1024, ge=1, le=200_000)


class RouterRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    when: str
    """Expression evaluated against run state, e.g. "intent == 'billing'"."""
    target: str
    """Target node id."""


class RouterNodeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["expression", "rule", "llm"] = "rule"
    rules: list[RouterRule] = Field(default_factory=list)
    default_target: str | None = None
    llm_instructions: str | None = None
    """Used when mode == 'llm': instructions for structured-output routing decision."""
    model: str = "default"


class SupervisorNodeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agents: list[str] = Field(default_factory=list)
    """Node ids of delegate agents."""
    routing_instructions: str = "Delegate to the most appropriate agent."
    max_delegation_depth: int = Field(default=3, ge=1, le=20)
    max_iterations: int = Field(default=6, ge=1, le=50)
    fallback_agent: str | None = None
    model: str = "default"


class ToolNodeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool_id: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    """Static arguments; may reference run state via `{{var}}` templating at execution time."""


class MCPNodeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    server_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class RAGNodeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    knowledge_base_id: str
    top_k: int = Field(default=4, ge=1, le=50)
    embedding_model: str | None = None
    min_score: float = Field(default=0.0, ge=0, le=1)


class MemoryNodeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    memory_type: Literal["conversation", "semantic"] = "conversation"
    scope: Literal["run", "agent", "workspace"] = "agent"
    ttl_seconds: int | None = None


class HumanApprovalNodeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    condition: str | None = None
    """Optional expression; if false the node is skipped (auto-approved)."""
    approvers: list[str] = Field(default_factory=list)
    timeout_seconds: int | None = None
    message_template: str = "Approval required to continue."


class GuardrailCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal[
        "pii_detection",
        "blocked_keywords",
        "prompt_injection_heuristic",
        "max_input_size",
        "output_validation",
        "json_schema",
    ]
    config: dict[str, Any] = Field(default_factory=dict)


class GuardrailNodeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stage: Literal["pre", "post"] = "pre"
    checks: list[GuardrailCheck] = Field(default_factory=list)
    on_fail: Literal["block", "warn"] = "block"


# --- Node (discriminated union) ---------------------------------------------


class _NodeBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    position: Position = Field(default_factory=lambda: Position(x=0, y=0))
    label: str = ""


class InputNode(_NodeBase):
    type: Literal[NodeType.INPUT] = NodeType.INPUT
    config: InputNodeConfig = Field(default_factory=InputNodeConfig)


class OutputNode(_NodeBase):
    type: Literal[NodeType.OUTPUT] = NodeType.OUTPUT
    config: OutputNodeConfig = Field(default_factory=OutputNodeConfig)


class AgentNode(_NodeBase):
    type: Literal[NodeType.AGENT] = NodeType.AGENT
    config: AgentNodeConfig


class LLMNode(_NodeBase):
    type: Literal[NodeType.LLM] = NodeType.LLM
    config: LLMNodeConfig = Field(default_factory=LLMNodeConfig)


class RouterNode(_NodeBase):
    type: Literal[NodeType.ROUTER] = NodeType.ROUTER
    config: RouterNodeConfig = Field(default_factory=RouterNodeConfig)


class SupervisorNode(_NodeBase):
    type: Literal[NodeType.SUPERVISOR] = NodeType.SUPERVISOR
    config: SupervisorNodeConfig = Field(default_factory=SupervisorNodeConfig)


class ToolNode(_NodeBase):
    type: Literal[NodeType.TOOL] = NodeType.TOOL
    config: ToolNodeConfig


class MCPNode(_NodeBase):
    type: Literal[NodeType.MCP] = NodeType.MCP
    config: MCPNodeConfig


class RAGNode(_NodeBase):
    type: Literal[NodeType.RAG] = NodeType.RAG
    config: RAGNodeConfig


class MemoryNode(_NodeBase):
    type: Literal[NodeType.MEMORY] = NodeType.MEMORY
    config: MemoryNodeConfig = Field(default_factory=MemoryNodeConfig)


class HumanApprovalNode(_NodeBase):
    type: Literal[NodeType.HUMAN_APPROVAL] = NodeType.HUMAN_APPROVAL
    config: HumanApprovalNodeConfig = Field(default_factory=HumanApprovalNodeConfig)


class GuardrailNode(_NodeBase):
    type: Literal[NodeType.GUARDRAIL] = NodeType.GUARDRAIL
    config: GuardrailNodeConfig = Field(default_factory=GuardrailNodeConfig)


Node = Annotated[
    InputNode
    | OutputNode
    | AgentNode
    | LLMNode
    | RouterNode
    | SupervisorNode
    | ToolNode
    | MCPNode
    | RAGNode
    | MemoryNode
    | HumanApprovalNode
    | GuardrailNode,
    Field(discriminator="type"),
]


class Edge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    source: str
    target: str
    condition: str | None = None
    """Optional expression gating this edge, used by router nodes."""


class FlowSpec(BaseModel):
    """The canonical, runtime-independent representation of an agent workflow."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = FLOWSPEC_SCHEMA_VERSION
    id: str
    name: str
    version: int = 1
    description: str = ""

    inputs: list[InputField] = Field(default_factory=list)
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)

    variables: dict[str, Any] = Field(default_factory=dict)
    policies: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def node_by_id(self, node_id: str) -> Node | None:
        return next((n for n in self.nodes if n.id == node_id), None)
