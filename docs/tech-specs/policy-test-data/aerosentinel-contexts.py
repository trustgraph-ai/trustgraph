"""
AeroSentinel Dynamics — Test User Contexts

Five personas exercising different policy paths through the
AeroSentinel knowledge graph. Each context is a transient
identity envelope assembled at query time.
"""

from trustgraph.schema import (
    UserContext, Assignment, Entitlement,
    OverrideAuthority, Delegation,
)

AS = "http://aerosentinel.com/data/"

# -------------------------------------------------------------
# Marcus — Commercial Sales Lead
#
# Manages commercial drone deals and client accounts.
# Should see: SkyFreighter specs, code, clients, AeroScout-v2
#             public specs
# Should NOT see: GhostEye-X anything (Violation if defense,
#                 Filtered if unrelated commercial)
# -------------------------------------------------------------

marcus = UserContext(
    user_id=f"{AS}usr_marcus_chen",
    roles=[f"{AS}CommercialSalesLead"],
    organisational_units=[f"{AS}Commercial_Division"],
    assignments=[
        Assignment(
            resource=f"{AS}SkyFreighter",
            scope="Sales",
            status="Active",
            valid_from="2026-01-01T00:00:00Z",
            valid_to="2026-12-31T23:59:59Z",
        ),
    ],
)

# -------------------------------------------------------------
# Dr. Elena — Defense Lead Engineer
#
# Lead engineer on GhostEye-X stealth and AI guidance systems.
# Should see: GhostEye-X specs, stealth coating, targeting AI,
#             flight tests, briefings, contracts, suppliers
# Should NOT see: SkyFreighter commercial IP (Filtered),
#                 client relationships (Filtered)
# -------------------------------------------------------------

elena = UserContext(
    user_id=f"{AS}usr_elena_vance",
    roles=[f"{AS}DefenseLeadEngineer", f"{AS}R_and_D_Lead"],
    organisational_units=[f"{AS}Defense_Division"],
    assignments=[
        Assignment(
            resource=f"{AS}GhostEye_X",
            scope="AutonomousAI",
            status="ActiveClearance",
            valid_from="2026-01-01T00:00:00Z",
            valid_to="2026-12-31T23:59:59Z",
            qualifiers={
                "classification": "Secret",
                "clean_team": "True",
            },
        ),
    ],
    purpose="FlightTestAnalysis",
)

# -------------------------------------------------------------
# Priya — Marketing Manager
#
# Writes public promotional copy and website documentation.
# Should see: AeroScout-v2 public specs, public office list
# Should NOT see: SkyFreighter proprietary data (Filtered),
#                 GhostEye-X anything (Violation — ITAR)
# -------------------------------------------------------------

priya = UserContext(
    user_id=f"{AS}usr_priya_sharma",
    roles=[f"{AS}MarketingManager"],
    organisational_units=[f"{AS}Commercial_Division"],
    entitlements=[
        Entitlement(
            resource_scope="PublicCatalog",
            access_level="ReadOnly",
        ),
    ],
)

# -------------------------------------------------------------
# Sam — Executive Assistant
#
# Books meetings and manages briefings on behalf of Dr. Elena.
# Acts under delegated authority with scope limited to
# scheduling and briefing access.
#
# Should see: GhostEye-X briefings (via delegation from Elena)
# Should NOT see: Targeting AI source code, stealth coating
#                 (delegation scope is ScheduleAndBriefing only)
# -------------------------------------------------------------

sam = UserContext(
    user_id=f"{AS}usr_sam_park",
    roles=[f"{AS}ExecutiveAssistant"],
    organisational_units=[f"{AS}Corporate"],
    delegation=Delegation(
        delegator_id=f"{AS}usr_elena_vance",
        scope="ScheduleAndBriefing",
    ),
)

# -------------------------------------------------------------
# Sarah — Compliance Officer
#
# Conducts mandatory export control and security compliance
# reviews. Has override authority for ITAR policy area.
#
# Should see: Full defense supplier list, contracts, and
#             classification data under audit override.
# Policy engine logs the override as an audited event.
# -------------------------------------------------------------

sarah = UserContext(
    user_id=f"{AS}usr_sarah_okonkwo",
    roles=[f"{AS}ComplianceOfficer"],
    organisational_units=[f"{AS}Corporate"],
    override_authorities=[
        OverrideAuthority(
            policy_area="ExportControlITAR",
            condition="Mandatory ITAR compliance audit",
        ),
    ],
    purpose="ITAR_Audit_Review",
)
