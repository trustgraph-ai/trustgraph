
from dataclasses import dataclass, field

from ..core.topic import queue
from ..core.primitives import Error

############################################################################

# Config service:
#   get(keys) -> (version, values)
#   list(type) -> (version, values)
#   getvalues(type) -> (version, values)
#   put(values) -> ()
#   delete(keys) -> ()
#   config() -> (version, config)
@dataclass
class ConfigKey:
    type: str = ""
    key: str = ""

@dataclass
class ConfigValue:
    type: str = ""
    key: str = ""
    value: str = ""

# Prompt services, abstract the prompt generation
@dataclass
class ConfigRequest:
    operation: str = ""  # get, list, getvalues, delete, put, config

    # get, delete
    keys: list[ConfigKey] = field(default_factory=list)

    # list, getvalues
    type: str = ""

    # put
    values: list[ConfigValue] = field(default_factory=list)

@dataclass
class ConfigResponse:
    # get, list, getvalues, config
    version: int = 0

    # get, getvalues
    values: list[ConfigValue] = field(default_factory=list)

    # list
    directory: list[str] = field(default_factory=list)

    # config
    config: dict[str, dict[str, str]] = field(default_factory=dict)

    # Everything
    error: Error | None = None

@dataclass
class ConfigPush:
    version: int = 0
    types: list[str] = field(default_factory=list)

config_request_queue = queue('config', cls='request')
config_response_queue = queue('config', cls='response')
config_push_queue = queue('config', cls='flow')

############################################################################

