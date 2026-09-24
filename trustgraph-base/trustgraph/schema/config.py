
from dataclasses import dataclass, field

from .core.topic import queue
from .core.primitives import Error

############################################################################

# Config service

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
    # Operations: get, list, getvalues, getvalues-all-ws,
    # getkeys-all-ws, delete, put, config
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
class WorkspaceChanges:
    created: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)

@dataclass
class ConfigPush:
    version: int = 0

    # Dict of config type -> list of affected workspaces.
    changes: dict[str, list[str]] = field(default_factory=dict)

    # Workspace lifecycle events.
    workspace_changes: WorkspaceChanges | None = None

config_request_queue = queue('config', cls='request')
config_response_queue = queue('config', cls='response')
config_push_queue = queue('config', cls='notify')

############################################################################

# Flow service

@dataclass
class FlowRequest:
    operation: str = ""  # list-blueprints, get-blueprint, put-blueprint, delete-blueprint
                         # list-flows, get-flow, start-flow, stop-flow

    # get_blueprint, put_blueprint, delete_blueprint, start_flow
    blueprint_name: str = ""

    # put_blueprint
    blueprint_definition: str = ""

    # start_flow
    description: str = ""

    # get_flow, start_flow, stop_flow
    flow_id: str = ""

    # start_flow - optional parameters for flow customization
    parameters: dict[str, str] = field(default_factory=dict)

@dataclass
class FlowResponse:
    # list_blueprints
    blueprint_names: list[str] = field(default_factory=list)

    # list_flows
    flow_ids: list[str] = field(default_factory=list)

    # get_blueprint
    blueprint_definition: str = ""

    # get_flow
    flow: str = ""

    # get_flow
    description: str = ""

    # get_flow - parameters used when flow was started
    parameters: dict[str, str] = field(default_factory=dict)

    # Everything
    error: Error | None = None

flow_request_queue = queue('flow', cls='request')
flow_response_queue = queue('flow', cls='response')

############################################################################

# Collection management

@dataclass
class CollectionMetadata:
    """Collection metadata record"""
    collection: str = ""
    name: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)

############################################################################

@dataclass
class CollectionManagementRequest:
    """Request for collection management operations."""
    operation: str = ""  # e.g., "delete-collection"

    collection: str = ""
    timestamp: str = ""  # ISO timestamp
    name: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)

    # For list
    tag_filter: list[str] = field(default_factory=list)  # Optional filter by tags
    limit: int = 0

@dataclass
class CollectionManagementResponse:
    """Response for collection management operations"""
    error: Error | None = None  # Only populated if there's an error
    timestamp: str = ""  # ISO timestamp
    collections: list[CollectionMetadata] = field(default_factory=list)

collection_request_queue = queue('collection', cls='request')
collection_response_queue = queue('collection', cls='response')

############################################################################
