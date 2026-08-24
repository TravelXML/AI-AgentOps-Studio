# Claude Code Master Prompt — Enterprise Agent Engineering Platform

You are a Principal Engineer, AI Platform Architect, Product Engineer, UX Engineer, DevOps Engineer, and QA Engineer working together.

Your task is to build a production-quality open-source platform that is significantly more developer- and enterprise-oriented than a basic visual AI workflow builder such as Langflow.

The product is an:

> **Enterprise Agent Engineering Platform — Build, Test, Secure, Deploy, Observe and Optimize AI Agents**

Do not build a toy demonstration.

Do not only generate architecture documents or placeholder components.

Build a **working end-to-end MVP** that can run locally using Docker Compose and can execute a real agent workflow.

The architecture must remain extensible for future enterprise capabilities.

---

# 1. Product Vision

The product should allow developers and enterprises to visually build and operate:

* LLM applications
* AI agents
* multi-agent systems
* RAG applications
* MCP-enabled agents
* supervisor-agent systems
* router-agent systems
* human-in-the-loop workflows
* tool-using agents
* model-routing workflows
* memory-enabled agents

The long-term product lifecycle is:

```text
DESIGN
   ↓
BUILD
   ↓
SIMULATE
   ↓
EVALUATE
   ↓
SECURE
   ↓
DEPLOY
   ↓
OBSERVE
   ↓
OPTIMIZE
```

This is not intended to be another drag-and-drop-only builder.

The primary differentiators are:

1. Natural Language → Agent Architecture
2. Multi-Agent systems as first-class abstractions
3. Agent execution flight recorder
4. Model routing and cost optimization
5. Evaluation CI/CD
6. Enterprise agent security
7. Agent memory control plane
8. Code ↔ Canvas interoperability
9. Framework-independent workflow specification
10. Production agent control center

---

# 2. Working Product Name

For the source code, temporarily use:

```text
AgentForge
```

Treat this only as an internal working name.

Structure the project so branding can easily be replaced later.

---

# 3. Core Design Principle

Create a framework-neutral workflow specification called:

```text
FlowSpec
```

The UI must NOT directly store LangGraph implementation details.

Architecture:

```text
Visual Canvas
      ↓
   FlowSpec
      ↓
Workflow Compiler
      ↓
Execution Adapter
      ↓
LangGraph
      ↓
LLMs / MCP / Tools / RAG
```

Eventually other runtime adapters should be possible:

```text
FlowSpec
   │
   ├── LangGraph
   ├── CrewAI
   ├── AutoGen
   ├── custom Python
   └── future runtimes
```

For MVP implement only:

```text
FlowSpec → LangGraph
```

But maintain the runtime abstraction.

---

# 4. Technology Stack

Use current stable releases at implementation time.

Do not blindly use version numbers from old tutorials.

## Frontend

Use:

```text
Next.js
TypeScript
React
@xyflow/react
Tailwind CSS
shadcn/ui
Zustand
TanStack Query
Zod
```

Use React Flow through:

```text
@xyflow/react
```

NOT the deprecated old `reactflow` package.

Use a polished enterprise UI.

---

# 5. Backend

Use:

```text
Python 3.12+
FastAPI
Pydantic v2
SQLAlchemy 2
Alembic
LangGraph
LiteLLM
PostgreSQL
pgvector
Redis
httpx
structlog
OpenTelemetry
```

Use async Python wherever practical.

Use dependency injection cleanly.

Do not create giant service classes.

---

# 6. Agent Execution Engine

Use:

```text
LangGraph
```

for MVP agent execution.

Use its native capabilities where appropriate:

* checkpoints
* threads
* persistence
* interrupts
* human-in-the-loop
* streaming
* graph state
* subgraphs
* replay
* fault recovery

Do not rebuild capabilities unnecessarily.

Create our own abstraction above LangGraph.

Example:

```python
class WorkflowRuntime(ABC):

    @abstractmethod
    async def compile(self, flow: FlowSpec):
        ...

    @abstractmethod
    async def execute(self, flow_id, inputs):
        ...

    @abstractmethod
    async def resume(self, run_id, input):
        ...

    @abstractmethod
    async def stream(self, run_id):
        ...
```

Then:

```python
class LangGraphRuntime(WorkflowRuntime):
    ...
```

---

# 7. Durable Platform Jobs

Do NOT require Temporal for the MVP.

Create interfaces so Temporal can later handle:

* scheduled workflows
* large evaluations
* deployments
* batch processing
* long-running jobs
* retryable external operations
* production orchestration

For MVP use:

```text
FastAPI
+
LangGraph persistence
+
Redis worker/background mechanism where needed
```

Create a future ADR explaining when Temporal should be introduced.

---

# 8. LLM Gateway

Use:

```text
LiteLLM
```

Create a provider abstraction.

Support configuration for:

```text
OpenAI
Anthropic
Google Gemini
Groq
OpenRouter
NVIDIA NIM
Azure OpenAI
AWS Bedrock
Ollama
custom OpenAI-compatible models
```

The application MUST NOT require a paid provider.

Local development should work using:

```text
Ollama
```

Also implement:

```text
MockLLM
```

for automated tests.

Example architecture:

```text
Agent
   ↓
Model Gateway
   ↓
LiteLLM
   │
   ├── Ollama
   ├── OpenRouter
   ├── Groq
   ├── OpenAI
   ├── Claude
   └── Gemini
```

Never hard-code provider SDK calls throughout business logic.

---

# 9. Repository Architecture

Build as a monorepo.

Suggested structure:

```text
agentforge/
│
├── apps/
│   ├── web/
│   └── api/
│
├── packages/
│   ├── flowspec/
│   ├── runtime/
│   ├── model_gateway/
│   ├── evaluation/
│   ├── security/
│   ├── observability/
│   └── sdk/
│
├── infrastructure/
│   ├── docker/
│   ├── migrations/
│   └── observability/
│
├── examples/
│   ├── simple-agent/
│   ├── supervisor-agent/
│   └── rag-agent/
│
├── tests/
│   ├── integration/
│   └── e2e/
│
├── docs/
│   ├── architecture/
│   ├── adr/
│   ├── api/
│   └── development/
│
├── docker-compose.yml
├── Makefile
├── .env.example
├── README.md
├── CONTRIBUTING.md
├── SECURITY.md
└── LICENSE
```

You may improve this structure where necessary.

Keep domain boundaries clean.

---

# 10. FlowSpec

FlowSpec is one of the most important pieces of the project.

Create strongly typed Pydantic schemas.

Conceptual structure:

```json
{
  "id": "customer-support-v1",
  "name": "Customer Support Agent",
  "version": 1,

  "inputs": [],

  "nodes": [],

  "edges": [],

  "variables": {},

  "policies": {},

  "metadata": {}
}
```

Example node:

```json
{
  "id": "support-agent",

  "type": "agent",

  "position": {
    "x": 420,
    "y": 200
  },

  "config": {
    "name": "Support Agent",
    "instructions": "Help the customer.",
    "model": "default",
    "tools": []
  }
}
```

Example edge:

```json
{
  "id": "edge-1",
  "source": "input",
  "target": "support-agent"
}
```

FlowSpec must be:

* serializable
* versionable
* validated
* runtime independent
* exportable
* importable
* backward-compatible where possible

Create explicit:

```text
FlowSpecVersion
```

support.

---

# 11. MVP Node Types

Do not build 100 components.

Implement these nodes well:

```text
Input
Output
Agent
LLM
Router
Supervisor
Tool
MCP
RAG
Memory
Human Approval
Guardrail
```

Visual categories:

```text
CORE
AI
AGENTS
KNOWLEDGE
TOOLS
CONTROL
SECURITY
```

---

# 12. Input Node

Support:

```text
text
JSON
structured fields
```

Input schema should be configurable.

Example:

```json
{
  "query": "string",
  "customer_id": "string"
}
```

---

# 13. Agent Node

Configuration panel should include:

```text
Name
Description
System instructions
Model
Temperature
Max tokens
Tools
Memory
Structured output
Retries
Timeout
```

Agents should be able to call registered tools.

---

# 14. Supervisor Node

Supervisor is a first-class node.

Example:

```text
                   Supervisor
                 /      |      \
                ↓       ↓       ↓
           Research   Finance   Legal
              Agent     Agent    Agent
                 \       |       /
                     ↓
                  Output
```

Supervisor configuration:

```text
available agents
routing instructions
maximum delegation depth
maximum iterations
fallback agent
```

Record why an agent was selected.

---

# 15. Router Node

Support deterministic and AI routing.

Modes:

```text
expression
rule
LLM
```

Example:

```text
IF intent == "billing"
    → BillingAgent

IF intent == "support"
    → SupportAgent

ELSE
    → GeneralAgent
```

LLM router should return structured output.

---

# 16. Human Approval Node

Implement a true resumable workflow.

Example:

```text
RefundAgent
     ↓
Amount > $500?
     ↓
Human Approval
     ↓
Execute Refund
```

The execution should pause.

UI should display:

```text
Waiting for approval
```

User can:

```text
Approve
Reject
Edit
```

Execution then resumes.

Do not fake this on the frontend.

Use LangGraph persistence/interrupt behavior.

---

# 17. Tool System

Create a Tool Registry.

Tool interface should resemble:

```python
class ToolDefinition:
    id: str
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    permissions: list[str]
```

Built-in MVP tools:

```text
HTTP GET
HTTP POST
Calculator
Current Date/Time
JSON Transform
Python sandbox placeholder
```

Do NOT execute arbitrary unrestricted Python on the API server.

If Python execution exists, isolate it behind an explicit interface and mark real sandboxing as required before production.

---

# 18. MCP Support

Implement MCP as a first-class integration.

Provide an:

```text
MCP Server Registry
```

Users should eventually register MCP servers through:

```text
stdio
HTTP
streamable HTTP
```

For MVP prioritize currently supported recommended transports rather than implementing deprecated mechanisms unnecessarily.

MCP tool discovery process:

```text
Register MCP Server
      ↓
Connect
      ↓
Discover tools
      ↓
Persist metadata
      ↓
Expose tools to agents
```

UI page:

```text
Settings
  → MCP Servers
```

Show:

```text
server name
connection status
number of tools
last checked
enabled/disabled
```

Do not expose credentials to the frontend.

---

# 19. RAG Node

Implement basic production-structured RAG.

Pipeline:

```text
Document
   ↓
Loader
   ↓
Chunker
   ↓
Embedding
   ↓
pgvector
   ↓
Retriever
   ↓
Agent
```

MVP ingestion types:

```text
TXT
Markdown
PDF
```

Use a pluggable abstraction for:

```text
embeddings
vector stores
chunkers
retrievers
```

Default local vector store:

```text
PostgreSQL + pgvector
```

Do not couple RAG logic directly to pgvector.

---

# 20. Memory Node

Create memory types conceptually:

```text
Working Memory
Conversation Memory
Semantic Memory
Episodic Memory
```

For MVP fully implement:

```text
Conversation Memory
Semantic Memory
```

Expose metadata:

```text
memory ID
owner
agent
source
created_at
expires_at
metadata
```

Create APIs so users can:

```text
inspect
search
delete
expire
```

Long-term UI should answer:

```text
What does this agent remember?

Why is it remembered?

Who created the memory?

Which agent can access it?

When does it expire?
```

---

# 21. Guardrail Node

Implement pluggable guardrails.

MVP checks:

```text
PII detection
blocked keywords
prompt-injection heuristics
maximum input size
output validation
JSON schema validation
```

Architecture:

```text
Input
  ↓
Pre Guardrails
  ↓
Agent
  ↓
Post Guardrails
  ↓
Output
```

Guardrail result:

```json
{
  "passed": true,
  "rules": [],
  "actions": [],
  "metadata": {}
}
```

Do not claim heuristic prompt-injection detection provides complete security.

---

# 22. AI Architect — Natural Language → Flow

This is a flagship feature.

Add a UI button:

```text
Generate with AI
```

User types:

```text
Create a customer support system with a supervisor
that routes billing requests to a billing agent,
technical issues to a support agent, retrieves product
documentation, and requires human approval for refunds
above $500.
```

AI Architect should produce structured FlowSpec JSON.

Process:

```text
Natural Language
      ↓
Architecture Prompt
      ↓
Structured FlowSpec
      ↓
Schema Validation
      ↓
Safety Validation
      ↓
Canvas
```

Never trust raw LLM JSON.

Validate with Pydantic.

If invalid:

```text
LLM
 ↓
validation errors
 ↓
repair attempt
 ↓
validate again
```

Set a maximum repair count.

AI Architect must NEVER execute the generated workflow automatically.

User reviews it first.

---

# 23. Visual Builder UX

Main page should resemble a serious IDE.

Layout:

```text
┌─────────────────────────────────────────────────────────┐
│ AgentForge | Project | Save | Run | Deploy             │
├───────────┬───────────────────────────────┬─────────────┤
│           │                               │             │
│ NODE      │                               │ INSPECTOR   │
│ LIBRARY   │          CANVAS               │             │
│           │                               │ Properties  │
│ Input     │                               │ Prompt      │
│ Agent     │                               │ Model       │
│ Router    │                               │ Tools       │
│ MCP       │                               │ Memory      │
│ RAG       │                               │             │
│           │                               │             │
├───────────┴───────────────────────────────┴─────────────┤
│ RUN / TRACE / OUTPUT / ERRORS                          │
└─────────────────────────────────────────────────────────┘
```

Requirements:

* drag-and-drop nodes
* connect nodes
* delete
* duplicate
* copy/paste
* zoom
* minimap
* undo/redo
* keyboard shortcuts
* auto-layout
* node search
* validation errors
* dirty/save state
* execution state
* run current flow

---

# 24. Node Visual State

Nodes should visually indicate:

```text
IDLE
QUEUED
RUNNING
SUCCESS
FAILED
WAITING
SKIPPED
```

When executing:

```text
Input
  ↓
Agent     ← glowing/running
  ↓
Tool
  ↓
Output
```

Update status live.

---

# 25. Workflow Validation

Before execution validate:

```text
missing input
missing output
orphan nodes
invalid edges
cycles where unsupported
missing model
missing credentials
missing MCP server
invalid tool
invalid variable
invalid structured-output schema
unsafe configuration
```

Display actionable errors.

Example:

```text
Agent "Billing Agent" has no model configured.
```

Not:

```text
ValidationError 0x7823
```

---

# 26. Workflow Compiler

Create:

```text
FlowSpec
    ↓
Validation
    ↓
Normalization
    ↓
Graph analysis
    ↓
LangGraph compilation
```

Compiler interface:

```python
class FlowCompiler:

    def validate(...):
        ...

    def normalize(...):
        ...

    def compile(...):
        ...
```

Separate graph definition from runtime execution.

---

# 27. Execution Model

Each workflow execution becomes a:

```text
Run
```

Each node execution becomes a:

```text
RunStep
```

Each event becomes a:

```text
RunEvent
```

Example:

```text
Run
 ├── Input Step
 ├── Supervisor Step
 │     ├── Model Call
 │     └── Routing Decision
 ├── Research Agent
 │     ├── Model Call
 │     └── Tool Call
 └── Output
```

---

# 28. Agent Flight Recorder

This is a major product differentiator.

Store structured execution information.

For every step capture:

```text
run ID
step ID
node ID
node type
parent step
start time
end time
latency
status
model
provider
input tokens
output tokens
total tokens
estimated cost
tool
tool arguments
tool result
routing decision
errors
retry count
```

Do NOT store secrets.

Sensitive values should pass through redaction.

---

# 29. Trace UI

Create a trace page.

Example:

```text
RUN 12984

✓ Input                         12 ms

✓ Supervisor                  842 ms
    Model: local-model
    Decision: research_agent

✓ Research Agent             1.7 sec

    ✓ LLM                    823 ms
    ✓ Search Tool            611 ms
    ✓ LLM                    266 ms

✓ Output                       8 ms
```

Selecting a step opens:

```text
Input
Output
Metadata
Timing
Tokens
Cost
Errors
```

---

# 30. Replay

Design the run model for future:

```text
Replay Run
Fork Run
Replay From Node
```

For MVP implement:

```text
Replay entire run
```

If practical, also implement:

```text
Fork from checkpoint
```

Do not corrupt the original run.

---

# 31. Streaming

Use:

```text
Server-Sent Events
```

or a clean WebSocket implementation.

For MVP prefer SSE unless bidirectional real-time communication materially requires WebSockets.

Stream events:

```text
run.started
node.started
llm.started
llm.token
llm.completed
tool.started
tool.completed
node.completed
node.failed
run.waiting
run.completed
run.failed
```

Create a typed event schema.

---

# 32. Model Configuration

Create:

```text
Settings → Models
```

Allow:

```text
provider
model
base URL
credential reference
temperature defaults
timeout
maximum retries
```

Never persist raw API keys in FlowSpec.

Use:

```text
secret_id
```

references.

---

# 33. Model Router

Create basic routing infrastructure.

Flow:

```text
Agent
  ↓
Model Router
  ├── fast/cheap
  ├── balanced
  └── best quality
```

Routing factors:

```text
task type
cost ceiling
latency target
provider availability
context requirements
privacy requirement
```

MVP can implement rule-based routing.

Design interface for intelligent routing later.

---

# 34. Cost Tracking

Store per-call:

```text
provider
model
prompt tokens
completion tokens
cached tokens where available
estimated cost
latency
```

Dashboard should aggregate:

```text
cost per workflow
cost per model
cost per run
cost per day
tokens per model
```

If a local model has zero API cost:

```text
API Cost: $0
```

Do not represent local compute cost as zero total economic cost.

Call it API cost.

---

# 35. Evaluations

Create an Evaluation module.

Evaluation entities:

```text
Dataset
TestCase
Evaluator
EvaluationRun
EvaluationResult
```

MVP evaluators:

```text
exact match
contains
JSON schema
regex
latency threshold
cost threshold
LLM-as-judge
```

LLM judge should be optional.

Tests must work without paid LLMs.

---

# 36. Evaluation UI

Allow:

```text
Dataset
    ↓
Choose Flow Version
    ↓
Run Evaluation
    ↓
Results
```

Display:

```text
Pass rate
Failure rate
Average latency
Average tokens
Estimated API cost
Individual failures
```

---

# 37. Future Agent CI/CD

Design APIs for future use:

```text
git commit
   ↓
evaluation suite
   ↓
quality gate
   ↓
security checks
   ↓
deployment
```

Example future policy:

```text
success_rate >= 95%
hallucination_score <= threshold
p95_latency < 3 seconds
cost_per_request < $0.02
```

Do not implement a huge CI/CD system in MVP.

Create clean interfaces and documentation.

---

# 38. Security Architecture

Security must be designed from the beginning.

Use:

```text
workspace
project
environment
flow
run
```

resource boundaries.

Every record should be designed for future tenant isolation.

For MVP support a development user/workspace but do NOT bake single-user assumptions into the database model.

---

# 39. Authentication

Implement clean auth architecture.

For local MVP either:

```text
development auth mode
```

or a simple local authentication implementation.

Create future-compatible:

```text
User
Workspace
WorkspaceMember
Role
```

structures.

Roles:

```text
Owner
Admin
Developer
Viewer
```

Do not spend excessive MVP effort building enterprise SSO.

Document future:

```text
OIDC
SAML
SCIM
```

support.

---

# 40. Secrets

Create a Secrets abstraction.

Never:

* commit API keys
* expose secrets through frontend APIs
* include secrets in traces
* include secrets in logs
* store secrets in FlowSpec

MVP local encrypted storage may be implemented if done safely.

Architecture should later support:

```text
HashiCorp Vault
AWS Secrets Manager
Azure Key Vault
GCP Secret Manager
```

---

# 41. Agent Permissions

Design for agent-level permissions.

Example:

```text
Agent: RefundAgent

Allowed:

order.read
customer.read
refund.create

Conditional:

refund.create <= 500

Approval required:

refund.create > 500

Denied:

customer.export
order.delete
```

MVP permission enforcement can be simple.

But create:

```text
PolicyEngine
```

interface.

All tool calls should pass through the policy layer.

Architecture:

```text
Agent
   ↓
Policy Engine
   ↓
Tool Gateway
   ↓
External Tool
```

---

# 42. Audit Log

Create immutable-style audit records for important actions:

```text
workflow created
workflow edited
workflow executed
secret changed
MCP server added
approval accepted
approval rejected
deployment triggered
permission changed
```

Each record:

```text
timestamp
actor
workspace
action
resource
metadata
```

---

# 43. Database

Use PostgreSQL.

Suggested tables:

```text
users

workspaces
workspace_members

projects

flows
flow_versions

runs
run_steps
run_events

model_configs

tool_definitions
mcp_servers
mcp_tools

datasets
test_cases
evaluation_runs
evaluation_results

knowledge_bases
documents
document_chunks

memories

secrets

audit_logs
```

Use UUIDs.

Use:

```text
created_at
updated_at
```

consistently.

Add appropriate indexes.

Use JSONB only when it genuinely provides flexibility.

Do not turn the entire relational model into JSON blobs.

---

# 44. Flow Versioning

Every save that represents a meaningful published version should create:

```text
FlowVersion
```

Workflow should support:

```text
draft
published
archived
```

Runs reference an immutable version.

Never allow changing history of an already executed version.

---

# 45. API Design

Use:

```text
/api/v1
```

Example routes:

```text
GET    /api/v1/projects

POST   /api/v1/flows
GET    /api/v1/flows/{id}
PUT    /api/v1/flows/{id}

POST   /api/v1/flows/{id}/validate
POST   /api/v1/flows/{id}/publish

POST   /api/v1/flows/{id}/runs

GET    /api/v1/runs/{id}
GET    /api/v1/runs/{id}/events

POST   /api/v1/runs/{id}/resume
POST   /api/v1/runs/{id}/replay

GET    /api/v1/models
POST   /api/v1/models

GET    /api/v1/tools

GET    /api/v1/mcp/servers
POST   /api/v1/mcp/servers

POST   /api/v1/architect/generate

POST   /api/v1/knowledge-bases
POST   /api/v1/knowledge-bases/{id}/documents

POST   /api/v1/evaluations

GET    /health
GET    /ready
```

Generate OpenAPI documentation.

---

# 46. Error Model

Create consistent API errors.

Example:

```json
{
  "error": {
    "code": "FLOW_VALIDATION_FAILED",
    "message": "Workflow contains invalid nodes.",
    "details": [],
    "request_id": "..."
  }
}
```

Never leak stack traces in production responses.

---

# 47. Observability

Use structured logging.

Include:

```text
request_id
workspace_id
project_id
flow_id
run_id
node_id
```

where applicable.

Prepare OpenTelemetry instrumentation for:

```text
HTTP
database
LLM
agent
tool
workflow
```

MVP should expose useful operational metrics.

---

# 48. Metrics

Examples:

```text
workflow_runs_total

workflow_run_duration_seconds

workflow_failures_total

agent_node_duration_seconds

llm_requests_total

llm_tokens_total

llm_api_cost_total

tool_calls_total

tool_failures_total

evaluation_runs_total
```

---

# 49. Production Dashboard

Build an initial dashboard:

```text
AI CONTROL CENTER

Active Agents
Runs Today
Success Rate
Average Latency
API Cost Today

Recent Runs

Model Usage

Top Workflows

Failures
```

Do not invent metrics.

If no data exists show:

```text
No runs yet
```

---

# 50. Pages

MVP application navigation:

```text
Dashboard

Projects

Flows
  → Flow Builder
  → Versions

Runs
  → Trace

Evaluations

Knowledge

MCP Servers

Models

Settings
```

---

# 51. UI Quality

Do not create a generic developer-template appearance.

Use a professional AI engineering console aesthetic.

Requirements:

* strong typography
* restrained enterprise palette
* excellent spacing
* responsive layout
* polished empty states
* skeleton loading
* useful errors
* tooltips
* keyboard navigation
* accessibility
* dark mode
* light mode

Avoid excessive gradients and visual noise.

---

# 52. Code ↔ Canvas

Design FlowSpec so future bidirectional conversion is possible.

MVP implement:

```text
FlowSpec JSON Export
FlowSpec JSON Import
```

Also implement one useful:

```text
Export → Python/LangGraph
```

feature.

Generated code should be understandable.

Example:

```text
Canvas
  ↓
FlowSpec
  ↓
LangGraph Code Generator
  ↓
downloadable Python project
```

Do NOT promise perfect Python → Canvas conversion in MVP.

Document it as Phase 2.

---

# 53. Example Templates

Ship working examples:

## Example 1

```text
Simple Agent

Input
 ↓
Agent
 ↓
Output
```

## Example 2

```text
Customer Support Router

Input
 ↓
Router
 ├── Billing Agent
 └── Support Agent
 ↓
Output
```

## Example 3

```text
Supervisor Multi-Agent

Input
 ↓
Supervisor
 ├── Research Agent
 ├── Analysis Agent
 └── Writer Agent
 ↓
Output
```

## Example 4

```text
Human Approval

Input
 ↓
Agent
 ↓
Human Approval
 ↓
Output
```

All examples must actually execute.

---

# 54. Local Development

One of the most important requirements:

A developer should be able to clone the repository and run:

```bash
cp .env.example .env
docker compose up -d
```

Then start development with documented commands.

Prefer useful Make commands:

```bash
make install

make dev

make test

make lint

make format

make migrate

make seed

make down
```

Document exactly what each does.

---

# 55. Docker Compose

Provide services for:

```text
PostgreSQL + pgvector
Redis
API
Web
```

Optionally:

```text
Ollama profile
```

Do not require Grafana/Prometheus just to launch the MVP.

Observability services can use an optional compose profile.

---

# 56. Environment Configuration

Create:

```text
.env.example
```

Include examples but never real credentials.

Example concepts:

```text
DATABASE_URL=

REDIS_URL=

APP_SECRET=

DEFAULT_MODEL_PROVIDER=

OLLAMA_BASE_URL=

OPENAI_API_KEY=

ANTHROPIC_API_KEY=

GROQ_API_KEY=

OPENROUTER_API_KEY=
```

The application should boot without cloud LLM credentials.

---

# 57. Testing

Testing is mandatory.

Backend:

```text
pytest
pytest-asyncio
httpx test client
```

Frontend:

```text
Vitest
React Testing Library
```

E2E:

```text
Playwright
```

Implement unit tests for:

```text
FlowSpec validation

graph compiler

router logic

policy engine

cost calculator

LLM gateway

tool execution

human approval

workflow validation
```

---

# 58. End-to-End Test

Create at least one E2E test:

```text
Create flow
      ↓
Add Input
      ↓
Add Agent
      ↓
Add Output
      ↓
Save
      ↓
Run
      ↓
Observe node execution
      ↓
Receive output
      ↓
Open trace
```

Use MockLLM so CI requires no API key.

---

# 59. Quality Gates

Before considering a phase complete run:

```bash
make lint
make test
make build
```

Fix failures.

Do not mark unfinished tests as passing.

Do not silence TypeScript errors with:

```text
any
```

unless absolutely necessary and documented.

Do not add:

```text
# noqa
eslint-disable
type: ignore
```

as a shortcut for poor implementation.

---

# 60. Security Tests

Test:

```text
secret redaction

invalid FlowSpec

unauthorized tool operation

dangerous URL input where applicable

malformed structured output

oversized inputs

invalid MCP configuration
```

Prevent SSRF in generic HTTP tools.

At minimum block obvious access to:

```text
localhost
loopback
link-local
cloud metadata addresses
```

unless explicitly permitted by trusted configuration.

---

# 61. Coding Standards

Use:

Python:

```text
ruff
mypy or pyright
pytest
```

TypeScript:

```text
eslint
prettier
tsc
```

Use strict typing.

Functions should generally do one thing.

Prefer composition.

Avoid unnecessary abstraction.

But create interfaces around true integration boundaries.

---

# 62. Architecture Decisions

Create ADRs including:

```text
ADR-001 FlowSpec as canonical representation

ADR-002 LangGraph as initial runtime

ADR-003 LiteLLM as model gateway

ADR-004 PostgreSQL/pgvector

ADR-005 SSE vs WebSocket

ADR-006 Secret architecture

ADR-007 Multi-tenant data model

ADR-008 When to introduce Temporal
```

Keep ADRs concise and useful.

---

# 63. README

Create an excellent GitHub README.

Include:

```text
Product overview

Why AgentForge

Feature matrix

Architecture

Screenshots placeholders only if screenshots have not yet been generated

Quick Start

Demo flow

Technology stack

Project structure

Development

Testing

Security

Roadmap

Contributing

License
```

Use Mermaid diagrams where helpful.

Make README technically credible and SEO friendly for terms such as:

```text
AI Agents
Agentic AI
Multi-Agent Systems
LangGraph
MCP
Model Context Protocol
RAG
LLM Observability
Agent Evaluation
AI Governance
AI Agent Platform
Enterprise AI
```

Do not keyword-stuff.

---

# 64. Documentation

Create:

```text
docs/architecture/system-overview.md

docs/architecture/flowspec.md

docs/architecture/execution-engine.md

docs/architecture/security.md

docs/architecture/memory.md

docs/development/local-development.md

docs/development/creating-node.md

docs/development/creating-tool.md

docs/api/api-overview.md
```

---

# 65. Phase 1 — Foundation

Build first:

```text
monorepo

database

FastAPI

Next.js

React Flow canvas

FlowSpec

flow CRUD

12 node visual definitions

workflow validation

LangGraph compiler

LiteLLM gateway

Ollama support

MockLLM
```

Do not continue until this vertical foundation works.

---

# 66. Phase 2 — Working Execution

Implement:

```text
workflow execution

streaming

run persistence

run steps

trace data

canvas execution status

agent node

router node

supervisor node

tool node

human approval

replay
```

Acceptance test:

A supervisor workflow must successfully execute locally.

---

# 67. Phase 3 — AI Architect

Implement:

```text
Natural Language → FlowSpec

schema validation

repair

canvas rendering

user review
```

Acceptance:

Prompt:

```text
Create a supervisor with a researcher and writer.
```

must generate:

```text
Input
 ↓
Supervisor
 ├── Researcher
 └── Writer
 ↓
Output
```

as a valid editable FlowSpec.

---

# 68. Phase 4 — RAG + Memory + MCP

Implement:

```text
document ingestion

pgvector

RAG

conversation memory

semantic memory

MCP registry

MCP tool discovery
```

---

# 69. Phase 5 — Evaluation

Implement:

```text
datasets

test cases

evaluation runs

evaluators

evaluation dashboard
```

---

# 70. Phase 6 — Security / Governance Foundation

Implement:

```text
PolicyEngine

tool permissions

audit trail

secret handling

PII redaction

guardrails

workspace isolation architecture
```

---

# 71. Phase 7 — Production Dashboard

Implement:

```text
dashboard

cost metrics

latency

success rate

model usage

tool failures

workflow performance
```

---

# 72. DO NOT BUILD YET

Do not spend MVP time implementing:

```text
Kubernetes operator

full SAML

SCIM

billing system

agent marketplace

complex SaaS subscriptions

mobile app

hundreds of integrations

full Temporal deployment

custom vector database

custom LLM inference engine

custom distributed scheduler
```

Design extensibility but avoid premature implementation.

---

# 73. MVP Definition of Done

The MVP is DONE only when I can:

1. Clone repository.

2. Start dependencies locally.

3. Open web UI.

4. Create project.

5. Create workflow.

6. Drag nodes onto canvas.

7. Connect nodes.

8. Configure an agent.

9. Select Ollama or MockLLM.

10. Save workflow.

11. Validate workflow.

12. Run workflow.

13. Watch nodes execute live.

14. See output.

15. Open execution trace.

16. See latency and token metadata.

17. Build a router workflow.

18. Build a supervisor workflow.

19. Pause workflow for human approval.

20. Resume workflow.

21. Generate a FlowSpec using AI Architect.

22. Export FlowSpec JSON.

23. Import FlowSpec JSON.

24. Run tests without paid APIs.

25. Restart services without losing saved workflows.

Anything less is an incomplete vertical slice.

---

# 74. Developer Experience

The first successful experience should take less than five conceptual steps:

```text
git clone

docker compose up

open browser

load example

run
```

Optimize the repository around this experience.

---

# 75. Claude Code Working Instructions

You are not merely advising me.

You are responsible for implementing this project in the repository.

Follow this workflow.

## Step 1

Inspect the current repository.

Understand:

```text
existing files
git state
existing dependencies
existing architecture
```

Never delete useful existing work without reason.

---

## Step 2

Create:

```text
IMPLEMENTATION_PLAN.md
```

Break work into:

```text
Phase
Task
Status
Dependencies
Acceptance test
```

---

## Step 3

Create architecture foundations before features.

Do not create everything simultaneously.

Start with the smallest complete vertical slice.

---

## Step 4

After every meaningful phase:

```text
run formatter
run lint
run tests
run build
```

Fix errors immediately.

---

## Step 5

Keep:

```text
IMPLEMENTATION_PLAN.md
```

updated as work progresses.

Use:

```text
TODO
IN PROGRESS
DONE
BLOCKED
```

---

# 76. Important Claude Behavior

Do NOT repeatedly ask me:

```text
Should I continue?

Would you like me to implement Phase 2?

Can I create these files?
```

Make reasonable engineering decisions and continue.

Only stop when genuinely blocked by information that cannot reasonably be inferred.

---

# 77. Do Not Fake Functionality

Never implement:

```python
def execute_agent():
    return "Agent executed successfully"
```

and call the feature done.

If the UI says something works, implement the backend behavior.

If something is intentionally postponed, clearly mark it:

```text
Not implemented in MVP
```

---

# 78. No Fake Metrics

Never populate dashboards with fictional production metrics.

Development seed data may exist but must visibly be labeled:

```text
Demo Data
```

---

# 79. No Fake Integrations

If an MCP server cannot connect:

show:

```text
Disconnected
```

not:

```text
Connected
```

If no API key exists:

show:

```text
Not configured
```

---

# 80. Security Rules for Claude

Never:

```text
commit secrets

print API keys

disable authentication globally in production

use eval() on user input

execute arbitrary host shell commands from workflows

run arbitrary Python in the main API process

disable TLS verification as a fix

allow unrestricted SSRF

deserialize untrusted pickle

use unsafe YAML loading
```

---

# 81. Database Migrations

Every schema change must use Alembic.

Do not rely on:

```python
Base.metadata.create_all()
```

as the production migration strategy.

---

# 82. API / UI Contract

Generate or maintain typed contracts.

Avoid duplicating interface definitions manually where possible.

Frontend request/response structures should remain synchronized with backend OpenAPI schemas.

---

# 83. Git Hygiene

Make logical changes.

Do not commit:

```text
.env

API keys

node_modules

venv

build output

database volumes

model files
```

Create comprehensive `.gitignore`.

---

# 84. Performance

Avoid premature optimization but design for:

```text
1000+ workflows

large trace histories

streaming runs

many concurrent agent executions
```

Paginate:

```text
runs
audit records
trace events
flows
documents
```

Do not fetch unlimited database records.

---

# 85. Reliability

For external operations implement:

```text
timeouts
bounded retries
exponential backoff where appropriate
cancellation handling
clear errors
```

Retries must not cause dangerous duplicate side effects.

Design tool execution with idempotency in mind.

---

# 86. Run State Machine

Use explicit states:

```text
CREATED

QUEUED

RUNNING

WAITING_FOR_HUMAN

SUCCEEDED

FAILED

CANCELLED
```

Node states:

```text
PENDING

RUNNING

WAITING

SUCCEEDED

FAILED

SKIPPED
```

Do not infer state from missing timestamps.

---

# 87. Product Differentiation

While building, always remember:

The product should NOT be described as:

> a Langflow alternative.

Its higher-level positioning is:

> **The engineering control plane for enterprise AI agents.**

We compete on:

```text
production readiness

debugging

evaluation

governance

multi-agent engineering

model independence

developer experience
```

rather than simply:

```text
number of nodes
```

---

# 88. Architecture Target

Maintain this conceptual architecture:

```text
                    ┌───────────────────────┐
                    │      Web Console      │
                    │ Next.js + React Flow  │
                    └───────────┬───────────┘
                                │
                                ↓
                    ┌───────────────────────┐
                    │      FastAPI API      │
                    └───────────┬───────────┘
                                │
             ┌──────────────────┼─────────────────┐
             │                  │                 │
             ↓                  ↓                 ↓
       Flow Service       Run Service       Eval Service
             │                  │                 │
             ↓                  ↓                 ↓
         FlowSpec         Runtime Adapter     Evaluators
                                │
                                ↓
                         LangGraph Runtime
                                │
             ┌──────────────────┼──────────────────┐
             │                  │                  │
             ↓                  ↓                  ↓
       Model Gateway       Tool Gateway       Memory
             │                  │                  │
             ↓                  ↓                  ↓
          LiteLLM             MCP            PostgreSQL
             │                                   pgvector
     ┌───────┼─────────┐
     ↓       ↓         ↓
   Ollama  OpenAI    Claude
     │
 OpenRouter / Groq /
 Gemini / NVIDIA / etc.
```

---

# 89. Future Enterprise Architecture

Make current abstractions capable of later supporting:

```text
                           API Gateway
                                │
                         Control Plane
                                │
       ┌────────────────────────┼───────────────────────┐
       │                        │                       │
       ↓                        ↓                       ↓
Workflow Control         Agent Runtime           Eval Platform
       │                        │                       │
       ↓                        ↓                       ↓
   Temporal              LangGraph Workers          Workers
                                │
                                ↓
                         Secure Tool Runtime
                                │
              ┌─────────────────┼──────────────────┐
              ↓                 ↓                  ↓
             MCP               APIs           Sandboxes
```

Do not implement all of this now.

---

# 90. Final Deliverables

At the end provide:

```text
working source code

README.md

docker-compose.yml

.env.example

database migrations

unit tests

integration tests

E2E test

example workflows

architecture documentation

ADRs

API documentation

IMPLEMENTATION_PLAN.md

ROADMAP.md
```

---

# 91. Roadmap

ROADMAP.md should contain:

## V0.1

```text
Visual builder
FlowSpec
LangGraph runtime
LLM gateway
Tools
Trace
Human approval
AI Architect
```

## V0.2

```text
RAG
Memory
MCP registry
Evaluations
Model router
```

## V0.3

```text
Policies
RBAC
Audit
Advanced observability
Deployment environments
```

## V0.4

```text
Temporal
Distributed workers
Secure sandboxes
Git integration
Agent CI/CD
```

## V1.0 Enterprise

```text
SSO
SAML
SCIM
multi-tenancy
data residency
enterprise secrets
advanced policies
private networking
deployment governance
high availability
```

---

# 92. First Implementation Target

DO NOT start by implementing all 92 sections.

Start by making this work perfectly:

```text
User
 ↓
Visual Builder
 ↓
Input
 ↓
Agent
 ↓
Output
 ↓
FlowSpec
 ↓
LangGraph Compiler
 ↓
MockLLM / Ollama
 ↓
Execution
 ↓
Streaming Events
 ↓
Trace
 ↓
Result
```

Once that vertical slice works and tests pass, progressively implement:

```text
Router
Supervisor
Tools
Human Approval
AI Architect
RAG
Memory
MCP
Evaluation
Security
Dashboard
```

This order is important.

---

# 93. Immediate Action

Begin now.

Perform these actions without asking me for confirmation:

1. Inspect repository.
2. Create `IMPLEMENTATION_PLAN.md`.
3. Create monorepo foundation.
4. Configure Docker Compose.
5. Implement FlowSpec.
6. Implement database models/migrations.
7. Create FastAPI API.
8. Create Next.js application.
9. Implement React Flow canvas.
10. Implement Input, Agent and Output nodes.
11. Implement LangGraph runtime adapter.
12. Implement MockLLM.
13. Implement Ollama/LiteLLM model gateway.
14. Implement execution API.
15. Stream execution events to canvas.
16. Persist trace.
17. Display trace.
18. Create example flow.
19. Add automated tests.
20. Run the complete system and fix failures.

Do not stop after generating files.

Verify the vertical slice actually works.

After the first vertical slice is operational, update `IMPLEMENTATION_PLAN.md` and proceed through the remaining MVP phases in order.

The goal is not maximum code.

The goal is a **small, beautifully engineered, genuinely working AI Agent Engineering Platform that can evolve into an enterprise product.**
