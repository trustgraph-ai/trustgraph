from dataclasses import dataclass, field

from ..core.primitives import Error


@dataclass
class PassthroughRequest:
    payload: dict = field(default_factory=dict)


@dataclass
class PassthroughResponse:
    payload: dict = field(default_factory=dict)
    error: Error | None = None
    is_final: bool = True
