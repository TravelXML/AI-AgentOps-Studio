# AgentQ, explained without jargon

This guide assumes no prior knowledge of AI agents, workflow builders, or the words "LLM" and
"node." If you can drag a box on a screen and type a sentence, you can use this.

## What is this thing?

AgentQ is a tool for building small AI-powered programs by dragging boxes onto a canvas and
connecting them with lines - instead of writing code. Each box does one job. You connect boxes to
describe "first do this, then do that." Then you click **Run**, and it actually does it, using a
real AI model (or a free stand-in one, see below), and shows you exactly what happened at every
step.

People build things like:
- "Read a customer's message, and if it's about billing, answer directly; otherwise ask a human
  to approve the response first."
- "Answer questions using only the content of our own documents, not the model's general
  knowledge."
- "Look up a number from a calculator, then explain the result in plain English."

## The four words you actually need to know

| Word | What it means |
|---|---|
| **Flow** | The whole thing you build - a set of boxes connected by lines, saved under a name. |
| **Node** | One box on the canvas. Each node does exactly one job (see the table below). |
| **Run** | One execution of a flow, start to finish, with real input. Every run is recorded. |
| **Model** | The AI brain a node can call (like the engine everyone means when they say "AI"). |

That's genuinely all the vocabulary this needs. Everything else is a variation on those four
ideas.

## Your first five minutes

1. Open the app (usually `http://localhost:3000`) and click **Flows** in the left sidebar.
2. Click **Simple Agent** - it's already built for you. You'll see three boxes connected in a
   line: **Input → Assistant → Output**.
3. Scroll down to the **Run** panel, type something in the input box (e.g.
   `{"query": "Hello!"}`), and click **Run**.
4. Watch the boxes light up one at a time as it runs, then click the finished run to see the
   **trace** - a step-by-step record of what happened, how long each step took, and what it cost
   (usually $0, see below).

That's the whole loop: build → run → see what happened. Everything else in the app is a way to
build more interesting flows, or understand what a run actually did.

## Every node type, in one sentence each

The left sidebar of the canvas lists every kind of box you can drag in. Here's what each one
actually does, without the technical description:

| Node | What it does, plainly |
|---|---|
| **Input** | Where a run's information comes in. Every flow starts with exactly one of these. |
| **Output** | What the flow hands back when it's done. Every flow ends with at least one. |
| **Agent** | Calls an AI model with instructions, like "you are a helpful support agent." Can also use tools. This is the node you'll use most. |
| **LLM** | A raw, no-frills call to an AI model - no instructions or tool use, just "take this text, get a reply." Useful for simple one-off tasks. |
| **Router** | A fork in the road - sends the flow down one of several paths depending on a rule (or lets an AI model pick the path). |
| **Supervisor** | Delegates the work to one of several specialist agents, picking whichever fits the request best. |
| **Tool** | Calls a plain function - a calculator, a web request, the current date/time - no AI model involved. |
| **MCP** | Calls a tool that lives on an external server, over a standard protocol other AI tools also speak. |
| **RAG** | Looks up relevant snippets from a knowledge base you've uploaded, so the agent can answer from *your* documents instead of guessing. |
| **Memory** | Remembers earlier messages (or facts) across runs, so a conversation doesn't start from zero every time. |
| **Human Approval** | Pauses the flow and waits for a real person to click Approve or Reject before continuing. |
| **Guardrail** | Checks content for problems - personal information, banned words - before letting it through. |

You don't need to memorize this. Every node's card in the sidebar already shows this same
one-liner, and every node you drag onto the canvas shows a form on the right for configuring it.

## There's already one example flow for every node type

You don't have to build from a blank canvas to learn. Open **Flows** and you'll find a working,
already-connected example for *every single node type* above - click one, read its description,
click **Run**, and watch it actually work:

| Flow | What it teaches |
|---|---|
| Simple Agent | The basic shape: Input → Agent → Output |
| Calculator Tool | A Tool node doing arithmetic, no AI involved |
| Raw LLM Call | The difference between an LLM node and an Agent node |
| Customer Support Router | A Router node picking between two specialist agents |
| Supervisor Multi-Agent | A Supervisor delegating to sub-agents |
| Refund Approval | A Human Approval node pausing for a real decision |
| Guardrail Demo | A Guardrail node blocking a message before it reaches the agent |
| Conversation Memory | A Memory node remembering earlier messages - run it two or three times |
| RAG Q&A | A RAG node answering questions from an uploaded document |
| MCP Tool Call | An MCP node calling a tool on an external server |

Every one of these actually runs - there's nothing faked or "coming soon" among them. Poke at
them, break them, duplicate one and change it. That's the fastest way to understand the platform.

## About "models" - the AI brains

Every Agent, LLM, Router, and Supervisor node needs to know which AI model to use. By default,
every new node uses **`default`**, which is a free, offline stand-in model built into the app - it
doesn't call the real internet or cost anything, which is why the whole app (including every
example flow above) works the moment you install it, with nothing to sign up for. Its answers are
simple and repeat the same pattern every time - good enough to prove a flow's wiring is correct,
not good enough for real answers.

To get real answers, connect a real model:

1. Open **Models** in the sidebar. You'll see a row of provider cards - OpenAI, Anthropic,
   Gemini, OpenRouter, Ollama, and others.
2. Click one. **If you don't have an API key for anything yet, click OpenRouter** - it's the
   easiest starting point because a single free account gives you access to hundreds of models,
   including several that cost nothing to use, and the form will show you live suggestions of
   which ones are free the moment you open it.
3. Give it a short **key** (like `fast` or `smart` - this is just the name you'll pick from later,
   not a password), search for or type the model you want, paste in your API key, and save.
4. Go back to any flow, click an Agent (or LLM/Router/Supervisor) node, and pick your new model
   from its **Model** dropdown instead of `default`.

You never *have* to do this - the app is fully usable, and every example above fully runs, without
it. It just means the answers you get back are real instead of the offline stand-in's canned
pattern.

## Where the rest of the app fits in

Once the basics click, here's what the other sidebar pages are for, in plain terms:

- **Runs** - every execution of every flow, in one list, so you don't have to remember which flow
  you tested last.
- **Evaluations** - instead of testing a flow by hand one message at a time, upload a list of
  sample questions (and, optionally, what a good answer looks like), and run the whole list
  through a flow at once to see a pass/fail score.
- **Knowledge** - where you upload documents for a RAG node to search through. Paste text or
  upload a file (text, markdown, or PDF).
- **MCP Servers** - where you register external tool servers so an MCP node can call them.
- **Settings** - a simple safety switch (block specific tools workspace-wide) and a log of who did
  what and when.

## If something goes wrong

Click into any run and open its **trace** - it shows exactly which node failed and why, in plain
language, not a stack trace. If a Guardrail blocked something, it tells you which check caught it.
If a model call failed, it tells you the model wasn't configured or the request failed, not a
cryptic error code.

## One honest caveat

This guide describes what the app actually does today, verified by actually running every example
listed above - nothing here is aspirational. If a feature is still a placeholder (a few settings
under **Settings**, for instance), the page itself says so plainly rather than pretending to work.
