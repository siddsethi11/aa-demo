# Context

## Project Summary

This repo is a Kong-governed multi-agent demo for a customer escalation workflow.

Core flow:
- UI sends a `Play` request through Kong to the orchestrator.
- Orchestrator gathers account context through MCP tools exposed by Kong.
- Orchestrator calls two sub-agents through Kong:
  - `support-agent`
  - `success-agent`
- Orchestrator produces a final executive brief through Kong-routed LLM endpoints.

Main code locations:
- `/Users/surajpillai/Documents/work/demos/learn/aa-demo/services/orchestrator/app.py`
- `/Users/surajpillai/Documents/work/demos/learn/aa-demo/services/support_agent/app.py`
- `/Users/surajpillai/Documents/work/demos/learn/aa-demo/services/success_agent/app.py`
- `/Users/surajpillai/Documents/work/demos/learn/aa-demo/services/common/llm.py`
- `/Users/surajpillai/Documents/work/demos/learn/aa-demo/services/common/mcp_client.py`
- `/Users/surajpillai/Documents/work/demos/learn/aa-demo/kong/deck/kong.yaml`
- `/Users/surajpillai/Documents/work/demos/learn/aa-demo/observability/grafana/dashboards/kong-governance-overview.json`

## Runtime Shape

Relevant services in `docker-compose.yml`:
- `orchestrator`
- `support-agent`
- `success-agent`
- `mock-api`
- `kong-dp`
- `loki`
- `grafana`
- `redis-stack`
- `ui`

Important environment wiring:
- orchestrator uses `AGENT_API_KEY=orchestrator-demo-key`
- support-agent uses `AGENT_API_KEY=support-demo-key`
- success-agent uses `AGENT_API_KEY=success-demo-key`
- orchestrator LLM base URL: `http://kong-dp:8000/ai/orchestrator`
- sub-agent LLM base URL: `http://kong-dp:8000/ai/subagent`

## Expected LLM Call Counts Per Normal Run

For a normal run:
- orchestrator should produce `5` LLM calls
  - 3 tool-selection/planner calls
  - 1 triage brief call
  - 1 executive summary call
- support-agent should produce `3` LLM calls
  - 2 tool-selection/planner calls
  - 1 technical summary call
- success-agent should produce `3` LLM calls
  - 2 tool-selection/planner calls
  - 1 success summary call

Expected per-model totals for a normal run:
- `gpt-4o-mini-2024-07-18` = `5`
- `gemini-2.5-flash` = `6`

## Grafana / Loki Findings

### Dashboard Consolidation

User wanted one dashboard instead of separate governance and run dashboards.

Current direction:
- governance dashboard now has a `Run ID` variable
- `Run ID = All` should show all labeled runs
- selecting a concrete run id should scope the governance dashboard to that run

### Cost Mismatch Root Cause

Original issue:
- governance dashboard cost panels used hardcoded `[1h]`

That caused mismatches because Grafana time range and query window did not match.

Fix applied:
- changed cost panels to use `[$__range]`

### "All Runs" Mismatch Root Cause

Another issue:
- governance dashboard originally used `run_id=~"$run_id"`
- when `Run ID = All`, Grafana expands to `.*`
- that matched blank `run_id` too

Effect:
- unlabeled traffic was included in the "All" view

Fix applied:
- added `run_id!=""` to run-scoped dashboard queries

### Average Cost Meaning

Original panel:
- `Average Cost By Agent`
- query used `avg_over_time(...)`

That was actually average cost per LLM call, not average total cost per run.

User intent:
- average agent cost across runs

Fix applied:
- panel now computes:
  - per `(consumer, run_id)` total cost
  - then average of those per-run totals by `consumer`
- title changed to `Average Cost Per Run By Agent`

## Key LLM Logging Bug We Found

This was the important debugging thread.

Observed symptom:
- `LLM Calls By Model`
- `LLM Calls By Agent And Model`
- support and success were showing `1` instead of expected `3`

Initial suspicion:
- dashboard query issue

What Loki proved:
- the missing planner calls existed
- but for earlier runs they were logged with `run=""`
- only the final sub-agent summary call had the real `run_id`

Important evidence:
- for historical run `3d4f8dd5-c303-48bf-9d03-f32c047ad507`, Loki showed:
  - `orchestrator-agent = 5`
  - `support-agent = 1`
  - `success-agent = 1`
- inspecting nearby sub-agent LLM logs showed the missing planner calls existed with blank run id

## Code Fixes Applied

### 1. Pass `run_id` into sub-agent planner calls

Fixed in:
- `/Users/surajpillai/Documents/work/demos/learn/aa-demo/services/support_agent/app.py`
- `/Users/surajpillai/Documents/work/demos/learn/aa-demo/services/success_agent/app.py`

Change:
- `llm.choose_next_tool(...)` now receives `run_id=params["run_id"]`

### 2. Replace `AsyncOpenAI` path in shared LLM client

Critical fix in:
- `/Users/surajpillai/Documents/work/demos/learn/aa-demo/services/common/llm.py`

What changed:
- `OrchestratorLLM.generate(...)` no longer uses `AsyncOpenAI`
- it now uses explicit `httpx.AsyncClient.post(...)`
- headers are set directly:
  - `apikey`
  - `content-type`
  - `x-demo-run-id`

Reason:
- planner calls were still arriving in Kong/Loki with blank `run_id`
- switching to explicit HTTP requests removed ambiguity in header propagation

### 3. Dashboard count windows

Updated:
- governance dashboard LLM count panels use `[$__range]`

## Verified Fresh Run After Fix

After rebuilding and restarting:
- `orchestrator`
- `support-agent`
- `success-agent`

I triggered a fresh run:
- `6890278c-9815-4015-ac87-eadf224c6834`

Verified in Loki:
- `orchestrator-agent -> gpt-4o-mini-2024-07-18 = 5`
- `support-agent -> gemini-2.5-flash = 3`
- `success-agent -> gemini-2.5-flash = 3`

Also verified raw sub-agent LLM log lines for that run:
- support-agent had 3 `/ai/subagent/chat/completions` entries with the correct run id
- success-agent had 3 `/ai/subagent/chat/completions` entries with the correct run id

Conclusion:
- fix is live for new runs
- old Loki data remains historically incorrect

## Historical Runs

Important note for future debugging:
- previously generated runs will still show wrong counts if their planner calls were logged without `run_id`
- Grafana cannot retroactively fix old Loki entries
- only fresh runs after the service rebuild reflect the corrected behavior

## Current Dashboard State

Governance dashboard changes currently include:
- optional `Run ID` selector
- `All` mode excludes blank `run_id`
- cost panels respect `[$__range]`
- LLM count panels respect `[$__range]`
- average cost panel means average per-run cost by agent
- ambiguous single-series tiles now force label rendering and clearer titles

## Recommended Next Checks If Work Resumes

If the next session continues from here, useful next checks are:
- confirm Grafana UI reflects the latest dashboard JSON after reload
- convert remaining token panels from fixed windows like `[1h]` or `[5m]` if exact dashboard-range parity is required everywhere
