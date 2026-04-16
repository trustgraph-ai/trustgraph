from __future__ import annotations

from typing import Any

from . spec import Spec

class Parameter:
    def __init__(self, value: Any) -> None:
        self.value = value
    async def start(self) -> None:
        pass
    async def stop(self) -> None:
        pass
        
class ParameterSpec(Spec):
    def __init__(self, name: str) -> None:
        self.name = name

    def add(self, flow: Any, processor: Any, definition: dict[str, Any]) -> None:

        value = definition.get(self.name, None)

        flow.parameter[self.name] = Parameter(value)
