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
    """
    type : str
    key : str
    value : str

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
        user: User/owner identifier
        tags: List of tags for categorization
    """
    id : str
    time : datetime.datetime
    kind : str
    title : str
    comments : str
    metadata : List[Triple]
    user : str
    tags : List[str]

@dataclasses.dataclass
class ProcessingMetadata:
    """
    Metadata for an active document processing job.

    Attributes:
        id: Unique processing job identifier
        document_id: ID of the document being processed
        time: Processing start timestamp
        flow: Flow instance handling the processing
        user: User identifier
        collection: Target collection for processed data
        tags: List of tags for categorization
    """
    id : str
    document_id : str
    time : datetime.datetime
    flow : str
    user : str
    collection : str
    tags : List[str]

@dataclasses.dataclass
class CollectionMetadata:
    """
    Metadata for a data collection.

    Collections provide logical grouping and isolation for documents and
    knowledge graph data.

    Attributes:
        user: User/owner identifier
        collection: Collection identifier
        name: Human-readable collection name
        description: Collection description
        tags: List of tags for categorization
    """
    user : str
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
        chunk_type: Always "thought"
    """
    chunk_type: str = "thought"

@dataclasses.dataclass
class AgentObservation(StreamingChunk):
    """
    Agent tool execution observation chunk.

    Represents the result or observation from executing a tool or action.
    These chunks show what the agent learned from using tools.

    Attributes:
        content: Observation text describing tool results
        end_of_message: True if this completes the current observation
        chunk_type: Always "observation"
    """
    chunk_type: str = "observation"

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
        chunk_type: Always "final-answer"
    """
    chunk_type: str = "final-answer"
    end_of_dialog: bool = False

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
        chunk_type: Always "rag"
    """
    chunk_type: str = "rag"
    end_of_stream: bool = False
    error: Optional[Dict[str, str]] = None
