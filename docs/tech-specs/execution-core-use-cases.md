# Execution Core — Use Cases

Worked examples showing how the Execution Coordinator decomposes
real-world agentic questions into parallel DAGs with typed artifacts,
policy-driven redaction, and structured synthesis.

Each use case shows:
- Parallel branch decomposition
- Artifact type flow (TextBlob, Tabular, Subgraph, ExternalReference)
- Redaction/filtering splice points
- Join and synthesis steps

## 1. Financial Spend Review

**Question:** "Compare Q3 contractor spend against budget across our
UK engineering teams, and draft a summary for the finance review —
omitting any unapproved salary adjustments."

### Plan

**Branch A — Structured Spend & Budget:**

- **Step 1A:** Query ERP/Finance MCP tool for Q3 contractor invoices
  and departmental budgets. Output: `TabularArtifact`.
- **Step 1B:** Redact restricted individual compensation rows and
  unapproved salary adjustments. Output: sanitised `TabularArtifact`.

**Branch B — Org Structure & Team Context:**

- **Step 2A:** Query Knowledge Graph for active UK engineering teams
  and cost-centre mappings. Output: `SubgraphArtifact`.
- **Step 2B:** Retrieve Q3 budget review policy guidelines from
  document store. Output: `TextBlobArtifact`.

**Join:**

- **Step 3:** Join sanitised spend (1B) with UK engineering cost
  centres (2A) and compute variance by team. Output:
  `TabularArtifact`.

**Synthesis:**

- **Step 4:** Generate executive summary combining variance table (3)
  and policy framing (2B). Output: `TextBlobArtifact`.

---

## 2. Enterprise Account Retention Briefing

**Question:** "Identify our top 5 enterprise accounts with open
high-severity support tickets and upcoming renewals in the next
90 days, and prepare a retention briefing for the VP of Sales."

### Plan

**Branch A — Renewals & Account Graph:**

- **Step 1A:** Query CRM MCP tool for enterprise accounts renewing
  within 90 days. Output: `ExternalReferenceArtifact` (cursor).
- **Step 1B:** Query Knowledge Graph for account ownership, contract
  tiers, and executive sponsors. Output: `SubgraphArtifact`.

**Branch B — Support Incidents & Engineering Notes:**

- **Step 2A:** Query Support Ticketing MCP tool for open Sev-1/Sev-2
  tickets across enterprise accounts. Output: `TabularArtifact`.
- **Step 2B:** Retrieve recent root-cause analysis post-mortems for
  those ticket IDs. Output: `TextBlobArtifact`.
- **Step 2C:** Redact internal engineer names and unpublished security
  vulnerability details from RCAs. Output: sanitised
  `TextBlobArtifact`.

**Join:**

- **Step 3:** Intersect renewing accounts (1A), account graph (1B),
  and open tickets (2A). Rank top 5 by ARR at risk. Output:
  `TabularArtifact`.

**Synthesis:**

- **Step 4:** Draft VP of Sales retention briefing combining ranked
  account table (3) and sanitised RCA summaries (2C). Output:
  `TextBlobArtifact`.

---

## 3. Flood Risk Infrastructure Map

**Question:** "Show me all active flood warnings in the Thames Valley
along with our critical substation assets inside those zones, and map
them out for the field ops team."

### Plan

**Branch A — Live Flood Polygons:**

- **Step 1A:** Query Environment Agency MCP tool for active flood
  warning zones in the Thames Valley. Output:
  `ExternalReferenceArtifact` (GeoJSON feature collection).
- **Step 1B:** Compute unified bounding box and normalise warning
  severity polygons. Output: `SubgraphArtifact` (GeoJSON payload).

**Branch B — Infrastructure Asset Graph:**

- **Step 2A:** Query Knowledge Graph for substations in the Thames
  Valley region. Output: `SubgraphArtifact` (coordinates and voltage
  tiers).
- **Step 2B:** Redact restricted grid-security coordinates and
  classified defence-site feeders. Output: sanitised
  `SubgraphArtifact`.

**Join:**

- **Step 3:** Spatial join — flag substations (2B) inside active
  flood polygons (1B). Assemble combined map payload with bounding
  box and overlay layers. Output: `SubgraphArtifact` (GeoJSON).

**Synthesis:**

- **Step 4:** Generate field ops dispatch summary paired with
  structured map object (3) for WebSocket UI rendering. Output:
  `TextBlobArtifact` + `SubgraphArtifact`.

---

## 4. Payment Gateway Outage Timeline

**Question:** "Reconstruct the timeline of events leading up to
Tuesday's payment gateway outage, including code deployments,
infrastructure alerts, and customer impact milestones."

### Plan

**Branch A — Change & Deployment Events:**

- **Step 1A:** Query CI/CD MCP tool for all production deployments
  and config changes in the 24 hours preceding the incident. Output:
  `TabularArtifact` (ISO timestamps).
- **Step 1B:** Redact internal commit author emails and proprietary
  repository paths. Output: sanitised `TabularArtifact`.

**Branch B — Telemetry & Incident Comms:**

- **Step 2A:** Query Observability MCP tool for threshold alerts,
  latency spikes, and failover triggers. Output: `TabularArtifact`
  (ISO timestamps).
- **Step 2B:** Retrieve incident Slack/war-room logs and status-page
  updates. Output: `TextBlobArtifact`.
- **Step 2C:** Extract timestamped incident decisions and customer
  impact milestones from logs. Output: `SubgraphArtifact`.

**Join:**

- **Step 3:** Merge sanitised deployments (1B), telemetry alerts
  (2A), and extracted milestones (2C). Sort chronologically, link
  causal edges (`prov:wasInformedBy`). Output: `SubgraphArtifact`
  (timeline).

**Synthesis:**

- **Step 4:** Generate post-incident executive summary paired with
  structured timeline object (3) for UI rendering. Output:
  `TextBlobArtifact` + `SubgraphArtifact`.

---

## 5. Subsea Cable Fault Regulatory Report

**Question:** "Compile a regulatory incident report on yesterday's
North Sea subsea cable fault — including the affected cable route and
repair vessel positions on a map, a chronological timeline of fault
detection and traffic rerouting, and a table of impacted enterprise
SLAs."

### Plan

**Branch A — Geospatial & Maritime Data:**

- **Step 1A:** Query Subsea Network GIS MCP tool for affected North
  Sea cable corridor and fault coordinates. Output:
  `SubgraphArtifact` (GeoJSON).
- **Step 1B:** Query AIS Maritime Tracking MCP tool for nearby
  cable-repair vessels. Compute map bounding box and multi-layer
  GeoJSON overlay. Output: `SubgraphArtifact` (map).

**Branch B — Chronological Event Log:**

- **Step 2A:** Query Network Telemetry MCP tool for optical signal
  loss, BGP route-flap alerts, and automated failover timestamps.
  Output: `TabularArtifact`.
- **Step 2B:** Retrieve NOC operator shift handover logs and extract
  timestamped manual mitigation actions. Output: `TextBlobArtifact`
  then `SubgraphArtifact`.
- **Step 2C:** Merge telemetry (2A) and operator actions (2B) into
  ordered incident timeline. Output: `SubgraphArtifact` (timeline).

**Branch C — Commercial & SLA Impact:**

- **Step 3A:** Query Knowledge Graph for enterprise circuits
  traversing the affected cable segment. Output: `SubgraphArtifact`.
- **Step 3B:** Cross-reference affected circuits against CRM SLA
  tiers. Redact sensitive customer contact PII. Output: sanitised
  `TabularArtifact`.

**Synthesis:**

- **Step 4:** Generate executive narrative and regulatory compliance
  sections. Bind narrative, GeoJSON map (1B), timeline (2C), and SLA
  impact table (3B) into composite report. Output:
  `TextBlobArtifact` + `SubgraphArtifact`.

---

## 6. Portfolio Rebalance Trade Slate

**Question:** "Review our Global Growth Mandate portfolio against
current sector exposure limits and Q3 macro research, and calculate
the exact rebalance trades needed — excluding any restricted-list
securities."

### Plan

**Branch A — Current Holdings & Market Prices:**

- **Step 1A:** Query Portfolio Accounting MCP tool for current
  holdings, quantities, and cash balances. Output:
  `TabularArtifact`.
- **Step 1B:** Query Market Data MCP tool for live prices and FX
  rates. Join with holdings (1A) to compute current portfolio
  weights. Output: `TabularArtifact`.

**Branch B — Mandate Rules & Compliance Restrictions:**

- **Step 2A:** Query Knowledge Graph for Global Growth Mandate target
  allocation bands and sector exposure caps. Output:
  `SubgraphArtifact`.
- **Step 2B:** Query Compliance MCP tool for active restricted-list
  and MNPI securities. Filter restricted tickers before optimisation.
  Output: sanitised `TabularArtifact`.

**Branch C — Macro & Desk Research:**

- **Step 3A:** Retrieve Q3 investment committee notes and sector
  outlook memos. Output: `TextBlobArtifact`.
- **Step 3B:** Extract structured overweight/underweight sector tilts
  from research notes. Output: `SubgraphArtifact`.

**Optimise:**

- **Step 4:** Run Portfolio Optimiser MCP tool combining current
  weights (1B), mandate constraints (2A), restricted-list exclusions
  (2B), and research tilts (3B). Generate buy/sell order quantities
  and post-trade weights. Output: `TabularArtifact`.

**Synthesis:**

- **Step 5:** Draft investment rationale and compliance attestation
  summary paired with proposed trade slate (4) for HITL approval.
  Output: `TextBlobArtifact`.
