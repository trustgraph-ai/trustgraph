# Execution Core — Message Flow Trace

## Use Case 1: Financial Spend Review

Traces the full lifecycle of: *"Compare Q3 contractor spend against
budget across our UK engineering teams, and draft a summary for the
finance review — omitting any unapproved salary adjustments."*

See [execution-core-use-cases.md](execution-core-use-cases.md) §1 for
the plan decomposition. See
[execution-core-spec.md](execution-core-spec.md) for the design that
this trace exercises.

### Phase 0: Ingress

The gateway receives the question over WebSocket. It creates an
AgentRequest (existing schema) and publishes to the agent request
queue. The Execution Coordinator consumes it.

```
Gateway → request:tg:agent:ws1

AgentRequest {
  question: "Compare Q3 contractor spend...",
  collection: "default",
  conversation_id: "conv-8f92",
  session_id: "sess-a1b2",
}
```

### Phase 1: Run Initialisation

The Coordinator creates an ExecutionRun and its named graphs.

```
ExecutionRun {
  run_id: "run-3e7f",
  goal: "Compare Q3 contractor spend against budget...",
  principal: "urn:tg:user:alice",
  workspace: "ws1",
  status: "planning",
  working_graph: "urn:tg:run:run-3e7f",
  audit_graph: "urn:tg:audit:run-3e7f",
}
```

The Coordinator streams a "thought" response to the gateway so the
user sees activity:

```
Coordinator → response:tg:agent:ws1

AgentResponse {
  message_type: "thought",
  content: "Planning data retrieval for Q3 spend review...",
  end_of_message: true,
}
```

### Phase 2: Planning

The Coordinator sends the goal and context to the Planner service.

```
Coordinator → request:tg:planner:ws1

PlanRequest {
  run_id: "run-3e7f",
  goal: "Compare Q3 contractor spend against budget...",
  context: { workspace: "ws1", principal: "urn:tg:user:alice" },
}
```

The Planner queries the capability registry for workspace `ws1`,
browses the index of available capabilities and their
PortContracts, and selects the ones relevant to the goal.

The Planner returns an ExecutionPlan — a DAG of six steps:

```
Planner → response:tg:planner:ws1

ExecutionPlan {
  plan_id: "plan-001",
  run_id: "run-3e7f",
  steps: [
    { step_id: "1A", capability: "erp-finance-query",
      depends_on: [], status: "pending",
      params: { query: "Q3 contractor invoices + budgets" },
      emits: "TabularArtifact" },

    { step_id: "1B", capability: "tabular-redact",
      depends_on: ["1A"], status: "pending",
      params: { rules: "strip unapproved salary adjustments" },
      emits: "TabularArtifact" },

    { step_id: "2A", capability: "knowledge-graph-query",
      depends_on: [], status: "pending",
      params: { query: "UK engineering teams + cost centres" },
      emits: "SubgraphArtifact" },

    { step_id: "2B", capability: "document-retrieval",
      depends_on: [], status: "pending",
      params: { query: "Q3 budget review policy guidelines" },
      emits: "TextBlobArtifact" },

    { step_id: "3", capability: "tabular-join",
      depends_on: ["1B", "2A"], status: "pending",
      params: { join_key: "cost_centre", compute: "variance" },
      emits: "TabularArtifact" },

    { step_id: "4", capability: "llm-synthesis",
      depends_on: ["3", "2B"], status: "pending",
      params: { format: "executive summary" },
      emits: "ReportArtifact" },
  ]
}
```

### Phase 3: Policy Pre-flight

The Coordinator sends the full plan to the Policy Engine for
pre-flight evaluation before any steps execute.

```
Coordinator → request:tg:exec-policy:ws1

PolicyEvalRequest {
  run_id: "run-3e7f",
  evaluation_type: "plan-preflight",
  subject: "plan-001",
  principal: "urn:tg:user:alice",
  plan: { ... full plan ... },
}
```

The Policy Engine evaluates each step against workspace rules.
Step 1B's redaction is part of the plan, not a policy splice —
the Planner included it because the question asked to omit salary
adjustments. The policy engine may add its own constraints (e.g.
disclosure posture on the ERP data).

```
Policy Engine → response:tg:exec-policy:ws1

PolicyEvalResponse {
  run_id: "run-3e7f",
  attestation: {
    verdict: "ALLOW",
    disclosure: "OPAQUE",
    boundary_failure: false,
  },
  per_step_obligations: {
    "1A": { verdict: "ALLOW", disclosure: "OPAQUE" },
    "1B": { verdict: "ALLOW" },
    "2A": { verdict: "ALLOW" },
    "2B": { verdict: "ALLOW" },
    "3":  { verdict: "ALLOW" },
    "4":  { verdict: "ALLOW" },
  },
}
```

The attestation is written to the audit graph. The Coordinator
transitions the run to `status: "executing"`.

### Phase 4: Parallel Dispatch — Ready Steps

Steps 1A, 2A, and 2B have no dependencies — they're immediately
ready. The Coordinator dispatches all three in parallel.

```
Coordinator → request:tg:erp-finance-query:ws1

StepRequest {
  run_id: "run-3e7f",
  step_id: "1A",
  capability: "erp-finance-query",
  params: { query: "Q3 contractor invoices + budgets" },
}

Coordinator → request:tg:knowledge-graph-query:ws1

StepRequest {
  run_id: "run-3e7f",
  step_id: "2A",
  capability: "knowledge-graph-query",
  params: { query: "UK engineering teams + cost centres" },
}

Coordinator → request:tg:document-retrieval:ws1

StepRequest {
  run_id: "run-3e7f",
  step_id: "2B",
  capability: "document-retrieval",
  params: { query: "Q3 budget review policy guidelines" },
}
```

### Phase 5: Step Completion — Branch A continues

Step 2A and 2B complete independently and their artifacts are written
to the working graph. Step 1A completes:

```
ERP Worker → response:tg:erp-finance-query:ws1

StepResponse {
  run_id: "run-3e7f",
  step_id: "1A",
  status: "completed",
  artifact: {
    artifact_id: "art-1a",
    type: "TabularArtifact",
    render_hint: "table",
    content: { ... rows of invoices and budgets ... },
  },
}
```

The Coordinator writes the artifact to the working graph, marks
step 1A as completed, and checks the DAG. Step 1B's dependencies
are now satisfied — dispatch it:

```
Coordinator → request:tg:tabular-redact:ws1

StepRequest {
  run_id: "run-3e7f",
  step_id: "1B",
  capability: "tabular-redact",
  params: { rules: "strip unapproved salary adjustments" },
  input_artifacts: ["art-1a"],
}
```

### Phase 6: Step Completion — Policy Egress Check

Step 1B completes with a sanitised TabularArtifact. Before writing
it to the working graph, the Coordinator sends it through a policy
egress check:

```
Coordinator → request:tg:exec-policy:ws1

PolicyEvalRequest {
  run_id: "run-3e7f",
  evaluation_type: "step-egress",
  subject: "1B",
  artifact: { ... sanitised tabular data ... },
  principal: "urn:tg:user:alice",
}
```

Policy Engine confirms ALLOW. The artifact is committed to the
working graph. The attestation is written to the audit graph.

### Phase 7: Join Step

Steps 1B, 2A, and 2B are all complete. Step 3's dependencies are
satisfied:

```
Coordinator → request:tg:tabular-join:ws1

StepRequest {
  run_id: "run-3e7f",
  step_id: "3",
  capability: "tabular-join",
  params: { join_key: "cost_centre", compute: "variance" },
  input_artifacts: ["art-1b", "art-2a"],
}
```

Step 3 completes with a variance-by-team TabularArtifact.

### Phase 8: Synthesis

Step 4's dependencies (step 3 and step 2B) are both satisfied:

```
Coordinator → request:tg:llm-synthesis:ws1

StepRequest {
  run_id: "run-3e7f",
  step_id: "4",
  capability: "llm-synthesis",
  params: { format: "executive summary" },
  input_artifacts: ["art-3", "art-2b"],
}
```

The LLM synthesis step produces a ReportArtifact with the executive
summary narrative and an embedded reference to the variance table.

### Phase 9: Egress and Response

The Coordinator performs a final policy egress check on the
ReportArtifact. Policy returns ALLOW with `disclosure: OPAQUE` —
meaning the response includes a notice that some items were
policy-constrained but no detail.

The Coordinator streams the final response back through the
existing agent response topic:

```
Coordinator → response:tg:agent:ws1

AgentResponse {
  message_type: "answer",
  content: "## Q3 Contractor Spend vs Budget — UK Engineering\n\n...",
  end_of_message: true,
  end_of_dialog: true,
}
```

The run transitions to `status: "completed"`. The working graph
and audit graph are retained for explainability queries.

### Summary: Topic Flow

```
Gateway
  │
  ▼
request:tg:agent:ws1 ──▶ Coordinator
  │
  ├──▶ request:tg:planner:ws1 ──▶ Planner ──▶ response
  │
  ├──▶ request:tg:exec-policy:ws1 ──▶ Policy Engine ──▶ response
  │         (pre-flight, per-step egress, final egress)
  │
  ├──┬──▶ request:tg:erp-finance-query:ws1 ──▶ ERP Worker ──▶ response
  │  ├──▶ request:tg:knowledge-graph-query:ws1 ──▶ KG Worker ──▶ response
  │  └──▶ request:tg:document-retrieval:ws1 ──▶ Doc Worker ──▶ response
  │
  ├──▶ request:tg:tabular-redact:ws1 ──▶ Redact Worker ──▶ response
  │
  ├──▶ request:tg:tabular-join:ws1 ──▶ Join Worker ──▶ response
  │
  ├──▶ request:tg:llm-synthesis:ws1 ──▶ LLM Worker ──▶ response
  │
  ▼
response:tg:agent:ws1 ──▶ Gateway ──▶ WebSocket ──▶ User
```
