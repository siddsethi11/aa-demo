# Kong Agent + MCP Demo

This repo is a simple Konnect hybrid demo for showing how Kong governs both agent-to-agent traffic and MCP tool traffic.

## What the project does

This project demonstrates a small, visually clear agent system running behind Kong in Konnect hybrid mode.

The demo uses:

- 1 LangGraph orchestrator
- 2 LangGraph sub-agents
- an orchestrator LLM step for triage and executive synthesis
- LLM calls from the orchestrator and sub-agents routed through Kong AI Proxy Advanced
- separate Kong AI routes for orchestrator and sub-agents
- 1 backing REST API
- Kong's `ai-mcp-proxy` plugin to expose that API as MCP tools
- Consumers and Consumer Groups to control which agent can see which tools
- a lightweight UI that shows the flow in real time

The business scenario is a simple customer escalation:

- a customer is at risk of not renewing
- they report a billing problem
- they also report a product issue
- the system needs to produce an executive escalation brief quickly

The point of the demo is to show that Kong sits in the middle of every important hop:

- UI to orchestrator
- orchestrator to MCP tools
- orchestrator to sub-agents
- sub-agents to MCP tools

This makes Kong's role easy to explain:

- route control
- authentication
- tool exposure through MCP
- LLM routing through AI Proxy Advanced
- per-agent tool restrictions
- observability of agent traffic

## What it will show

- 1 orchestrator agent
- 2 sub-agents
- 1 backing REST API exposed as MCP tools through Kong's `ai-mcp-proxy`
- per-agent tool visibility enforced with Consumers and Consumer Groups
- LangGraph-based deterministic agent workflows
- an orchestrator LLM call for planning and synthesis
- a lightweight UI that visualizes the request flow

## Runtime shape

- `ui`: starts the demo and shows the trace
- `orchestrator`: receives the play request and coordinates the run
- `support-agent`: handles product and runbook investigation
- `success-agent`: handles customer follow-up and action items
- `mock-api`: backing REST API for the 7 tools
- `ai-llm-service`: LLM traffic routed through Kong AI Proxy Advanced
- `kong-dp`: Kong Gateway `3.13.0.1` in Konnect hybrid mode

## Routes

- `/orchestrator`
- `/support-agent`
- `/success-agent`
- `/api`
- `/mock-mcp`
- `/ai`
- `/ai/orchestrator/chat/completions`
- `/ai/subagent/chat/completions`

The UI is also intended to be hosted through Kong, so the full demo can be reached from the same gateway entrypoint instead of exposing the UI separately.

`/mock-mcp` is the important route for the demo. Kong fronts the REST API and exposes it as MCP tools using the `ai-mcp-proxy` plugin.
The AI routes are split by caller type:

- `/ai/orchestrator/chat/completions`
  - used only by the orchestrator
  - primary target: `gpt-4o-mini`
  - secondary failover target: `gemini-2.5-flash`
- `/ai/subagent/chat/completions`
  - used by both sub-agents
  - target: `gemini-2.5-flash`

The services use OpenAI-compatible clients pointed at those Kong routes, and Kong forwards the requests using the AI Proxy Advanced plugin.

## What happens when Play is pressed

When the user presses `Play` in the UI, the following flow happens:

1. The UI sends a single request to the orchestrator through Kong.
2. The orchestrator starts a LangGraph workflow and emits live trace events.
3. The orchestrator calls Kong's MCP endpoint on `/mock-mcp`.
4. Through Kong, the orchestrator lists only the MCP tools it is allowed to access:
   - `get_customer_account`
   - `get_renewal_risk`
   - `get_open_tickets`
5. The orchestrator gathers account context using those tools:
   - customer account details
   - renewal risk
   - open support tickets
6. The orchestrator creates an executive triage brief using the orchestrator AI route in Kong.
7. The orchestrator sends that triage brief to both sub-agents as shared escalation context.
8. The orchestrator invokes the `support-agent` through Kong using explicit HTTP JSON-RPC.
9. The support agent starts its own LangGraph workflow and calls only its allowed MCP tools through Kong:
   - `get_incident_status`
   - `search_runbook`
10. The support agent also makes its own LLM call through the sub-agent AI route in Kong to turn the incident and runbook findings into a concise technical summary.
11. The support agent returns a structured technical response to the orchestrator through Kong.
12. The orchestrator uses that support output as context and then invokes the `success-agent` through Kong.
13. The success agent starts its own LangGraph workflow and calls only its allowed MCP tools through Kong:
   - `draft_customer_reply`
   - `create_followup_task`
14. The success agent also makes its own LLM call through the sub-agent AI route in Kong to turn the drafted reply and follow-up task into a concise customer-success summary.
15. The success agent returns a structured customer-success output to the orchestrator through Kong.
16. The orchestrator makes a second LLM call through the orchestrator AI route in Kong to turn the gathered context into an executive brief.
17. The orchestrator merges both tracks into one final recommendation.
18. The UI shows:
   - live node state changes
   - event log updates
   - the final coordinated response

In short: one button press creates a full end-to-end run where LangGraph controls the workflow and Kong controls the network path and tool visibility.

## Data flow

The data flow is explicit and easy to narrate.

### 1. Input data from the UI

The UI sends a single request to the orchestrator containing:

- `customer_id`
- `account_name`
- `issue_summary`
- `product_issue`
- `billing_issue`
- `incident_id`

This is the starting payload for the full run.

### 2. The orchestrator enriches that input with account context

The orchestrator uses its MCP tools through Kong to fetch structured records:

- `get_customer_account`
  - account metadata such as name, segment, ARR, renewal date, and health state
- `get_renewal_risk`
  - current renewal risk level and drivers
- `get_open_tickets`
  - currently open tickets tied to the customer

This turns the original UI request into a richer working context.

### 3. The orchestrator converts the raw context into a triage brief

The orchestrator sends the gathered context to Kong's orchestrator AI route and gets back a triage brief.

That brief is a concise narrative of:

- the current situation
- the likely next actions
- the customer communication posture

This triage brief is then passed to both sub-agents so they start from the same framing.

### 4. Data sent to the support sub-agent

The orchestrator sends the support sub-agent:

- `customer_id`
- `account_name`
- `product_issue`
- `incident_id`
- `triage_brief`

The support sub-agent uses:

- the operational identifiers to fetch technical evidence
- the triage brief to understand the escalation context

The support sub-agent then calls only:

- `get_incident_status`
- `search_runbook`

It also makes one LLM call through Kong's sub-agent AI route to convert the incident and runbook findings into a concise technical summary.

It returns:

- `triage_brief`
- `available_tools`
- `incident`
- `runbook`
- `technical_response`
- `recommended_actions`

### 5. Data sent to the success sub-agent

After support returns, the orchestrator sends the success sub-agent:

- `account_name`
- `csm`
- `issue_summary`
  - currently the triage brief summary
- `renewal_risk`
- `technical_summary`
  - derived from the support agent output
- `triage_brief`

The success sub-agent uses:

- the triage brief as shared executive framing
- the support technical summary as the technical basis for customer communication

The success sub-agent then calls only:

- `draft_customer_reply`
- `create_followup_task`

It also makes one LLM call through Kong's sub-agent AI route to turn those results into a concise customer-success summary.

It returns:

- `triage_brief`
- `available_tools`
- `customer_reply`
- `followup_task`
- `success_plan`

### 6. Final data assembly in the orchestrator

The orchestrator then holds:

- the original UI request
- the MCP-fetched account context
- the triage brief
- the support agent output
- the success agent output

It sends that combined package to Kong's orchestrator AI route one more time to produce the final executive brief.

That final payload is what the UI renders.

## Demo reference

### API keys used in the demo

These are the demo consumer keys currently configured in the repo:

- `ui-demo-key`
  - used by the hosted UI when it calls the orchestrator and subscribes to `/orchestrator/trace`
- `orchestrator-demo-key`
  - used by the orchestrator when it calls:
    - `/mock-mcp`
    - `/support-agent`
    - `/success-agent`
    - `/ai/orchestrator/chat/completions`
- `support-demo-key`
  - used by the support sub-agent when it calls:
    - `/mock-mcp`
    - `/ai/subagent/chat/completions`
- `success-demo-key`
  - used by the success sub-agent when it calls:
    - `/mock-mcp`
    - `/ai/subagent/chat/completions`

The Kong Consumers for these keys are defined in [kong/deck/kong.yaml](/Users/surajpillai/Documents/work/demos/learn/aa-demo/kong/deck/kong.yaml).

### Scene input values

The demo scene currently accepts these fields:

- `customer_id`
- `account_name`
- `issue_summary`
- `product_issue`
- `billing_issue`
- `incident_id`

The current default values in the UI are:

- `customer_id = cust_acme`
- `account_name = Acme Health`
- `issue_summary = Customer reports a billing dispute and workflow-agent sync delays.`
- `product_issue = workflow agent sync delays`
- `billing_issue = billing overcharge on enterprise add-ons`
- `incident_id = INC-1007`

These are defined in [ui/index.html](/Users/surajpillai/Documents/work/demos/learn/aa-demo/ui/index.html) and in the `PlayRequest` model in [services/orchestrator/app.py](/Users/surajpillai/Documents/work/demos/learn/aa-demo/services/orchestrator/app.py).

### Final output

The final output is created by the orchestrator in the `finalize_response` step in [services/orchestrator/app.py](/Users/surajpillai/Documents/work/demos/learn/aa-demo/services/orchestrator/app.py).

It is built from:

- the original UI request
- MCP-fetched account context
- the orchestrator triage brief
- the support sub-agent result
- the success sub-agent result
- the final orchestrator executive-summary LLM call

The final response object contains:

- `headline`
- `available_tools`
- `account_context`
- `renewal_risk`
- `open_tickets`
- `triage_brief`
- `support_track`
- `success_track`
- `executive_brief`
- `recommended_summary`

So the orchestrator is the component that creates the final answer, and it does so after it has gathered tool results and both sub-agent outputs through Kong.

## Agent responsibilities

### Orchestrator

The orchestrator is responsible for:

- receiving the request from the UI
- gathering account context from MCP tools through Kong
- creating the triage brief through the orchestrator AI route in Kong
- passing the triage brief to both sub-agents
- calling the support agent first
- calling the success agent with support output
- creating the final executive brief through the orchestrator AI route in Kong
- streaming live trace events

The orchestrator coordinates. It does not do deep technical investigation or customer action planning directly.

### Support sub-agent

The support sub-agent is responsible for:

- technical investigation of the escalation
- checking the incident status
- checking relevant runbook guidance
- creating an LLM-based technical summary through Kong's sub-agent AI route
- producing the technical response and recommended technical actions

It turns raw incident data into technical guidance for the orchestrator.

### Success sub-agent

The success sub-agent is responsible for:

- customer-facing follow-up planning
- drafting the customer reply
- creating the success-team follow-up task
- creating an LLM-based customer-success summary through Kong's sub-agent AI route
- keeping the customer response aligned with the technical response from support

It turns the technical findings plus the triage framing into a customer-ready action plan.

## Implemented services

- [UI](/Users/surajpillai/Documents/work/demos/learn/aa-demo/ui/index.html): static single-screen demo UI with `Play`, `Reset`, live flow states, and event log
- [orchestrator](/Users/surajpillai/Documents/work/demos/learn/aa-demo/services/orchestrator/app.py): receives `POST /play`, exposes `WS /trace`, calls MCP through Kong, invokes the support-agent first, then invokes the success-agent with support context
- [orchestrator LLM helper](/Users/surajpillai/Documents/work/demos/learn/aa-demo/services/common/llm.py): shared OpenAI-compatible client used by the orchestrator and sub-agents, pointed at Kong's `/ai` route
- [support-agent](/Users/surajpillai/Documents/work/demos/learn/aa-demo/services/support_agent/app.py): LangGraph sub-agent for technical investigation using `get_incident_status` and `search_runbook`
- [success-agent](/Users/surajpillai/Documents/work/demos/learn/aa-demo/services/success_agent/app.py): LangGraph sub-agent for customer-success actions using `draft_customer_reply` and `create_followup_task`
- [mock-api](/Users/surajpillai/Documents/work/demos/learn/aa-demo/services/mock_api/app.py): backing REST API for the 7 tool endpoints plus OpenAPI schema
- [shared MCP client](/Users/surajpillai/Documents/work/demos/learn/aa-demo/services/common/mcp_client.py): lightweight streamable HTTP MCP client for the agents

## Tool access model

- `orchestrator-agent`
  - `get_customer_account`
  - `get_renewal_risk`
  - `get_open_tickets`
- `support-agent`
  - `get_incident_status`
  - `search_runbook`
- `success-agent`
  - `draft_customer_reply`
  - `create_followup_task`

This tool split will be enforced by Kong with authenticated Consumers and Consumer Group based ACL rules inside the MCP proxy configuration.

## Files added in this scaffold

- `docker-compose.yml`: local container topology
- `.env.example`: hybrid mode environment placeholders
- `.env`: local placeholder values so the compose file resolves
- `kong/deck/kong.yaml`: Konnect-managed services, routes, auth, Consumers, and MCP config skeleton
- `services/`: working FastAPI services and shared helper code
- `ui/`: static frontend assets and container

## Prerequisites

- Docker and Docker Compose
- `deck`
- a Konnect personal access token
- a Konnect control plane name
- Konnect hybrid data plane certificates
- an OpenAI API key
- a Gemini API key

## Quick Start

Run the following commands from the repo root.

### 1. Create the env file

```bash
cp .env.example .env
```

### 2. Edit `.env`

Set all required values in `.env`:

```bash
KONG_CLUSTER_CONTROL_PLANE=YOUR_KONNECT_CP_HOST:443
KONG_CLUSTER_SERVER_NAME=YOUR_KONNECT_CP_HOST
KONG_CLUSTER_TELEMETRY_ENDPOINT=YOUR_KONNECT_TELEMETRY_HOST:443
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
DECK_OPENAI_API_KEY=YOUR_OPENAI_API_KEY
DECK_GEMINI_API_KEY=YOUR_GEMINI_API_KEY
DECK_OPENAI_MODEL=gpt-4o-mini
DECK_GEMINI_MODEL=gemini-2.5-flash
KONNECT_TOKEN=YOUR_KONNECT_PAT
KONNECT_CONTROL_PLANE_NAME=YOUR_KONNECT_CONTROL_PLANE_NAME
```

### 3. Place the hybrid certs

```bash
mkdir -p kong/certs
```

Put your Konnect data plane cert and key here:

```text
kong/certs/tls.crt
kong/certs/tls.key
```

### 4. Export the env vars for decK

Load the values from `.env` into the current shell before running `deck`:

```bash
set -a
source .env
set +a
```

`set -a` tells the shell to automatically export variables that are defined or loaded after that point.
`set +a` turns that behavior back off.

### 5. Validate the Kong config

```bash
deck file validate kong/deck/kong.yaml
```

### 6. Sync the Kong config to Konnect

```bash
deck gateway sync \
  --konnect-token "$KONNECT_TOKEN" \
  --konnect-control-plane-name "$KONNECT_CONTROL_PLANE_NAME" \
  kong/deck/kong.yaml
```

### 7. Start the stack

```bash
docker compose up --build -d
```

### 8. Verify the containers

```bash
docker compose ps
```

### 9. Open the hosted UI

After the hybrid data plane connects and the Kong config is synced, open:

```text
http://localhost:8000/
```

This is the intended demo entrypoint.

The UI is hosted through Kong and uses the same gateway for:

- `/orchestrator`
- `/orchestrator/trace`
- `/mock-mcp`
- `/ai/orchestrator/chat/completions`
- `/ai/subagent/chat/completions`

### Optional: direct UI container access for debugging

If you want to verify only the static UI container, you can open:

```text
http://localhost:3000/
```

That is only for debugging. The real demo path should be through Kong on port `8000`.

## Useful Commands

Validate Kong config:

```bash
deck file validate kong/deck/kong.yaml
```

Sync Kong config again:

```bash
deck gateway sync \
  --konnect-token "$KONNECT_TOKEN" \
  --konnect-control-plane-name "$KONNECT_CONTROL_PLANE_NAME" \
  kong/deck/kong.yaml
```

Start or rebuild the stack:

```bash
docker compose up --build -d
```

Check container status:

```bash
docker compose ps
```

Follow logs:

```bash
docker compose logs -f
```

Stop the stack:

```bash
docker compose down
```

## Notes

- The demo is intentionally simple and deterministic.
- The backing API is the source of truth for tool definitions.
- Kong is the only public entry point for agent and MCP traffic.
- `docker compose config` now resolves locally with placeholder `.env` values.
- `deck file validate kong/deck/kong.yaml` passes offline validation.
- service dependencies now include `langgraph` and `openai`, but I did not run a live service boot locally because the workspace Python environment does not have the app dependencies installed outside Docker.
- live Konnect validation and sync still require your real Konnect control plane name, token, and hybrid certificates.
