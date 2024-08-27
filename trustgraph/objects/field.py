
from dataclasses import dataclass
from enum import Enum

class FieldType(Enum):
    STRING = 0
    INT = 1
    LONG = 2
    BOOL = 3
    FLOAT = 4
    DOUBLE = 5

    def __str__(self):
        return self.name.lower()

@dataclass
class Field:
    name: str
    size: int = -1
    primary: bool = False
    type: str = "undefined"
    description: str = ""

    @staticmethod
    def parse(defn):

        if defn == "" or defn is None:
            raise RuntimeError("Field definition cannot be empty")

        parts = defn.split(":")

        if len(parts) == 0:
            raise RuntimeError("Field definition cannot be empty")

        if len(parts) == 1: parts.append("string")
        if len(parts) == 2: parts.append("0")
        if len(parts) == 3: parts.append("")
        if len(parts) == 4: parts.append("")

        name, type, size, pri, description = parts

        try:
            type = FieldType[type.upper()]
        except:
            raise RuntimeError(f"Field type {type} is not known")

        pri = True if pri == "pri" else False

        return Field(
            name=name, type=type, size=size, primary=pri,
            description=description
        )

    def __repr__(self):
        name = self.name
        type = self.type
        size = self.size
        pri = "pri" if self.primary else ""
        description = self.description

        return f"{name}:{type}:{size}:{pri}:{description}"

    def __str__(self):
        name = self.name
        type = self.type
        size = self.size
        pri = "pri" if self.primary else ""
        description = self.description

        return f"{name}:{type}:{size}:{pri}:{description}"
