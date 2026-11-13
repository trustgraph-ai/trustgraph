# TrustGraph Execution Core — Technical Specification

## Vision

Add a distributed, policy-governed execution runtime built on
TrustGraph's existing Pulsar pub/sub backbone and RDF knowledge graph
as an alternative to the single-process, in-memory ReAct agent loop.

Agent execution becomes a first-class graph data structure —
plannable, verifiable, auditable, and governable — without introducing
an external workflow engine.

## Key Goals

1. **Structured execution, not text-passing.** Plans, artifacts, and
   tool contracts are typed RDF — not untyped blobs an LLM must parse.
   Steps declare what they accept and emit. The system validates
   compatibility before execution begins.

2. **LLM cost control.** A tiered verification funnel handles ~90% of
   step validation with deterministic graph/SHACL checks (zero LLM
   cost). Fast classifiers cover another tier. The LLM planner is only
   re-invoked on exceptions or unexpected state changes.

3. **Parallel execution.** Plans are DAGs, not linear chains. Independent
   branches run concurrently over Pulsar. The rolling-horizon loop
   (Plan, Decide, Act, Re-evaluate) replaces sequential ReAct turns.

4. **Policy before side effects.** Every plan and every tool invocation
   passes through a pluggable policy engine before execution. SHACL-AF
   rules, RBAC, semantic risk scoring — chained per workspace.

5. **Graduated disclosure.** Four levels from silent redaction (no trace
   visible to agent or user) through full transparency (what was
   redacted, why, which policy rule). Dual-plane provenance separates
   the agent's working graph from the restricted audit graph.

6. **Zero breaking changes.** The Execution Coordinator drops into the
   existing Agent Manager role, preserving current Pulsar topics and
   WebSocket gateway contracts.

## Microservice Topology

Six pluggable services over Pulsar:

| Service | Role |
|---|---|
| **Execution Coordinator** | Drop-in for Agent Manager. Manages run state machine, validates port compatibility, splices adapters/redactors, routes control frames. |
| **Planner** | Consumes goals + context, emits `tg:ExecutionPlan` DAG subgraphs. Swappable: static ontology workflows, DAG decomposers, incremental planners. |
| **Policy Engine (PDP)** | Evaluates plans, context ingress, tool egress. Emits immutable `tg:PolicyAttestation` with ALLOW / FILTER / REQUIRE_APPROVAL / DENY decisions. Independent of Coordinator. |
| **Redaction Services (PEP)** | Dynamically spliced by Coordinator on FILTER or boundary failure. Dedicated processors per artifact type (graph, tabular, text). |
| **Action Workers** | MCP servers, GraphRAG, legacy tools. Consume typed control frames, dereference bulk payloads on demand. |
| **Verification** | Deterministic SHACL/graph checks + fast classifiers. Gates step completion without LLM calls. |

We need to take care not to duplicate policy code between Verification and
Policy Engine.  Verification owns task-contract shapes (e.g., "did the SQL
tool return valid rows matching tg:emitsOutput?"), while Policy Engine owns
workspace/principal rules (e.g., "can this user/agent see those rows?").

## Key Design Decisions

### Plans are graph data

An `tg:ExecutionPlan` is an RDF DAG of `tg:Step` nodes with
`tg:dependsOn` edges, stored in a run-scoped named graph
(`urn:tg:run:<run_id>`). This enables:

- Pre-flight structural validation and policy checks
- Parallel branch detection and concurrent dispatch
- Dynamic mutation (insert/reorder steps mid-run)
- Full PROV-O lineage without bolt-on tracing

### Typed artifacts, not text blobs

Every step output is a typed `tg:Artifact`:

- **TextBlobArtifact** — prose, RAG chunks, document content
- **TabularArtifact** — structured rows/columns with schema
- **SubgraphArtifact** — RDF triples conforming to an OWL/SHACL shape
- **ExternalReferenceArtifact** — cursors/handles to external systems
- **CompositeArtifact** — ordered manifest of child artifact
  references with role labels. Distinct from SubgraphArtifact so
  the serialisation layer can dispatch on type: SubgraphArtifact
  payloads are RDF to serialise, CompositeArtifact payloads are
  references to resolve and assemble
- **ReportArtifact** — a human-readable document assembling
  narrative, tables, maps, and other visualisations into a
  deliverable. Distinct from CompositeArtifact: a
  CompositeArtifact is a structural manifest for machine
  consumption, a ReportArtifact is a rendered document for
  people

Capabilities declare `tg:acceptsInput` and `tg:emitsOutput` with
type + shape. The Planner uses port contracts to choose and sequence
steps — including any format conversions or extractions. The
Coordinator validates edge compatibility at plan time but does not
inject steps. All steps come from the Planner.

### Tiered verification funnel

| Tier | Method | Cost | Coverage |
|---|---|---|---|
| 1 | SHACL/graph structural checks | 0ms LLM | ~90% of steps |
| 2 | Fast classifiers / Decision Scoring | ~35ms | Edge cases |
| 3 | LLM Planner re-evaluation | Full LLM call | Exceptions only |

### Three-axis policy evaluation

Policy evaluation output is compositional, not combinatorial.
Every `tg:PolicyAttestation` carries three orthogonal dimensions:

**Verdict** — what action to take:

| Verdict | Meaning |
|---|---|
| `ALLOW` | Proceed as planned |
| `FILTER` | Splice a redaction processor to strip/mask restricted content |
| `REQUIRE_APPROVAL` | Suspend execution, route to HITL approval over WebSockets |
| `DENY` | Block the step — feed violation back to Planner or abort |

**Disclosure** — how much to reveal in-band (applies to FILTER and
DENY):

| Disclosure | Agent/User sees |
|---|---|
| `SILENT` | Nothing — lineage rewritten, indistinguishable from normal response |
| `OPAQUE` | Generic notice: "some restricted items were omitted" or "action unavailable due to policy" |
| `TRANSPARENT` | Full `tg:RedactionReceipt` with policy citations — what, why, which rule |

**Boundary failure flag** — independent out-of-band signal:

A boolean flag emitted alongside the verdict when a security boundary
permitted something it should not have. This is not necessarily a
breach — the recipient may be authorised — but it indicates the
boundary itself failed and needs investigation. Decoupled from
filtering: normal data minimisation (strip PII for an unprivileged
role) is `FILTER + SILENT + boundary_failure: false`. An unexpected
boundary failure is `FILTER + SILENT + boundary_failure: true` —
masked in-band, immediate alert to
`tg.security.boundary_failure`, raw artifact quarantined to
`urn:tg:audit:<run_id>`.

### Dual-plane provenance

Two separate named graphs per run:

- **Working graph** (`urn:tg:run:<run_id>`) — visible to the agent
  and downstream steps. Subject to redaction.
- **Audit graph** (`urn:tg:audit:<run_id>`) — immutable, restricted.
  Contains unredacted provenance, policy attestations, boundary failure records.

### Mandatory causal justification

Every tool invocation requires PROV-O justification
(`prov:wasInformedBy` / `tg:justifiedBy`). No orphaned or runaway
tool loops — the graph must show why each step exists.

### Operational governance as data

Retry limits, timeouts, approval requirements, and idempotency
templates are RDF triples (`tg:maxRetries`, `tg:timeoutMs`,
`tg:requiresApproval`, `tg:idempotencyKeyTemplate`) — not
hardcoded config. Policy can vary them per workspace, per principal,
per capability.

## Migration Path

The Execution Coordinator preserves the existing Agent Manager's
Pulsar topic contracts and WebSocket gateway interface. Existing
`AgentRequest`/response schemas map onto `tg:ExecutionRun`
initialization. The swap is internal — callers see no API change.

## Ontologies

Three ontologies, two new:

| Ontology | Scope | Status |
|---|---|---|
| **`tg-exec`** | Plans, steps, DAG edges, artifact types, port contracts, run state machine, operational governance | New |
| **`tg-exec-pol`** | Execution policy: verdicts, disclosure posture, boundary failure, obligations, attestations | New |
| **PROV-O** | Lineage (wasGeneratedBy, wasInformedBy, etc.) | W3C standard, adopt as-is |

Note: the existing `tg-pol` ontology covers query-time data filtering
(SHACL-AF rules on triple visibility). `tg-exec-pol` is a separate
concern — runtime governance of plans and tool invocations, not
query results.

## `tg-exec-pol` Ontology Design

Namespace: `https://trustgraph.ai/ontology/exec-pol/`

### Classes

**PolicyEvaluation** — a single evaluation event. Created each time
the Policy Engine assesses a plan, step, or artifact. Immutable once
written. Links to the subject being evaluated, the rules that matched,
and the resulting attestation.

**PolicyAttestation** — the three-axis output of an evaluation:
verdict, disclosure, and boundary failure flag. Attached to the
evaluation. Written to the audit graph; a redacted projection may
appear in the working graph depending on disclosure posture.

**RedactionReceipt** — created when verdict is FILTER. Records what
was removed or masked, which fields/triples were affected, and which
rule triggered it. Only surfaces in the working graph under
TRANSPARENT disclosure.

**ApprovalRequest** — created when verdict is REQUIRE_APPROVAL.
Records the step being held, the principal whose approval is needed,
and the WebSocket channel for HITL response. Carries a timeout after
which the Coordinator treats it as DENY.

**ApprovalDecision** — the HITL response to an ApprovalRequest.
Records who approved/denied, when, and an optional justification.
Immutable once written.

**BoundaryFailureRecord** — created when the boundary failure flag
is set. Records the artifact that crossed the boundary, the expected
boundary constraint, and the quarantine location in the audit graph.
Published to `tg.security.boundary_failure` for out-of-band alerting.

**ExecutionPolicyRule** — a named, versionable policy rule. References
the conditions under which it fires and the verdict/disclosure it
produces. Scoped to workspace, principal roles, and capability types.

### Properties

**Evaluation → subject linkage:**

- `evaluates` — what is being evaluated (a Plan, Step, or Artifact IRI)
- `evaluationType` — the evaluation context: `plan-preflight`,
  `step-ingress`, `step-egress`, `artifact-egress`
- `evaluatedAt` — timestamp
- `evaluatedBy` — the Policy Engine instance that performed the
  evaluation

**Evaluation → rule linkage:**

- `matchedRule` — the ExecutionPolicyRule(s) that fired
- `producedAttestation` — the resulting PolicyAttestation

**Attestation fields (the three axes):**

- `verdict` — ALLOW, FILTER, REQUIRE_APPROVAL, or DENY
- `disclosure` — SILENT, OPAQUE, or TRANSPARENT
- `boundaryFailure` — boolean, default false

**Attestation → obligations:**

- `redactionDirective` — links to a RedactionReceipt describing
  what to strip/mask (present when verdict is FILTER)
- `approvalRequest` — links to an ApprovalRequest (present when
  verdict is REQUIRE_APPROVAL)
- `boundaryFailureRecord` — links to a BoundaryFailureRecord
  (present when boundaryFailure is true)

**RedactionReceipt fields:**

- `affectedField` — the property or triple pattern that was
  redacted
- `redactionMethod` — how: `strip`, `mask`, `generalise`,
  `synthetic-replace`
- `triggeredByRule` — back-link to the ExecutionPolicyRule

**ApprovalRequest fields:**

- `heldStep` — the Step awaiting approval
- `requiredApprover` — principal role or specific user IRI
- `approvalChannel` — WebSocket channel identifier
- `approvalTimeout` — duration after which treated as DENY

**ApprovalDecision fields:**

- `respondsTo` — the ApprovalRequest
- `decision` — `approved` or `denied`
- `decidedBy` — user IRI
- `decidedAt` — timestamp
- `justification` — free text

**BoundaryFailureRecord fields:**

- `failedArtifact` — the artifact that crossed the boundary
- `expectedConstraint` — the SHACL shape or policy rule that
  should have prevented it
- `quarantineLocation` — the audit graph URI where the raw
  artifact is stored

**ExecutionPolicyRule fields:**

- `ruleId` — stable identifier for the rule
- `ruleVersion` — version string
- `appliesTo` — workspace, principal roles, capability types
  (multiple values)
- `condition` — SPARQL or SHACL condition expression
- `defaultVerdict` — the verdict when this rule fires
- `defaultDisclosure` — the disclosure posture when this rule fires
- `effectiveFrom` / `effectiveTo` — validity period

### Relationships

```
ExecutionPolicyRule
    ├── appliesTo ──▶ (workspace / role / capability IRI)
    ├── condition ──▶ (SPARQL / SHACL expression)
    ├── defaultVerdict ──▶ {ALLOW, FILTER, REQUIRE_APPROVAL, DENY}
    ├── defaultDisclosure ──▶ {SILENT, OPAQUE, TRANSPARENT}
    └── effectiveFrom / effectiveTo ──▶ xsd:dateTime

PolicyEvaluation
    ├── evaluates ──▶ (Plan / Step / Artifact IRI)
    ├── evaluationType ──▶ {plan-preflight, step-ingress, step-egress, artifact-egress}
    ├── matchedRule ──▶ ExecutionPolicyRule (0..n)
    ├── producedAttestation ──▶ PolicyAttestation
    └── evaluatedBy ──▶ (Policy Engine instance)

PolicyAttestation
    ├── verdict ──▶ {ALLOW, FILTER, REQUIRE_APPROVAL, DENY}
    ├── disclosure ──▶ {SILENT, OPAQUE, TRANSPARENT}
    ├── boundaryFailure ──▶ xsd:boolean
    ├── redactionDirective ──▶ RedactionReceipt (0..n)
    ├── approvalRequest ──▶ ApprovalRequest (0..1)
    └── boundaryFailureRecord ──▶ BoundaryFailureRecord (0..1)

RedactionReceipt
    ├── affectedField ──▶ (property / triple pattern)
    ├── redactionMethod ──▶ {strip, mask, generalise, synthetic-replace}
    └── triggeredByRule ──▶ ExecutionPolicyRule

ApprovalRequest
    ├── heldStep ──▶ tg-exec:Step
    ├── requiredApprover ──▶ (principal IRI)
    ├── approvalChannel ──▶ xsd:string
    └── approvalTimeout ──▶ xsd:duration

ApprovalDecision
    ├── respondsTo ──▶ ApprovalRequest
    ├── decision ──▶ {approved, denied}
    ├── decidedBy ──▶ (user IRI)
    └── justification ──▶ xsd:string

BoundaryFailureRecord
    ├── failedArtifact ──▶ tg-exec:Artifact
    ├── expectedConstraint ──▶ (shape / rule IRI)
    └── quarantineLocation ──▶ (audit graph URI)
```

### Storage

PolicyAttestations are always written to the audit graph
(`urn:tg:audit:<run_id>`). Under TRANSPARENT disclosure, a
projection (attestation + RedactionReceipt) is also written to
the working graph. Under OPAQUE, only a flag
(`tg-exec-pol:containsRedactions true`) appears in the working
graph. Under SILENT, nothing appears in the working graph.

BoundaryFailureRecords are audit-graph-only — never exposed
in-band.

ExecutionPolicyRules are stored per-workspace in the config
service, analogous to how `tg-pol` shapes are stored in
`urn:graph:policy`.

## `tg-exec` Ontology Design

Namespace: `https://trustgraph.ai/ontology/exec/`

### Classes — Run and Plan

**ExecutionRun** — top-level container for a single agent execution.
Created when a request arrives (e.g. from the gateway). Owns the
run-scoped named graphs (working and audit). Carries the goal,
principal, workspace, and current status.

**ExecutionPlan** — the DAG of steps the Planner produces for a run.
A run may have multiple plans over its lifetime — the initial plan
plus any revisions from re-planning. Each plan is immutable once
committed; re-planning creates a new plan that supersedes the
previous one.

**Step** — a single node in the plan DAG. Represents one unit of
work: a tool invocation, an adapter transformation, a redaction
splice, or an LLM call. Steps are typed by the capability they
invoke and the artifact types they consume and produce.

### Classes — Artifacts

**Artifact** — abstract base. Every step output is recorded as a
typed artifact linked to the step via PROV-O (`prov:wasGeneratedBy`).

**TextBlobArtifact** — prose, RAG chunks, document content. Carries
the text content and optional metadata (source URI, chunk index).

**TabularArtifact** — structured rows and columns. References a
schema describing column names and types. Content stored as a
serialised payload or external reference.

**SubgraphArtifact** — RDF triples conforming to an OWL/SHACL shape.
Stored in a step-scoped named graph
(`urn:tg:run:<run_id>:step:<step_id>`). References the shape it
conforms to.

**ExternalReferenceArtifact** — a pointer to data held outside the
execution graph. Examples: database cursor, object storage URI,
paginated API endpoint, download URL, streaming query handle. The
data isn't inline — something has to dereference it.

The consuming step is responsible for dereferencing. The Planner
must understand the available reference types and plan appropriate
steps to materialise them. The reference should declare enough for
the Planner and consumer to work with: what kind of external system,
what artifact type it resolves to, and any TTL/validity constraints.

Open: the full taxonomy of reference types needs detailed design
per integration. Enough is understood to validate the architecture;
the specifics will follow when concrete integrations are built.

**CompositeArtifact** — an ordered manifest of child artifact
references. Each component carries a role label (e.g. `map`,
`narrative`, `table`, `timeline`) and a reference to the child
artifact IRI. Distinct from SubgraphArtifact: the serialisation
layer treats SubgraphArtifact payloads as RDF to store directly,
while CompositeArtifact payloads are references to resolve and
assemble. Used when downstream steps or the serialisation layer need
to resolve and process child artifacts programmatically.

**ReportArtifact** — a human-readable document. Combines narrative
text with embedded or referenced visualisations (tables, maps,
charts, timelines) into a deliverable for people. Distinct from
CompositeArtifact: CompositeArtifact is a structural manifest for
machine consumption, ReportArtifact is a rendered document intended
for human readers. Carries a document format (e.g. markdown, HTML,
PDF) and references to any embedded artifacts.

### Classes — Capabilities and Ports

**Capability** — a registered tool or service the system can invoke.
MCP servers, GraphRAG, SPARQL query, LLM completion, extractors,
adapters. Each capability declares its port contracts.

**PortContract** — describes one input or output slot on a
capability. Specifies the artifact type accepted/emitted and
optionally a SHACL shape the artifact must conform to.

### Classes — Operational Governance

**GovernancePolicy** — per-capability operational constraints stored
as RDF. Not access control (that's `tg-exec-pol`) — these are
execution mechanics: retry behaviour, timeouts, approval
requirements, idempotency.

### Properties — ExecutionRun

- `goal` — the natural language or structured goal for this run
- `principal` — the user/agent principal who initiated the run
- `workspace` — workspace scope
- `status` — current run status: `planning`, `executing`,
  `awaiting-approval`, `completed`, `failed`, `aborted`
- `currentPlan` — the active ExecutionPlan
- `workingGraph` — URI of the run's working named graph
- `auditGraph` — URI of the run's audit named graph
- `startedAt` / `completedAt` — timestamps

### Properties — ExecutionPlan

- `forRun` — back-link to the ExecutionRun
- `supersedes` — the previous plan this one replaces (if re-planned)
- `rootStep` — entry point(s) of the DAG (steps with no dependencies)
- `createdBy` — the Planner instance that produced this plan
- `createdAt` — timestamp

### Properties — Step

- `partOfPlan` — the ExecutionPlan this step belongs to
- `dependsOn` — other Step(s) that must complete before this one
  can execute (DAG edges)
- `invokesCapability` — the Capability this step calls
- `inputBinding` — links to the Artifact(s) consumed as input,
  with the PortContract they bind to
- `status` — `pending`, `ready`, `executing`, `completed`,
  `failed`, `skipped`, `awaiting-approval`
- `retryCount` — current retry attempt number
- `startedAt` / `completedAt` — timestamps

### Properties — Artifact

- `producedByStep` — the Step that created this artifact
  (mirrors `prov:wasGeneratedBy`)
- `artifactType` — IRI identifying the concrete artifact subclass
- `conformsToShape` — SHACL shape this artifact validates against
  (for SubgraphArtifact and TabularArtifact). Used by the
  Verification service for structural validation
- `renderHint` — how the UI should display this artifact (e.g.
  `map`, `timeline`, `chart`, `table`, `markdown`, `graph-viz`).
  Set by the producer. Unknown hints fall back to generic display.
  Applies to all artifact types, not just SubgraphArtifact
- `contentRef` — for ExternalReferenceArtifact, the external URI
  or handle
- `createdAt` — timestamp

### Properties — CompositeArtifact

- `hasComponent` — ordered link to a child artifact, with:
  - `componentRole` — role label (e.g. `map`, `narrative`, `table`,
    `timeline`)
  - `componentArtifact` — IRI of the child Artifact
  - `componentOrder` — integer for ordering

### Properties — ReportArtifact

- `documentFormat` — output format: `markdown`, `html`, `pdf`
- `narrative` — the document body text
- `embeddedArtifact` — references to artifacts rendered inline
  (tables, maps, charts) with placement/ordering metadata

### Properties — Capability

- `capabilityId` — stable identifier
- `acceptsInput` — PortContract(s) for inputs
- `emitsOutput` — PortContract(s) for outputs
- `capabilityType` — classification: `tool`, `adapter`, `redactor`,
  `llm`, `retrieval`

### Properties — PortContract

- `portName` — identifier for this port on the capability
- `artifactType` — the Artifact subclass accepted/emitted
- `shape` — optional SHACL shape the artifact must conform to
- `required` — boolean, whether this port must be bound

### Properties — GovernancePolicy

- `governsCapability` — the Capability this policy applies to
- `maxRetries` — integer
- `timeoutMs` — milliseconds before the step is timed out
- `requiresApproval` — boolean, forces HITL before execution
- `idempotencyKeyTemplate` — string template for deduplication
- `appliesInWorkspace` — workspace scope (or all if absent)

### Relationships

```
ExecutionRun
    ├── principal ──▶ (user/agent IRI)
    ├── workspace ──▶ (workspace IRI)
    ├── currentPlan ──▶ ExecutionPlan
    ├── workingGraph ──▶ urn:tg:run:<run_id>
    └── auditGraph ──▶ urn:tg:audit:<run_id>

ExecutionPlan
    ├── forRun ──▶ ExecutionRun
    ├── supersedes ──▶ ExecutionPlan (0..1)
    ├── rootStep ──▶ Step (1..n)
    └── createdBy ──▶ (Planner instance)

Step
    ├── partOfPlan ──▶ ExecutionPlan
    ├── dependsOn ──▶ Step (0..n)
    ├── invokesCapability ──▶ Capability
    ├── inputBinding ──▶ Artifact (0..n)
    └── prov:wasInformedBy ──▶ Step (causal justification)

Artifact (and subtypes)
    ├── prov:wasGeneratedBy ──▶ Step
    ├── conformsToShape ──▶ (SHACL shape IRI)
    └── prov:wasDerivedFrom ──▶ Artifact (0..n)

CompositeArtifact (extends Artifact)
    └── hasComponent ──▶ ComponentEntry (1..n)
        ├── componentRole ──▶ xsd:string
        ├── componentArtifact ──▶ Artifact
        └── componentOrder ──▶ xsd:integer

ReportArtifact (extends Artifact)
    ├── documentFormat ──▶ {markdown, html, pdf}
    ├── narrative ──▶ xsd:string
    └── embeddedArtifact ──▶ Artifact (0..n)

Capability
    ├── acceptsInput ──▶ PortContract (0..n)
    └── emitsOutput ──▶ PortContract (1..n)

PortContract
    ├── artifactType ──▶ {TextBlobArtifact, TabularArtifact, SubgraphArtifact, ExternalReferenceArtifact, CompositeArtifact, ReportArtifact}
    └── shape ──▶ (SHACL shape IRI, optional)

GovernancePolicy
    ├── governsCapability ──▶ Capability
    └── appliesInWorkspace ──▶ (workspace IRI, optional)
```

### Storage

The ExecutionRun, its plans, steps, and artifacts are stored in the
working graph (`urn:tg:run:<run_id>`). SubgraphArtifact content goes
in step-scoped named graphs underneath the run graph.

Capability and PortContract definitions are registered per-workspace
in the config service — they describe what the system can do, not
what a particular run is doing.

GovernancePolicy triples are stored alongside capabilities in config,
allowing operational constraints to be updated without redeploying
services.

## Message Flow Traces

See [execution-core-flow-trace.md](execution-core-flow-trace.md) for
worked message-level traces exercising this design against the use
cases.

## Next Steps

1. Define the Agent Manager migration seam — map existing schemas onto
   `tg:ExecutionRun`
