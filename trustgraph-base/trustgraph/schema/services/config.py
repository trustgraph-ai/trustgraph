
from dataclasses import dataclass, field

from ..core.topic import queue
from ..core.primitives import Error

############################################################################

# Config service:
#   get(workspace, keys) -> (version, values)
#   list(workspace, type) -> (version, directory)
#   getvalues(workspace, type) -> (version, values)
#   getvalues-all-ws(type) -> (version, values with workspace field)
#   put(workspace, values) -> ()
#   delete(workspace, keys) -> ()
#   config(workspace) -> (version, config)
#
# Most operations are scoped to a workspace. The workspace field on the
# request identifies which workspace's config to read or modify.
# getvalues-all-ws returns values across all workspaces for a single
# type — used by shared processors to load type-scoped config at startup.

@dataclass
class ConfigKey:
    type: str = ""
    key: str = ""

@dataclass
class ConfigValue:
    type: str = ""
    key: str = ""
    value: str = ""
    # Populated by getvalues-all-ws responses so callers can identify
    # which workspace each value belongs to. Empty otherwise.
    workspace: str = ""

@dataclass
class ConfigRequest:
    # Operations: get, list, getvalues, getvalues-all-ws, delete, put,
    # config
    operation: str = ""

    # Workspace scope — required on all operations except
    # getvalues-all-ws which spans all workspaces.
    workspace: str = ""

    # get, delete
    keys: list[ConfigKey] = field(default_factory=list)

    # list, getvalues, getvalues-all-ws
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

    # Dict of config type -> list of affected workspaces.
    # Handlers look up their registered type and get the list of
    # workspaces that need refreshing.
    # e.g. {"prompt": ["workspace-a", "workspace-b"], "schema": ["workspace-a"]}
    changes: dict[str, list[str]] = field(default_factory=dict)

config_request_queue = queue('config', cls='request')
config_response_queue = queue('config', cls='response')
config_push_queue = queue('config', cls='notify')

############################################################################

