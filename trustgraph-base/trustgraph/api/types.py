"""
TrustGraph API Type Definitions

Data classes and type definitions for TrustGraph API objects including knowledge
graph elements, metadata structures, and streaming response chunks.
"""

import dataclasses
import datetime
from typing import List, Optional, Dict, Any
from .. knowledge import hash, Uri, Literal

@dataclasses.dataclass
class Triple:
    """
    RDF triple representing a knowledge graph statement.

    Attributes:
        s: Subject (entity URI or value)
        p: Predicate (relationship URI)
        o: Object (entity URI, literal value, or typed value)
    """
    s : str
    p : str
    o : str

@dataclasses.dataclass
class ConfigKey:
    """
    Configuration key identifier.

    Attributes:
        type: Configuration type/category (e.g., "llm", "embedding")
        key: Specific configuration key within the type
    """
    type : str
    key : str

@dataclasses.dataclass
class ConfigValue:
    """
    Configuration key-value pair.

    Attributes:
        type: Configuration type/category
        key: Specific configuration key
        value: Configuration value as string
        workspace: Workspace the value belongs to. Only populated for
            responses to getvalues-all-ws; empty otherwise.
    """
    type : str
    key : str
    value : str
    workspace : str = ""

@dataclasses.dataclass
class DocumentMetadata:
    """
    Metadata for a document in the library.

    Attributes:
        id: Unique document identifier
        time: Document creation/upload timestamp
        kind: Document MIME type (e.g., "application/pdf", "text/plain")
        title: Document title
        comments: Additional comments or description
        metadata: List of RDF triples providing structured metadata
        workspace: Workspace the document belongs to
        tags: List of tags for categorization
        parent_id: Parent document ID for child documents (empty for top-level docs)
        document_type: "source" for uploaded documents, "extracted" for derived content
    """
    id : str
    time : datetime.datetime
    kind : str
    title : str
    comments : str
    metadata : List[Triple]
    workspace : str
    tags : List[str]
    parent_id : str = ""
    document_type : str = "source"

@dataclasses.dataclass
class ProcessingMetadata:
    """
    Metadata for an active document processing job.

    Attributes:
        id: Unique processing job identifier
        document_id: ID of the document being processed
        time: Processing start timestamp
        flow: Flow instance handling the processing
        workspace: Workspace the processing job belongs to
        collection: Target collection for processed data
        tags: List of tags for categorization
    """
    id : str
    document_id : str
    time : datetime.datetime
    flow : str
    workspace : str
    collection : str
    tags : List[str]

@dataclasses.dataclass
class CollectionMetadata:
    """
    Metadata for a data collection.

    Collections provide logical grouping within a workspace for documents
    and knowledge graph data.

    Attributes:
        collection: Collection identifier
        name: Human-readable collection name
        description: Collection description
        tags: List of tags for categorization
    """
    collection : str
    name : str
    description : str
    tags : List[str]

# Streaming chunk types

@dataclasses.dataclass
class StreamingChunk:
    """
    Base class for streaming response chunks.

    Used for WebSocket-based streaming operations where responses are delivered
    incrementally as they are generated.

    Attributes:
        content: The text content of this chunk
        end_of_message: True if this is the final chunk of a message segment
    """
    content: str
    end_of_message: bool = False

@dataclasses.dataclass
class AgentThought(StreamingChunk):
    """
    Agent reasoning/thought process chunk.

    Represents the agent's internal reasoning or planning steps during execution.
    These chunks show how the agent is thinking about the problem.

    Attributes:
        content: Agent's thought text
        end_of_message: True if this completes the current thought
        message_type: Always "thought"
        message_id: Provenance URI of the entity being built
    """
    message_type: str = "thought"
    message_id: str = ""

@dataclasses.dataclass
class AgentObservation(StreamingChunk):
    """
    Agent tool execution observation chunk.

    Represents the result or observation from executing a tool or action.
    These chunks show what the agent learned from using tools.

    Attributes:
        content: Observation text describing tool results
        end_of_message: True if this completes the current observation
        message_type: Always "observation"
        message_id: Provenance URI of the entity being built
    """
    message_type: str = "observation"
    message_id: str = ""

@dataclasses.dataclass
class AgentAnswer(StreamingChunk):
    """
    Agent final answer chunk.

    Represents the agent's final response to the user's query after completing
    its reasoning and tool use.

    Attributes:
        content: Answer text
        end_of_message: True if this completes the current answer segment
        end_of_dialog: True if this completes the entire agent interaction
        message_type: Always "final-answer"
    """
    message_type: str = "final-answer"
    end_of_dialog: bool = False
    message_id: str = ""
    in_token: Optional[int] = None
    out_token: Optional[int] = None
    model: Optional[str] = None

@dataclasses.dataclass
class RAGChunk(StreamingChunk):
    """
    RAG (Retrieval-Augmented Generation) streaming chunk.

    Used for streaming responses from graph RAG, document RAG, text completion,
    and other generative services.

    Attributes:
        content: Generated text content
        end_of_stream: True if this is the final chunk of the stream
        error: Optional error information if an error occurred
        in_token: Input token count (populated on the final chunk, 0 otherwise)
        out_token: Output token count (populated on the final chunk, 0 otherwise)
        model: Model identifier (populated on the final chunk, empty otherwise)
        message_type: Always "rag"
    """
    message_type: str = "rag"
    end_of_stream: bool = False
    error: Optional[Dict[str, str]] = None
    in_token: Optional[int] = None
    out_token: Optional[int] = None
    model: Optional[str] = None

@dataclasses.dataclass
class TextCompletionResult:
    """
    Result from a text completion request.

    Returned by text_completion() in both streaming and non-streaming modes.
    In streaming mode, text is None (chunks are delivered via the iterator).
    In non-streaming mode, text contains the complete response.

    Attributes:
        text: Complete response text (None in streaming mode)
        in_token: Input token count (None if not available)
        out_token: Output token count (None if not available)
        model: Model identifier (None if not available)
    """
    text: Optional[str]
    in_token: Optional[int] = None
    out_token: Optional[int] = None
    model: Optional[str] = None

@dataclasses.dataclass
class ProvenanceEvent:
    """
    Provenance event for explainability.

    Emitted during retrieval queries when explainable mode is enabled.
    Each event represents a provenance node created during query processing.

    Attributes:
        explain_id: URI of the provenance node (e.g., urn:trustgraph:question:abc123)
        explain_graph: Named graph where provenance triples are stored (e.g., urn:graph:retrieval)
        event_type: Type of provenance event (question, exploration, focus, synthesis, etc.)
        entity: Parsed ExplainEntity from inline triples (if available)
        triples: Raw triples from the response (wire format dicts)
    """
    explain_id: str
    explain_graph: str = ""
    event_type: str = ""  # Derived from explain_id
    entity: object = None  # ExplainEntity (parsed from triples)
    triples: list = dataclasses.field(default_factory=list)  # Raw wire-format triple dicts

    def __post_init__(self):
        # Extract event type from explain_id
        if "question" in self.explain_id:
            self.event_type = "question"
        elif "grounding" in self.explain_id:
            self.event_type = "grounding"
        elif "exploration" in self.explain_id:
            self.event_type = "exploration"
        elif "focus" in self.explain_id:
            self.event_type = "focus"
        elif "synthesis" in self.explain_id:
            self.event_type = "synthesis"
        elif "iteration" in self.explain_id:
            self.event_type = "iteration"
        elif "observation" in self.explain_id:
            self.event_type = "observation"
        elif "conclusion" in self.explain_id:
            self.event_type = "conclusion"
        elif "decomposition" in self.explain_id:
            self.event_type = "decomposition"
        elif "finding" in self.explain_id:
            self.event_type = "finding"
        elif "plan" in self.explain_id:
            self.event_type = "plan"
        elif "step-result" in self.explain_id:
            self.event_type = "step-result"
        elif "session" in self.explain_id:
            self.event_type = "session"
