from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field


app = FastAPI(title="Customer Escalation Mock API", version="1.0.0")


CUSTOMERS = {
    "cust_acme": {
        "customer_id": "cust_acme",
        "account_name": "Acme Health",
        "segment": "Enterprise",
        "health_score": "at_risk",
        "renewal_date": "2026-05-15",
        "csm": "Maya Patel",
        "arr": 420000,
    },
    "cust_northwind": {
        "customer_id": "cust_northwind",
        "account_name": "Northwind Logistics",
        "segment": "Mid-market",
        "health_score": "watchlist",
        "renewal_date": "2026-06-30",
        "csm": "Leo Martinez",
        "arr": 195000,
    },
    "cust_contoso": {
        "customer_id": "cust_contoso",
        "account_name": "Contoso Retail",
        "segment": "Enterprise",
        "health_score": "at_risk",
        "renewal_date": "2026-04-28",
        "csm": "Ava Thompson",
        "arr": 510000,
    },
}

RENEWAL_RISKS = {
    "cust_acme": {
        "score": 86,
        "level": "high",
        "drivers": [
            "Executive escalation within 30 days of renewal",
            "Billing dispute still open",
            "Repeated incident impact reported by customer",
        ],
    },
    "cust_northwind": {
        "score": 61,
        "level": "medium",
        "drivers": [
            "Invoice reconciliation issue open for more than 10 days",
            "Delayed connector jobs impacting finance exports",
            "Customer requested executive update before renewal review",
        ],
    },
    "cust_contoso": {
        "score": 92,
        "level": "high",
        "drivers": [
            "Duplicate usage billing reported by procurement",
            "Automation queue delay impacting customer operations",
            "Renewal discussion already escalated to VP level",
        ],
    },
}

TICKETS = {
    "cust_acme": [
        {
            "ticket_id": "TCK-4012",
            "severity": "high",
            "summary": "Billing overcharge on enterprise add-ons",
            "incident_id": "INC-1007",
            "status": "open",
        },
        {
            "ticket_id": "TCK-4018",
            "severity": "medium",
            "summary": "Workflow agents timing out during connector sync",
            "incident_id": "INC-1007",
            "status": "open",
        },
    ],
    "cust_northwind": [
        {
            "ticket_id": "TCK-5124",
            "severity": "high",
            "summary": "Invoice reconciliation mismatch on enterprise exports",
            "incident_id": "INC-2042",
            "status": "open",
        },
        {
            "ticket_id": "TCK-5129",
            "severity": "medium",
            "summary": "Connector sync backlog delaying nightly finance jobs",
            "incident_id": "INC-2042",
            "status": "open",
        },
    ],
    "cust_contoso": [
        {
            "ticket_id": "TCK-6203",
            "severity": "high",
            "summary": "Duplicate usage charges on premium connectors",
            "incident_id": "INC-3099",
            "status": "open",
        },
        {
            "ticket_id": "TCK-6208",
            "severity": "high",
            "summary": "Workflow automation queue delays during peak traffic",
            "incident_id": "INC-3099",
            "status": "open",
        },
    ],
}

INCIDENTS = {
    "INC-1007": {
        "incident_id": "INC-1007",
        "status": "identified",
        "severity": "sev2",
        "customer_impact": "Workflow agent sync jobs delayed by 3-5 minutes",
        "eta": "Patch rollout in progress, next update in 30 minutes",
    },
    "INC-2042": {
        "incident_id": "INC-2042",
        "status": "monitoring",
        "severity": "sev3",
        "customer_impact": "Connector export jobs delayed by up to 20 minutes",
        "eta": "Queue rebalance applied, monitoring for sustained recovery",
    },
    "INC-3099": {
        "incident_id": "INC-3099",
        "status": "identified",
        "severity": "sev1",
        "customer_impact": "Order automation queue stalled during peak retail traffic",
        "eta": "Mitigation in progress, executive update in 15 minutes",
    },
}

RUNBOOKS = [
    {
        "id": "RB-44",
        "title": "Workflow Connector Sync Delay",
        "summary": "Check queue depth, restart stale workers, and verify region failover state.",
    },
    {
        "id": "RB-12",
        "title": "Billing Reconciliation Escalation",
        "summary": "Confirm invoice deltas and create a finance-approved correction note.",
    },
    {
        "id": "RB-27",
        "title": "Connector Job Backlog Recovery",
        "summary": "Drain stale connector batches, rebalance workers, and verify downstream export completion.",
    },
    {
        "id": "RB-63",
        "title": "Duplicate Usage Charge Investigation",
        "summary": "Validate metering rollups, isolate duplicate connector events, and prepare a customer credit summary.",
    },
]

SCENE_PRESETS = [
    {
        "id": "acme_default",
        "label": "Acme Health",
        "customer_id": "cust_acme",
        "account_name": "Acme Health",
        "issue_summary": "Customer reports a billing dispute and workflow-agent sync delays.",
        "product_issue": "workflow agent sync delays",
        "billing_issue": "billing overcharge on enterprise add-ons",
        "incident_id": "INC-1007",
    },
    {
        "id": "northwind_exports",
        "label": "Northwind Logistics",
        "customer_id": "cust_northwind",
        "account_name": "Northwind Logistics",
        "issue_summary": "Customer reports invoice reconciliation errors and delayed connector export jobs.",
        "product_issue": "connector job backlog delaying finance exports",
        "billing_issue": "invoice reconciliation mismatch on enterprise exports",
        "incident_id": "INC-2042",
    },
    {
        "id": "contoso_peak",
        "label": "Contoso Retail",
        "customer_id": "cust_contoso",
        "account_name": "Contoso Retail",
        "issue_summary": "Customer reports duplicate usage billing and order automation queue delays during peak traffic.",
        "product_issue": "workflow automation queue delays during peak traffic",
        "billing_issue": "duplicate usage charges on premium connectors",
        "incident_id": "INC-3099",
    },
]


class DraftCustomerReplyRequest(BaseModel):
    account_name: str
    csm: str
    issue_summary: str
    renewal_risk: str
    technical_summary: str


class CreateFollowupTaskRequest(BaseModel):
    account_name: str
    owner: str
    due_date: str
    action_items: list[str] = Field(default_factory=list)


@app.get("/health", operation_id="healthcheck")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/customers/{customer_id}", operation_id="get_customer_account")
async def get_customer_account(customer_id: str) -> dict:
    return CUSTOMERS.get(customer_id, CUSTOMERS["cust_acme"])


@app.get("/customers/{customer_id}/renewal-risk", operation_id="get_renewal_risk")
async def get_renewal_risk(customer_id: str) -> dict:
    return RENEWAL_RISKS.get(customer_id, RENEWAL_RISKS["cust_acme"])


@app.get("/customers/{customer_id}/tickets", operation_id="get_open_tickets")
async def get_open_tickets(customer_id: str) -> dict[str, list[dict]]:
    return {"tickets": TICKETS.get(customer_id, TICKETS["cust_acme"])}


@app.get("/incidents/{incident_id}", operation_id="get_incident_status")
async def get_incident_status(incident_id: str) -> dict:
    return INCIDENTS.get(incident_id, INCIDENTS["INC-1007"])


@app.get("/runbooks/search", operation_id="search_runbook")
async def search_runbook(q: str = Query(..., min_length=2)) -> dict[str, list[dict]]:
    query = q.lower()
    matches = [
        runbook
        for runbook in RUNBOOKS
        if query in runbook["title"].lower() or query in runbook["summary"].lower()
    ]
    return {"results": matches or RUNBOOKS[:1]}


@app.post("/drafts/customer-reply", operation_id="draft_customer_reply")
async def draft_customer_reply(payload: DraftCustomerReplyRequest) -> dict[str, str]:
    body = (
        f"Hi team at {payload.account_name}, we have confirmed the reported issue and are "
        f"actively mitigating it. {payload.technical_summary} We also recognize the renewal "
        f"context is sensitive ({payload.renewal_risk}) and will provide daily updates until "
        f"the billing and product concerns are fully closed."
    )
    return {"draft": body}


@app.get("/drafts/customer-reply/preview", operation_id="draft_customer_reply_preview")
async def draft_customer_reply_preview(
    account_name: str,
    csm: str,
    issue_summary: str,
    renewal_risk: str,
    technical_summary: str,
) -> dict[str, str]:
    return await draft_customer_reply(
        DraftCustomerReplyRequest(
            account_name=account_name,
            csm=csm,
            issue_summary=issue_summary,
            renewal_risk=renewal_risk,
            technical_summary=technical_summary,
        )
    )


@app.post("/tasks/followup", operation_id="create_followup_task")
async def create_followup_task(payload: CreateFollowupTaskRequest) -> dict[str, str | list[str]]:
    return {
        "task_id": "TASK-9001",
        "status": "created",
        "owner": payload.owner,
        "due_date": payload.due_date,
        "action_items": payload.action_items,
    }


@app.get("/tasks/followup/preview", operation_id="create_followup_task_preview")
async def create_followup_task_preview(
    account_name: str,
    owner: str,
    due_date: str,
    action_items: str = "",
) -> dict[str, str | list[str]]:
    parsed_items = [item.strip() for item in action_items.split(",") if item.strip()]
    return await create_followup_task(
        CreateFollowupTaskRequest(
            account_name=account_name,
            owner=owner,
            due_date=due_date,
            action_items=parsed_items,
        )
    )


@app.get("/demo-scene", operation_id="get_demo_scene")
async def get_demo_scene() -> dict:
    return {
        "scene": "Customer Escalation Triage",
        "requested_at": datetime.now(UTC).isoformat(),
        "default_customer_id": SCENE_PRESETS[0]["customer_id"],
        "default_account_name": SCENE_PRESETS[0]["account_name"],
        "default_issue_summary": SCENE_PRESETS[0]["issue_summary"],
        "default_product_issue": SCENE_PRESETS[0]["product_issue"],
        "default_billing_issue": SCENE_PRESETS[0]["billing_issue"],
        "default_incident_id": SCENE_PRESETS[0]["incident_id"],
        "presets": SCENE_PRESETS,
    }
