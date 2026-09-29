
from dataclasses import dataclass, field


@dataclass
class Assignment:
    resource: str = ""
    scope: str = ""
    status: str = ""
    valid_from: str = ""
    valid_to: str = ""
    qualifiers: dict[str, str] = field(default_factory=dict)


@dataclass
class Entitlement:
    resource_scope: str = ""
    access_level: str = ""
    valid_from: str = ""
    valid_to: str = ""


@dataclass
class OverrideAuthority:
    policy_area: str = ""
    condition: str = ""


@dataclass
class Delegation:
    delegator_id: str = ""
    scope: str = ""


@dataclass
class UserContext:
    user_id: str = ""
    roles: list[str] = field(default_factory=list)
    assignments: list[Assignment] = field(default_factory=list)
    entitlements: list[Entitlement] = field(default_factory=list)
    organisational_units: list[str] = field(default_factory=list)
    override_authorities: list[OverrideAuthority] = field(default_factory=list)
    delegation: Delegation | None = None
    purpose: str = ""
