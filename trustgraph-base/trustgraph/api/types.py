
import dataclasses
import datetime
from typing import List, Optional, Dict, Any
from .. knowledge import hash, Uri, Literal

@dataclasses.dataclass
class Triple:
    s : str
    p : str
    o : str

@dataclasses.dataclass
class ConfigKey:
    type : str
    key : str

@dataclasses.dataclass
class ConfigValue:
    type : str
    key : str
    value : str

@dataclasses.dataclass
class DocumentMetadata:
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
    id : str
    document_id : str
    time : datetime.datetime
    flow : str
    user : str
    collection : str
    tags : List[str]

@dataclasses.dataclass
class CollectionMetadata:
    user : str
    collection : str
    name : str
    description : str
    tags : List[str]
    created_at : str
    updated_at : str

# Streaming chunk types

@dataclasses.dataclass
class StreamingChunk:
    """Base class for streaming chunks"""
    content: str
    end_of_message: bool = False

@dataclasses.dataclass
class AgentThought(StreamingChunk):
    """Agent reasoning chunk"""
    chunk_type: str = "thought"

@dataclasses.dataclass
class AgentObservation(StreamingChunk):
    """Agent tool observation chunk"""
    chunk_type: str = "observation"

@dataclasses.dataclass
class AgentAnswer(StreamingChunk):
    """Agent final answer chunk"""
    chunk_type: str = "final-answer"
    end_of_dialog: bool = False

@dataclasses.dataclass
class RAGChunk(StreamingChunk):
    """RAG streaming chunk"""
    end_of_stream: bool = False
    error: Optional[Dict[str, str]] = None
