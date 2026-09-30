"""
GC&CS Bletchley Park — Test User Contexts

Five personas exercising different policy paths through the
Bletchley Park knowledge graph. Each context is a transient
identity envelope assembled at query time.
"""

from trustgraph.schema import (
    UserContext, Assignment, Entitlement,
    OverrideAuthority, Delegation,
)

BP = "http://bletchleypark.gov.uk/data/"

# -------------------------------------------------------------
# Margaret — Hut 3 Intelligence Analyst
#
# Translates and analyses Army/Air Force decrypts produced by
# Hut 6. Sees the intelligence product but must NOT see how
# the ciphers are broken (methods/sources separation).
#
# Should see: Hut 3 intelligence summaries, Hut 3 reports
# Should NOT see: Hut 6 Bombe menus (methods separation),
#                 Enigma wiring diagrams (Most Secret methods),
#                 Hut 8 naval material (compartmentalisation),
#                 Ultra material (no Ultra clearance)
# -------------------------------------------------------------

margaret = UserContext(
    user_id=f"{BP}usr_margaret_wilson",
    roles=[f"{BP}IntelligenceAnalyst", f"{BP}Translator"],
    organisational_units=[f"{BP}Hut_3"],
    assignments=[
        Assignment(
            resource=f"{BP}Hut_3",
            scope="IntelligenceAnalysis",
            status="Active",
            valid_from="1943-01-01T00:00:00Z",
            valid_to="1945-12-31T23:59:59Z",
            qualifiers={
                "classification": "Secret",
            },
        ),
    ],
    purpose="IntelligenceTranslation",
)

# -------------------------------------------------------------
# Alan — Hut 8 Cryptanalyst
#
# Head of Naval Enigma cryptanalysis. Has Most Secret clearance
# for cryptanalytic methods. Sees Hut 8 operational material,
# Bombe menus, and Naval Enigma methods.
#
# Should see: Hut 8 reports, Bombe menus (Shark), Banburismus
#             method, Four-Rotor Bombe design
# Should NOT see: Hut 6 Army/Air Force material (compartmentalisation),
#                 Testery/Newmanry Lorenz material (compartmentalisation),
#                 ISK Abwehr material (compartmentalisation),
#                 Ultra material (no Ultra clearance)
# -------------------------------------------------------------

alan = UserContext(
    user_id=f"{BP}usr_alan_turing",
    roles=[f"{BP}SectionHead", f"{BP}Cryptanalyst"],
    organisational_units=[f"{BP}Hut_8"],
    assignments=[
        Assignment(
            resource=f"{BP}Hut_8",
            scope="Cryptanalysis",
            status="Active",
            valid_from="1939-09-04T00:00:00Z",
            valid_to="1945-12-31T23:59:59Z",
            qualifiers={
                "classification": "MostSecret",
            },
        ),
    ],
    purpose="NavalEnigmaCryptanalysis",
)

# -------------------------------------------------------------
# Dorothy — Bombe Operator, Hut 11
#
# Operates Bombe machines on behalf of both Hut 6 and Hut 8.
# Receives Bombe menus (the wiring instructions) but must not
# see the intelligence product those breaks produce, nor the
# cryptanalytic theory behind the menus.
#
# Should see: Bombe operating procedures, Bombe menus
#             (from Hut 6 and Hut 8 — served sections)
# Should NOT see: Intelligence reports from any Hut,
#                 Banburismus method (Most Secret theory),
#                 Colossus specs (Ultra, wrong section),
#                 Ultra dissemination protocols
# -------------------------------------------------------------

dorothy = UserContext(
    user_id=f"{BP}usr_dorothy_jenkins",
    roles=[f"{BP}BombeOperator"],
    organisational_units=[f"{BP}Hut_11"],
    assignments=[
        Assignment(
            resource=f"{BP}Hut_11",
            scope="MachineOperations",
            status="Active",
            valid_from="1942-06-01T00:00:00Z",
            valid_to="1945-12-31T23:59:59Z",
            qualifiers={
                "classification": "Secret",
            },
        ),
    ],
    purpose="BombeOperations",
)

# -------------------------------------------------------------
# Commander Bradshaw — Admiralty Liaison
#
# Royal Navy officer attached to Bletchley Park as liaison
# between GC&CS and the Admiralty's Operational Intelligence
# Centre (OIC). Receives Naval intelligence product from
# Hut 4 for convoy routing decisions.
#
# Has a liaison assignment covering Hut 4 (Naval intelligence).
# Must NOT see cryptanalytic methods (how Enigma is broken)
# or material from non-naval sections.
#
# Should see: Hut 4 naval intelligence summaries,
#             U-boat dispositions
# Should NOT see: Hut 8 cryptanalytic reports (methods),
#                 Hut 6/3 Army material (compartmentalisation),
#                 Bombe menus (methods),
#                 Ultra material (no Ultra clearance)
# -------------------------------------------------------------

bradshaw = UserContext(
    user_id=f"{BP}usr_cdr_bradshaw",
    roles=[f"{BP}LiaisonOfficer"],
    organisational_units=[f"{BP}Admiralty"],
    assignments=[
        Assignment(
            resource=f"{BP}Hut_4",
            scope="Liaison",
            status="Active",
            valid_from="1943-01-01T00:00:00Z",
            valid_to="1945-12-31T23:59:59Z",
            qualifiers={
                "classification": "Secret",
            },
        ),
    ],
    purpose="ConvoyRoutingIntelligence",
)

# -------------------------------------------------------------
# Travis — Director of GC&CS
#
# Has full oversight of all sections and Ultra clearance.
# Override authority for Ultra dissemination. The only persona
# who can see everything.
#
# Should see: All material across all sections and all
#             classification levels including Ultra.
# -------------------------------------------------------------

travis = UserContext(
    user_id=f"{BP}usr_travis",
    roles=[f"{BP}Director"],
    organisational_units=[f"{BP}Directorate"],
    assignments=[
        Assignment(
            resource=f"{BP}GC_CS",
            scope="DirectorOversight",
            status="Active",
            valid_from="1942-02-01T00:00:00Z",
            valid_to="1945-12-31T23:59:59Z",
            qualifiers={
                "classification": "Ultra",
            },
        ),
    ],
    override_authorities=[
        OverrideAuthority(
            policy_area="UltraDissemination",
            condition="Director oversight of all GC&CS operations",
        ),
    ],
    purpose="DirectorOversight",
)
