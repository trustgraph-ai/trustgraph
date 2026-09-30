# AeroSentinel Dynamics — Policy Test Data

Test data for validating the policy filtering engine against
realistic dual-use (commercial + defense) scenarios.

## Files

| File | Contents |
|------|----------|
| `aerosentinel-graph.ttl` | Knowledge graph: products, specs, clients, contracts, suppliers |
| `aerosentinel-policies.ttl` | SHACL-AF policy shapes stored in `urn:graph:policy` |
| `aerosentinel-contexts.py` | Python `UserContext` instances for each test persona |

## Scenario

AeroSentinel Dynamics is a dual-use drone manufacturer. They
build commercial drones (crop monitoring, logistics delivery)
and classified defense systems (stealth reconnaissance,
autonomous target tracking AI).

The graph contains three tiers of data:

- **Public** — product spec sheets, office locations
- **Proprietary** — commercial IP, sensor schematics, client
  relationships
- **ITAR/Secret** — stealth coatings, targeting AI code,
  defense contracts, foreign supplier details

## Test Personas

| Persona | Role | Org Unit | Key Context |
|---------|------|----------|-------------|
| Marcus | CommercialSalesLead | Commercial | Assignment: SkyFreighter (Sales) |
| Dr. Elena | DefenseLeadEngineer | Defense | Assignment: GhostEye-X (AutonomousAI, Secret clearance) |
| Priya | MarketingManager | Commercial | Entitlement: PublicCatalog only |
| Sam | ExecutiveAssistant | Corporate | Delegation from Dr. Elena (ScheduleAndBriefing) |
| Sarah | ComplianceOfficer | Corporate | Override: ExportControlITAR; Purpose: ITAR_Audit_Review |

## Expected Policy Evaluations

| Who | Query | Expected Result | Determination | Rationale |
|-----|-------|-----------------|---------------|-----------|
| Priya | AeroScout-v2 specs | Specs returned | **Allowed** | Public data, open to all |
| Marcus | All customer relationships | Only SkyFreighter clients returned; AgriCo visible (same division); defense contracts absent | **Filtered** | Routine over-retrieval: commercial user's broad query caught defense data |
| Priya | Stealth battery schematics and targeting AI | Access blocked | **Violation** | Marketing user touching ITAR-restricted military IP |
| Marcus | GhostEye-X contract details | Access blocked | **Violation** | Commercial user crossing defense information barrier |
| Dr. Elena | GhostEye-X flight test data | Data returned | **Allowed** | Assigned to GhostEye-X with active clearance |
| Dr. Elena | SkyFreighter payload code | Not returned | **Filtered** | Defense engineer has no assignment to commercial IP |
| Sam | GhostEye-X briefings | Briefing returned | **Allowed** | Delegation from Dr. Elena covers ScheduleAndBriefing |
| Sam | Targeting AI source code | Not returned | **Filtered** | Delegation scope is ScheduleAndBriefing, not source code |
| Sarah | GhostEye-X foreign supplier list | Full data returned | **Allowed** | Override authority for ExportControlITAR exercised; audited override event logged |
| Sarah | SkyFreighter client list | Not returned | **Filtered** | Override authority is for ITAR only, not commercial IP |
