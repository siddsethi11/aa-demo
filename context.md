# Simplified Agentic Data Path Demo Context

## Goal

Create a new project that demonstrates a simplified version of this repo:

- 1 orchestrator agent
- 2 sub-agents
- 1 MCP server exposing 7 tools total
- Kong in the middle of agent-to-agent and agent-to-tool communication
- A lightweight UI that can start the demo and visualize request/response flow in real time

The project should be easy to explain live, easy to reset, and visually clear enough that someone can understand the full data path in a few seconds.

This design intentionally incorporates a few lessons from the current repo:

- demo scenes should be selectable in the UI, because the current repo's scenes are documented in `Kong-Demo-Scenes.md` but are not exposed as a real scene selector
- A2A should remain explicit HTTP JSON-RPC over Kong, because LangGraph should control orchestration, not transport
- event-window semantics should be visible in the UI, because the current repo uses a rolling 60-second window rather than one-time queue draining
- Kong auth and MCP routing should be obvious in both the architecture and the UI, because those are central to the demo story

## Core Outcome

When a user clicks `Play` in the UI:

1. The orchestrator receives a single request.
2. The orchestrator performs initial reasoning.
3. The orchestrator calls both sub-agents.
4. Each agent uses only the MCP tools it is allowed to access.
5. All agent and MCP traffic passes through Kong.
6. The UI renders the full trace like a simplified LangSmith or Langfuse run view:
   - nodes for agents and tool calls
   - live status updates
   - animated arrows for request and response flows
   - timing and success/failure states

## Proposed Demo Scenario

Use a very simple, business-friendly scenario:

**Scenario:** "Customer Escalation Triage"

A SaaS company receives a high-priority escalation from a customer:

- The customer is threatening not to renew
- They are reporting a billing issue and a product issue
- The team wants a coordinated action plan quickly

The orchestrator breaks the problem into two tracks:

- **Support Sub-Agent**
  - investigates product issue details
  - checks incident/runbook knowledge
  - drafts a technical response

- **Success Sub-Agent**
  - checks account health / renewal context
  - drafts customer-facing follow-up

The orchestrator then merges both outputs into one final recommended response.

This scene is simple, easy to narrate, and clearly justifies two sub-agents.

## Agent Topology

There are 3 agents total:

1. **Orchestrator Agent**
   - entrypoint for the demo
   - receives the initial user request
   - performs initial classification/planning
   - calls the two sub-agents
   - synthesizes the final answer

2. **Support Sub-Agent**
   - focused on technical investigation
   - uses only its allowed MCP tools

3. **Success Sub-Agent**
   - focused on customer/account communication
   - uses only its allowed MCP tools

The orchestrator should call sub-agents deterministically, not leave that decision entirely to an LLM tool loop. This keeps the demo reliable and predictable.

## MCP Server Design

Use one MCP server with 7 tools. The tools can be fake or backed by static/mock data, but they should return realistic structured responses.

### Tool Set

Suggested 7 tools:

1. `get_customer_account`
2. `get_renewal_risk`
3. `get_open_tickets`
4. `get_incident_status`
5. `search_runbook`
6. `draft_customer_reply`
7. `create_followup_task`

### Tool Access Split

Distribute access by Kong consumer / ACL so each agent only sees its allowed tools:

- **Orchestrator Agent**: 3 tools
  - `get_customer_account`
  - `get_renewal_risk`
  - `get_open_tickets`

- **Support Sub-Agent**: 2 tools
  - `get_incident_status`
  - `search_runbook`

- **Success Sub-Agent**: 2 tools
  - `draft_customer_reply`
  - `create_followup_task`

This gives a clean 3 / 2 / 2 split across 7 tools.

## Kong’s Role

Kong should sit in front of both:

- **A2A communication**
  - Orchestrator -> Support Sub-Agent
  - Orchestrator -> Success Sub-Agent

- **MCP communication**
  - Orchestrator -> MCP server
  - Support Sub-Agent -> MCP server
  - Success Sub-Agent -> MCP server

The key demo point is that Kong governs every hop:

- routing
- auth
- per-agent tool visibility
- observability
- agent authentication
- agent rate limiting
- policy enforcement

If AI Gateway is used for LLM traffic as well, keep that explicit in the architecture:

- agents call LLMs through Kong AI Gateway
- agents call MCP tools through Kong Gateway with MCP proxy support
- agent-to-agent calls also go through Kong routes

### MCP Routing Pattern

Match the current repo's Kong pattern:

- expose MCP on a dedicated Kong route such as `/mock-mcp`
- protect that route with `key-auth` using the `apikey` header
- apply per-tool ACLs inside the MCP proxy configuration
- keep the backing REST API reachable through Kong as well

This matters because in the current repo the MCP tools resolve to Kong-managed backend paths, not to a direct out-of-band API path.

## A2A Implementation Pattern

The simplified project should use the same practical A2A pattern as this repo:

- orchestration decides when another agent should run
- the actual agent-to-agent call is an explicit HTTP JSON-RPC request
- the request goes through Kong

### Important Design Choice

Do not depend on a framework-specific A2A abstraction.

Use the orchestration layer only to decide:

- when to invoke a sub-agent
- what context to send
- how to handle the returned result

Then send the A2A request explicitly with HTTP to the sub-agent's JSON-RPC endpoint through Kong.

This is easier to explain, easier to debug, and easier to visualize in the UI.
It also makes it clear that the orchestration framework is choosing when to call, while plain HTTP JSON-RPC performs the actual A2A transport.

### Agent Discovery

Each sub-agent should expose an agent card at:

- `GET /.well-known/agent.json`

The orchestrator should know a small set of Kong route prefixes, for example:

- `/support-agent`
- `/success-agent`

For each route, it should fetch:

- `/support-agent/.well-known/agent.json`
- `/success-agent/.well-known/agent.json`

The returned card should contain:

- `agent_id`
- `name`
- `description`
- `endpoints.jsonrpc`

The orchestrator should then build the callable endpoint as:

- `<kong-url><route-prefix><jsonrpc-endpoint>`

Example:

- `http://kong:8000/support-agent/v1/jsonrpc`

### Required A2A Endpoints

Each sub-agent should expose:

- `GET /.well-known/agent.json`
- `POST /v1/jsonrpc`
- `GET /health`

Recommended agent card shape:

```json
{
  "schema_version": "v1",
  "agent_id": "support-agent",
  "name": "Support Agent",
  "description": "Handles technical investigation tasks.",
  "endpoints": {
    "jsonrpc": "/v1/jsonrpc"
  }
}
```

### JSON-RPC Request Shape

The orchestrator should send A2A messages as JSON-RPC 2.0 requests.

Recommended request:

```json
{
  "jsonrpc": "2.0",
  "method": "a2a_sendMessage",
  "params": {
    "message": "context for the sub-agent"
  },
  "id": 1
}
```

The `message` field can be plain text for the first version. Keep it simple and deterministic.
This mirrors the current repo, where cross-agent context is passed as plain text in `params.message`.

### JSON-RPC Response Shape

Each sub-agent should return a structured result in the JSON-RPC `result` field.

Recommended response:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "success": true,
    "output": "final sub-agent answer",
    "tool_calls": [
      {
        "tool": "search_runbook",
        "args": {
          "query": "billing mismatch"
        }
      }
    ],
    "agent": "support_agent"
  },
  "id": 1
}
```

This response shape is useful because:

- the orchestrator can reason over `success`
- the UI can render `tool_calls`
- the final output remains easy to display

`tool_calls` should contain the tool name plus the arguments used, for example `{"tool": "search_runbook", "args": {...}}`. Do not rely on it to contain full raw tool responses.

### Message Passing Model

Data should not pass directly between sub-agents.

Use this pattern:

1. Orchestrator gathers context.
2. Orchestrator builds a message string for Support Agent.
3. Orchestrator sends A2A request through Kong.
4. Support Agent returns structured output.
5. Orchestrator builds a message string for Success Agent.
6. Orchestrator sends A2A request through Kong.
7. Success Agent returns structured output.
8. Orchestrator synthesizes the final answer.

This makes the orchestrator the hub for all cross-agent data flow.

### Orchestration Layer Integration

If you use LangGraph, use it the same way as this repo:

- graph nodes decide when sub-agents run
- the node implementation performs the HTTP JSON-RPC call

If you do not use LangGraph, the same pattern still applies:

- normal async functions can call the sub-agents directly

The important point is that A2A transport remains explicit and visible.

### Kong Routing For A2A

Kong should expose separate routes for each sub-agent, for example:

- `/support-agent`
- `/success-agent`

Kong should enforce:

- `key-auth`
- optional rate limiting
- logging/observability

This means all A2A traffic is:

- authenticated
- observable
- controllable for demos

### UI Expectations For A2A

The UI should render each A2A hop explicitly.

At minimum, show:

- Orchestrator -> Kong -> Support Agent
- Support Agent -> Kong -> Orchestrator
- Orchestrator -> Kong -> Success Agent
- Success Agent -> Kong -> Orchestrator

If a failure mode is selected, the A2A trace should show whether the failure happened:

- before auth
- at auth
- at rate limiting
- at the sub-agent itself

## Security And Policy Requirements

The simplified demo should explicitly show that agents are not talking to each other or to tools directly. Kong should enforce identity and policy on every hop.

### Agent Authentication

Use Kong `key-auth` for:

- dashboard -> orchestrator
- orchestrator -> support-agent
- orchestrator -> success-agent
- each agent -> MCP server

Each caller should have its own credential:

- dashboard key
- orchestrator key
- support-agent key
- success-agent key

This should make it easy to explain:

- every agent is a distinct Kong consumer
- each consumer has its own API key
- Kong identifies who is calling before allowing access

### Agent Rate Limiting

Add rate limiting to the simplified demo so you can show that Kong can protect both agents and tools from abuse or runaway loops.

Suggested policy:

- dashboard -> orchestrator: moderate limit
- orchestrator -> sub-agents: moderate limit
- agents -> MCP server: tighter per-agent limits

This does not need to be aggressive in the default happy path, but it should be configurable so the demo can optionally show:

- an agent hitting a limit
- Kong returning a rate-limit response
- the UI showing the failed span clearly

### Per-Agent Tool Authorization

Tool access should be enforced by Kong, not only by prompt instructions.

The demo should make it obvious that:

- the orchestrator only sees its 3 tools
- support-agent only sees its 2 tools
- success-agent only sees its 2 tools

If possible, include one optional demo mode where an agent attempts to call a tool it is not allowed to use and Kong denies access.

## Failure Simulation

The simplified project should include the same failure simulation idea used in this repo.

### LLM Failure Simulator

Add a dedicated Kong route such as:

- `/llm-failure-simulator`

Back it with a `request-termination` plugin that immediately returns a controlled failure such as:

- HTTP `503`
- message like `Simulated primary LLM outage`

### How It Should Work

The AI Gateway model configuration should support switching one primary LLM target to the simulator route instead of the real provider.

That means the demo can:

1. point the primary model target at the failure simulator
2. re-apply Kong config
3. run the exact same demo again
4. show that Kong fails over to the fallback model automatically

### Why This Matters

This makes the failover story visible and repeatable:

- the app code does not change
- the agent prompts do not change
- only Kong configuration changes
- the UI trace should show the failed LLM call and the successful fallback call

### UI Expectations For Failure Demo

When failure simulation is enabled, the UI should clearly show:

- the failed primary LLM request
- the fallback request
- success after retry/failover
- timing difference between failed and successful attempts

This is a strong demo moment because it shows resilience, not just routing.

## Simplified Architecture

### Components

- `orchestrator` service
- `support-agent` service
- `success-agent` service
- `mcp-server` service
- `kong` service
- `dashboard` service

### Data Flow

1. User clicks `Play` in the dashboard.
2. Dashboard calls orchestrator via Kong.
3. Orchestrator starts a trace/run.
4. Orchestrator calls the LLM through Kong AI Gateway.
5. Orchestrator calls its allowed MCP tools through Kong.
6. Orchestrator invokes Support Sub-Agent through Kong using key-auth.
7. Support Sub-Agent calls the LLM through Kong AI Gateway.
8. Support Sub-Agent calls its MCP tools through Kong.
9. Orchestrator invokes Success Sub-Agent through Kong using key-auth.
10. Success Sub-Agent calls the LLM through Kong AI Gateway.
11. Success Sub-Agent calls its MCP tools through Kong.
12. Sub-agents return results to orchestrator through Kong.
13. Orchestrator synthesizes the final response.
14. Dashboard displays the final output plus the full execution trace.

## UI Requirements

The UI is a core part of the demo, not an afterthought.
It should use animation intentionally so a presenter can explain the flow by following motion on the screen.

### Visual Direction

The UI should look close in spirit to the reference image:

- dark "control room" aesthetic
- large network/data-path canvas as the visual centerpiece
- execution logs in a dedicated left panel
- live feed or event stream in a lower left panel
- top status bar with run-state chips and health indicators
- glowing active nodes and color-coded animated paths

The target feel is:

- polished demo environment
- operational visibility
- easy to narrate on a live call

It should not look like a generic admin table or a default analytics dashboard.

### Main Interaction

The homepage should have:

- a clear title and one-sentence explanation
- a single `Play Demo` button
- an optional `Reset` button
- a feature selector / scenario control panel
- a visible system diagram / flow view
- a trace panel showing chronological events

Recommended page structure, based on the reference:

- **Top bar**
  - product/demo logo
  - current run status chips such as `Analyzing`, `Calling Agents`, `Compiling Results`
  - lightweight health indicators for key systems
  - presenter identity / avatar area if useful

- **Left rail**
  - `Execution Logs` panel showing chronological spans
  - `Live Event Stream` or `Sentiment/Event Feed` panel for incoming stimuli

- **Main canvas**
  - `Agent Data Path` network view with animated edges and highlighted nodes

- **Optional right/overlay detail**
  - selected node or trace details

### Animation Principles

Animation should be explanatory, not decorative.

It should make these things obvious:

- what started
- what is active now
- where the request is going
- where the response returned
- what failed
- what retried or failed over

The presenter should be able to narrate the system just by following the animated flow.
The visual hierarchy should make the active path impossible to miss.

### Demo Feature Controls

The UI should be able to simulate demo features directly, without requiring manual edits to Kong config files during the presentation.
This is a deliberate improvement over the current repo, where scenes are run manually from the playbook instead of being selected from the dashboard.

Before pressing `Play Demo`, the user should be able to choose one mode or a small combination of modes such as:

- `Happy Path`
- `LLM Failover`
- `Agent Auth Failure`
- `Rate Limit Triggered`
- `Tool Access Denied`

This control should be simple and demo-friendly:

- segmented control, cards, or toggles
- obvious current mode
- easy reset back to `Happy Path`

The selected mode should also influence the animation language so the audience can immediately tell whether they are watching a normal run, a failure, a failover, or a policy denial.

The control panel should feel like a demo console, not a form:

- compact chips
- segmented toggles
- obvious selected state
- minimal text density

### How UI-Driven Simulation Should Work

The UI should not directly bypass Kong. Instead, it should start a run with a selected demo profile, and the backend should apply the matching simulation behavior in a controlled way.

Possible implementation patterns:

- pass a `demo_mode` or `feature_flags` payload when starting a run
- have the orchestrator call a demo-control service
- use preconfigured Kong routes/plugins that activate based on headers, routes, or dedicated test consumers

The important constraint is:

- the simulation should still exercise Kong, not fake the result entirely in the frontend

### Recommended Demo Modes

#### Happy Path

Normal successful run:

- valid auth
- no rate limiting
- no forced failures
- all allowed tools succeed

#### LLM Failover

The UI should trigger a mode where one primary LLM target fails and Kong routes to the fallback target.

The audience should see:

- failed primary LLM span
- fallback LLM span
- successful agent completion

#### Agent Auth Failure

The UI should trigger a mode where one A2A or MCP request uses an invalid or missing credential.

The audience should see:

- Kong rejecting the request
- clear unauthorized status in the trace
- affected agent or step marked failed

#### Rate Limit Triggered

The UI should trigger a mode where a route intentionally hits a configured limit.

The audience should see:

- successful requests up to the threshold
- Kong returning the rate-limit response
- trace panel showing which call was blocked

#### Tool Access Denied

The UI should trigger a mode where an agent attempts to call a tool outside its allowed set.

The audience should see:

- the attempted tool call
- Kong denying or filtering access
- a visible policy enforcement event in the trace

### What Happens on Play

When `Play Demo` is clicked:

- the UI sends one request to start the run, including the selected demo mode
- the backend begins emitting trace events over WebSocket or Server-Sent Events
- the graph animates in real time as each request/response happens
- the currently active path should always be visually obvious

### Visualization Style

The UI should feel similar to LangSmith / Langfuse in spirit:

- each agent/tool invocation becomes a span/event
- events appear in a timeline
- selected nodes show input, output, duration, and status
- active work is highlighted
- success and failure are visually distinct
- the selected demo mode is visible throughout the run

But it should be more animated and presenter-friendly than a standard trace viewer:

- active nodes should pulse or glow
- arrows should visibly travel between nodes
- failed calls should flash or mark red immediately
- retries and failover should look different from normal success

### Color Language

Use a small, consistent semantic palette inspired by the reference:

- inference / LLM traffic: amber or gold
- A2A traffic: violet or blue-violet
- MCP/tool traffic: pink or magenta
- event/Kafka traffic: green or teal
- neutral infrastructure: charcoal, slate, muted gray

Active nodes should use a cool blue glow or a semantic glow matching the active edge type.
Avoid rainbow overload. The color system should help explanation, not compete with it.

### Graph View

The graph should include these nodes:

- User / Dashboard
- Kong Gateway
- Orchestrator
- Support Sub-Agent
- Success Sub-Agent
- MCP Server
- LLM Provider Pool or LLM node

### Dynamic Arrows

Dynamic arrows are required.

For every request/response:

- animate the request arrow from caller to callee
- animate the response arrow back to caller
- change arrow color/state while in flight
- persist completed edges briefly or show them in a subdued state
- use directional movement so the audience can clearly see who initiated the call
- use distinct animation for retry, deny, timeout, and failover cases

Examples:

- Dashboard -> Kong -> Orchestrator
- Orchestrator -> Kong -> LLM
- Orchestrator -> Kong -> MCP Server
- Orchestrator -> Kong -> Support Sub-Agent
- Support Sub-Agent -> Kong -> LLM
- Support Sub-Agent -> Kong -> MCP Server
- Orchestrator -> Kong -> Success Sub-Agent
- Success Sub-Agent -> Kong -> LLM
- Success Sub-Agent -> Kong -> MCP Server
- Sub-Agent -> Kong -> Orchestrator

The canvas should visually separate these traffic classes so the presenter can say:

- "green is event flow"
- "gold is inference"
- "pink is MCP tool traffic"
- "violet is agent-to-agent traffic"

### Node Animation

Nodes should have explicit animated states:

- `idle`
- `active`
- `waiting`
- `success`
- `failed`
- `rate_limited`
- `auth_denied`
- `failover_target`

Suggested behavior:

- `active`: pulse or glow
- `waiting`: subtle breathing animation
- `success`: quick positive flash then settled state
- `failed`: visible error flash and persistent failed styling
- `rate_limited`: warning state distinct from generic failure
- `auth_denied`: locked or denied visual treatment
- `failover_target`: highlighted as the backup path now serving traffic

### Logs And Feed Panels

Match the reference layout closely:

- `Execution Logs` should show timestamp, icon, short message, and status pill
- `Live Feed` should show incoming events as stacked cards or rows
- active log rows should animate in as they arrive
- the currently executing step should be easy to spot without reading the whole list

Use iconography aggressively but simply:

- robot/agent icon for agent steps
- tool icon for MCP calls
- cloud icon for provider calls
- alert/lock icon for auth, denial, or rate-limit events

### Event Detail Panel

Clicking a node or trace item should show:

- request payload summary
- response summary
- start time
- end time
- duration
- status
- tool name or agent name
- policy outcome if applicable, such as authenticated, rate-limited, denied, or failed over

## Recommended UX Layout

Use a 3-panel layout:

- **Top bar**
  - title
  - play/reset controls
  - overall run status

- **Left panel**
  - graph / flow visualization with animated edges

- **Right panel**
  - trace timeline and detail inspector

This layout works well for demos because the audience can watch the overall architecture and the detailed trace at the same time.
The graph panel should be the visual focal point and should always show the currently active route clearly.

The UI should prioritize legibility on shared screens:

- large enough labels
- strong contrast
- limited text per row
- no tiny unreadable panels

## Suggested Frontend Stack

- React
- TypeScript
- Vite
- Tailwind
- React Flow for graph layout and animated edges
- Zustand or React Query for state management
- WebSocket or SSE for live trace streaming
- Framer Motion or Motion for controlled node and panel transitions

React Flow is a strong fit because it already supports:

- custom nodes
- custom animated edges
- programmatic graph updates
- viewport control for demos

You should implement custom nodes and custom animated edges rather than relying on default React Flow styling. The visual quality of the nodes, glows, chips, and edge motion matters for this demo.

## Suggested Backend Behavior

The orchestrator should emit trace events for every meaningful step.
The event stream should be rich enough to drive animation deterministically, not by inference in the frontend.

### Event Types

Suggested event model:

- `run_started`
- `window_summary_generated`
- `agent_started`
- `agent_completed`
- `auth_check`
- `rate_limit_check`
- `policy_denied`
- `tool_call_started`
- `tool_call_completed`
- `a2a_request_started`
- `a2a_request_completed`
- `llm_call_started`
- `llm_call_completed`
- `llm_failover_triggered`
- `run_completed`
- `run_failed`

### Event Shape

Each event should include:

- `event_id`
- `run_id`
- `demo_mode`
- `timestamp`
- `event_type`
- `source`
- `target`
- `label`
- `status`
- `duration_ms` if completed
- `input_summary`
- `output_summary`
- `animation_hint` when useful for request, response, failure, retry, denial, or failover

If the workflow is driven by a rolling event window, also include:

- `window_seconds`
- `data_points_processed`
- `window_end`

This makes it easy for the UI to drive both:

- timeline rendering
- animated graph edges
- node state transitions

## Reliability Requirements

This demo should optimize for predictability over autonomy.

- The orchestrator should explicitly call both sub-agents.
- Tool use should be constrained by Kong policies, not just prompts.
- Agent-to-agent calls should require authentication.
- Agent and tool routes should have rate limiting configured.
- Mock data should be deterministic enough that the demo tells the same story every run.
- The trace stream should not depend on fragile parsing of model output.
- Sub-agent failures should be shown clearly in the UI instead of hidden.
- Animation should be driven from explicit backend events, not guessed in the browser.
- If using a rolling event window, the UI should show that clearly and not imply one-time queue draining.

## What To Keep Simple

Do not overbuild the first version.

- one demo scenario only
- one MCP server only
- one orchestrator and two sub-agents only
- static/mock data is fine
- one clean happy-path trace is more valuable than many branches

## Nice-to-Have Enhancements

Only add these after the basic demo works:

- replay previous runs
- speed control for the animation
- a "step mode" that advances one call at a time
- a toggle to show/hide Kong as a node
- failure injection such as one tool call timing out
- policy demos such as rate limiting or denied tool access
- multi-mode combinations if they remain easy to explain

## Suggested Repository Structure

```text
simple-agentic-demo/
  agents/
    orchestrator/
    support-agent/
    success-agent/
  mcp-server/
  kong/
    deck/
    terraform/   # optional
  dashboard/
  docker-compose.yaml
  README.md
  ARCHITECTURE.md
```

## Minimal Demo Script

A presenter should be able to say:

1. "I’m going to start a customer escalation workflow."
2. "From the UI, I can choose which capability I want to demonstrate."
3. "Kong authenticates the request before the orchestrator starts."
4. "The orchestrator receives the request and gathers account context."
5. "It delegates technical investigation to the support agent."
6. "It delegates customer communication to the success agent."
7. "Each agent only sees the MCP tools Kong allows it to use."
8. "If I choose failover, auth failure, or rate limiting, the trace shows that behavior live."
9. "The UI shows every request and response as it happens."
10. "The orchestrator combines the results into one final recommendation."

## Definition of Done

The simplified project is successful when:

- clicking `Play Demo` starts a full run end-to-end
- the UI lets the presenter select which feature or policy behavior to demonstrate
- the orchestrator and both sub-agents execute in a visible, deterministic flow
- all tool access goes through one MCP server behind Kong
- all agent-to-agent traffic goes through Kong with key authentication
- each agent sees only its assigned tools
- rate limiting is configured on agent and MCP routes
- LLM traffic can optionally fail over through a Kong-configured failure simulator
- the UI shows live animated request/response arrows
- the UI shows a trace/timeline view of the run
- the animation makes the active path easy to follow during a live explanation
- the UI makes the active demo mode and analyzed event window obvious
- the final result is easy to explain in a 2-3 minute demo

## Build Priorities

Build in this order:

1. Mock MCP server with 7 tools
2. Kong routes, key-auth, and per-agent tool restrictions
3. Orchestrator and two sub-agents
4. Rate limiting and failure-simulator wiring
5. Trace event model and backend streaming
6. UI graph with animated arrows
7. Timeline/detail panel
8. Demo polish
