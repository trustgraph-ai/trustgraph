
import dataclasses
from typing import Any, Dict

@dataclasses.dataclass
class Argument:
    name : str
    type : str
    description : str

@dataclasses.dataclass
class Tool:
    name : str
    description : str
    arguments : list[Argument]
    implementation : Any
    config : Dict[str, str]
    
@dataclasses.dataclass
class Action:
    thought : str
    name : str
    arguments : dict
    observation : str
    
@dataclasses.dataclass
class Final:
    thought : str
    final : str

