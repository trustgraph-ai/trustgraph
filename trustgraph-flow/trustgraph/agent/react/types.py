
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
    llm_duration_ms : int = None
    tool_duration_ms : int = None
    tool_error : str = None
    in_token : int = None
    out_token : int = None
    llm_model : str = None

@dataclasses.dataclass
class Final:
    thought : str
    final : str
    llm_duration_ms : int = None
    in_token : int = None
    out_token : int = None
    llm_model : str = None

