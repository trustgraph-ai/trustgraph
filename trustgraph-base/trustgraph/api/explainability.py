"""
Explainability support for TrustGraph API.

Provides classes for explainability entities (Question, Exploration, Focus,
Synthesis, Analysis, Conclusion) and utilities for fetching them with
eventual consistency handling.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple, Union

# Provenance predicates
TG = "https://trustgraph.ai/ns/"
TG_QUERY = TG + "query"
TG_EDGE_COUNT = TG + "edgeCount"
TG_SELECTED_EDGE = TG + "selectedEdge"
TG_EDGE = TG + "edge"
TG_REASONING = TG + "reasoning"
TG_CONTENT = TG + "content"
TG_DOCUMENT = TG + "document"
TG_CHUNK_COUNT = TG + "chunkCount"
TG_SELECTED_CHUNK = TG + "selectedChunk"
TG_THOUGHT = TG + "thought"
TG_ACTION = TG + "action"
TG_ARGUMENTS = TG + "arguments"
TG_OBSERVATION = TG + "observation"
TG_ANSWER = TG + "answer"
TG_THOUGHT_DOCUMENT = TG + "thoughtDocument"
TG_OBSERVATION_DOCUMENT = TG + "observationDocument"

# Entity types
TG_QUESTION = TG + "Question"
TG_EXPLORATION = TG + "Exploration"
TG_FOCUS = TG + "Focus"
TG_SYNTHESIS = TG + "Synthesis"
TG_ANALYSIS = TG + "Analysis"
TG_CONCLUSION = TG + "Conclusion"
TG_GRAPH_RAG_QUESTION = TG + "GraphRagQuestion"
TG_DOC_RAG_QUESTION = TG + "DocRagQuestion"
TG_AGENT_QUESTION = TG + "AgentQuestion"

# PROV-O predicates
PROV = "http://www.w3.org/ns/prov#"
PROV_STARTED_AT_TIME = PROV + "startedAtTime"
PROV_WAS_DERIVED_FROM = PROV + "wasDerivedFrom"
PROV_WAS_GENERATED_BY = PROV + "wasGeneratedBy"

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"


@dataclass
class EdgeSelection:
    """A selected edge with reasoning from GraphRAG Focus step."""
    uri: str
    edge: Optional[Dict[str, str]] = None  # {"s": ..., "p": ..., "o": ...}
    reasoning: str = ""


@dataclass
class ExplainEntity:
    """Base class for explainability entities."""
    uri: str
    entity_type: str = ""

    @classmethod
    def from_triples(cls, uri: str, triples: List[Tuple[str, str, Any]]) -> "ExplainEntity":
        """Parse triples into the appropriate entity type."""
        # Determine entity type from rdf:type triples
        types = [o for s, p, o in triples if p == RDF_TYPE]

        if TG_GRAPH_RAG_QUESTION in types or TG_DOC_RAG_QUESTION in types or TG_AGENT_QUESTION in types:
            return Question.from_triples(uri, triples, types)
        elif TG_EXPLORATION in types:
            return Exploration.from_triples(uri, triples)
        elif TG_FOCUS in types:
            return Focus.from_triples(uri, triples)
        elif TG_SYNTHESIS in types:
            return Synthesis.from_triples(uri, triples)
        elif TG_ANALYSIS in types:
            return Analysis.from_triples(uri, triples)
        elif TG_CONCLUSION in types:
            return Conclusion.from_triples(uri, triples)
        else:
            # Generic entity
            return ExplainEntity(uri=uri, entity_type="unknown")


@dataclass
class Question(ExplainEntity):
    """Question entity - the user's query that started the session."""
    query: str = ""
    timestamp: str = ""
    question_type: str = ""  # "graph-rag", "document-rag", "agent"

    @classmethod
    def from_triples(cls, uri: str, triples: List[Tuple[str, str, Any]],
                     types: List[str]) -> "Question":
        query = ""
        timestamp = ""
        question_type = "unknown"

        for s, p, o in triples:
            if p == TG_QUERY:
                query = o
            elif p == PROV_STARTED_AT_TIME:
                timestamp = o

        if TG_GRAPH_RAG_QUESTION in types:
            question_type = "graph-rag"
        elif TG_DOC_RAG_QUESTION in types:
            question_type = "document-rag"
        elif TG_AGENT_QUESTION in types:
            question_type = "agent"

        return cls(
            uri=uri,
            entity_type="question",
            query=query,
            timestamp=timestamp,
            question_type=question_type
        )


@dataclass
class Exploration(ExplainEntity):
    """Exploration entity - edges/chunks retrieved from the knowledge store."""
    edge_count: int = 0
    chunk_count: int = 0

    @classmethod
    def from_triples(cls, uri: str, triples: List[Tuple[str, str, Any]]) -> "Exploration":
        edge_count = 0
        chunk_count = 0

        for s, p, o in triples:
            if p == TG_EDGE_COUNT:
                try:
                    edge_count = int(o)
                except (ValueError, TypeError):
                    pass
            elif p == TG_CHUNK_COUNT:
                try:
                    chunk_count = int(o)
                except (ValueError, TypeError):
                    pass

        return cls(
            uri=uri,
            entity_type="exploration",
            edge_count=edge_count,
            chunk_count=chunk_count
        )


@dataclass
class Focus(ExplainEntity):
    """Focus entity - selected edges with LLM reasoning (GraphRAG only)."""
    selected_edge_uris: List[str] = field(default_factory=list)
    edge_selections: List[EdgeSelection] = field(default_factory=list)

    @classmethod
    def from_triples(cls, uri: str, triples: List[Tuple[str, str, Any]]) -> "Focus":
        selected_edge_uris = []

        for s, p, o in triples:
            if p == TG_SELECTED_EDGE and isinstance(o, str):
                selected_edge_uris.append(o)

        return cls(
            uri=uri,
            entity_type="focus",
            selected_edge_uris=selected_edge_uris,
            edge_selections=[]  # Populated separately by fetching each edge URI
        )


@dataclass
class Synthesis(ExplainEntity):
    """Synthesis entity - the final answer."""
    content: str = ""
    document_uri: str = ""  # Reference to librarian document

    @classmethod
    def from_triples(cls, uri: str, triples: List[Tuple[str, str, Any]]) -> "Synthesis":
        content = ""
        document_uri = ""

        for s, p, o in triples:
            if p == TG_CONTENT:
                content = o
            elif p == TG_DOCUMENT:
                document_uri = o

        return cls(
            uri=uri,
            entity_type="synthesis",
            content=content,
            document_uri=document_uri
        )


@dataclass
class Analysis(ExplainEntity):
    """Analysis entity - one think/act/observe cycle (Agent only)."""
    thought: str = ""
    action: str = ""
    arguments: str = ""  # JSON string
    observation: str = ""
    thought_document_uri: str = ""  # Reference to thought in librarian
    observation_document_uri: str = ""  # Reference to observation in librarian

    @classmethod
    def from_triples(cls, uri: str, triples: List[Tuple[str, str, Any]]) -> "Analysis":
        thought = ""
        action = ""
        arguments = ""
        observation = ""
        thought_document_uri = ""
        observation_document_uri = ""

        for s, p, o in triples:
            if p == TG_THOUGHT:
                thought = o
            elif p == TG_ACTION:
                action = o
            elif p == TG_ARGUMENTS:
                arguments = o
            elif p == TG_OBSERVATION:
                observation = o
            elif p == TG_THOUGHT_DOCUMENT:
                thought_document_uri = o
            elif p == TG_OBSERVATION_DOCUMENT:
                observation_document_uri = o

        return cls(
            uri=uri,
            entity_type="analysis",
            thought=thought,
            action=action,
            arguments=arguments,
            observation=observation,
            thought_document_uri=thought_document_uri,
            observation_document_uri=observation_document_uri
        )


@dataclass
class Conclusion(ExplainEntity):
    """Conclusion entity - final answer (Agent only)."""
    answer: str = ""
    document_uri: str = ""  # Reference to librarian document

    @classmethod
    def from_triples(cls, uri: str, triples: List[Tuple[str, str, Any]]) -> "Conclusion":
        answer = ""
        document_uri = ""

        for s, p, o in triples:
            if p == TG_ANSWER:
                answer = o
            elif p == TG_DOCUMENT:
                document_uri = o

        return cls(
            uri=uri,
            entity_type="conclusion",
            answer=answer,
            document_uri=document_uri
        )


def parse_edge_selection_triples(triples: List[Tuple[str, str, Any]]) -> EdgeSelection:
    """Parse triples for an edge selection entity."""
    uri = triples[0][0] if triples else ""
    edge = None
    reasoning = ""

    for s, p, o in triples:
        if p == TG_EDGE and isinstance(o, dict):
            edge = o
        elif p == TG_REASONING:
            reasoning = o

    return EdgeSelection(uri=uri, edge=edge, reasoning=reasoning)


def extract_term_value(term: Dict[str, Any]) -> Any:
    """Extract value from a wire-format Term dict."""
    t = term.get("t") or term.get("type")

    if t == "i":
        return term.get("i") or term.get("iri", "")
    elif t == "l":
        return term.get("v") or term.get("value", "")
    elif t == "t":
        # Quoted triple - return as dict
        tr = term.get("tr") or term.get("triple", {})
        return {
            "s": extract_term_value(tr.get("s", {})),
            "p": extract_term_value(tr.get("p", {})),
            "o": extract_term_value(tr.get("o", {})),
        }
    else:
        # Unknown format, try common keys
        return term.get("i") or term.get("v") or term.get("iri") or term.get("value") or str(term)


def wire_triples_to_tuples(wire_triples: List[Dict[str, Any]]) -> List[Tuple[str, str, Any]]:
    """Convert wire-format triples to (s, p, o) tuples."""
    result = []
    for t in wire_triples:
        s = extract_term_value(t.get("s", {}))
        p = extract_term_value(t.get("p", {}))
        o = extract_term_value(t.get("o", {}))
        result.append((s, p, o))
    return result


class ExplainabilityClient:
    """
    Client for fetching explainability entities with eventual consistency handling.

    Uses quiescence detection: fetch, wait, fetch again, compare.
    If results are the same, data is stable.
    """

    def __init__(self, flow_instance, retry_delay: float = 0.2, max_retries: int = 10):
        """
        Initialize explainability client.

        Args:
            flow_instance: A SocketFlowInstance for querying triples
            retry_delay: Delay between retries in seconds (default: 0.2)
            max_retries: Maximum retry attempts (default: 10)
        """
        self.flow = flow_instance
        self.retry_delay = retry_delay
        self.max_retries = max_retries
        self._label_cache: Dict[str, str] = {}

    def fetch_entity(
        self,
        uri: str,
        graph: Optional[str] = None,
        user: Optional[str] = None,
        collection: Optional[str] = None
    ) -> Optional[ExplainEntity]:
        """
        Fetch an explainability entity by URI with eventual consistency handling.

        Uses quiescence detection:
        1. Fetch triples for URI
        2. If zero results, retry
        3. If non-zero results, wait and fetch again
        4. If same results, data is stable - parse and return
        5. If different results, data still being written - retry

        Args:
            uri: The entity URI to fetch
            graph: Named graph to query (e.g., "urn:graph:retrieval")
            user: User/keyspace identifier
            collection: Collection identifier

        Returns:
            ExplainEntity subclass or None if not found
        """
        prev_triples = None

        for attempt in range(self.max_retries):
            # Fetch triples for this URI
            wire_triples = self.flow.triples_query(
                s=uri,
                g=graph,
                user=user,
                collection=collection,
                limit=100
            )

            if not wire_triples:
                # Zero results - definitely retry
                time.sleep(self.retry_delay)
                continue

            # Convert to comparable format
            triples = wire_triples_to_tuples(wire_triples)
            triples_set = frozenset((s, p, str(o)) for s, p, o in triples)

            if prev_triples is None:
                # First non-empty result - wait and check for stability
                prev_triples = triples_set
                time.sleep(self.retry_delay)
                continue

            if triples_set == prev_triples:
                # Same as before - data is stable
                return ExplainEntity.from_triples(uri, triples)
            else:
                # Different - still being written, update and retry
                prev_triples = triples_set
                time.sleep(self.retry_delay)
                continue

        # Max retries reached - return what we have if anything
        if prev_triples:
            # Re-fetch and parse
            wire_triples = self.flow.triples_query(
                s=uri, g=graph, user=user, collection=collection, limit=100
            )
            if wire_triples:
                triples = wire_triples_to_tuples(wire_triples)
                return ExplainEntity.from_triples(uri, triples)

        return None

    def fetch_edge_selection(
        self,
        uri: str,
        graph: Optional[str] = None,
        user: Optional[str] = None,
        collection: Optional[str] = None
    ) -> Optional[EdgeSelection]:
        """
        Fetch an edge selection entity (used by Focus).

        Args:
            uri: The edge selection URI
            graph: Named graph to query
            user: User/keyspace identifier
            collection: Collection identifier

        Returns:
            EdgeSelection or None if not found
        """
        wire_triples = self.flow.triples_query(
            s=uri,
            g=graph,
            user=user,
            collection=collection,
            limit=100
        )

        if not wire_triples:
            return None

        triples = wire_triples_to_tuples(wire_triples)
        return parse_edge_selection_triples(triples)

    def fetch_focus_with_edges(
        self,
        uri: str,
        graph: Optional[str] = None,
        user: Optional[str] = None,
        collection: Optional[str] = None
    ) -> Optional[Focus]:
        """
        Fetch a Focus entity and all its edge selections.

        Args:
            uri: The Focus entity URI
            graph: Named graph to query
            user: User/keyspace identifier
            collection: Collection identifier

        Returns:
            Focus with populated edge_selections, or None
        """
        entity = self.fetch_entity(uri, graph, user, collection)

        if not isinstance(entity, Focus):
            return None

        # Fetch each edge selection
        for edge_uri in entity.selected_edge_uris:
            edge_sel = self.fetch_edge_selection(edge_uri, graph, user, collection)
            if edge_sel:
                entity.edge_selections.append(edge_sel)

        return entity

    def resolve_label(
        self,
        uri: str,
        user: Optional[str] = None,
        collection: Optional[str] = None
    ) -> str:
        """
        Resolve rdfs:label for a URI, with caching.

        Args:
            uri: The URI to get label for
            user: User/keyspace identifier
            collection: Collection identifier

        Returns:
            The label if found, otherwise the URI itself
        """
        if not uri or not uri.startswith(("http://", "https://", "urn:")):
            return uri

        if uri in self._label_cache:
            return self._label_cache[uri]

        wire_triples = self.flow.triples_query(
            s=uri,
            p=RDFS_LABEL,
            user=user,
            collection=collection,
            limit=1
        )

        if wire_triples:
            triples = wire_triples_to_tuples(wire_triples)
            if triples:
                label = triples[0][2]
                self._label_cache[uri] = label
                return label

        self._label_cache[uri] = uri
        return uri

    def resolve_edge_labels(
        self,
        edge: Dict[str, str],
        user: Optional[str] = None,
        collection: Optional[str] = None
    ) -> Tuple[str, str, str]:
        """
        Resolve labels for all components of an edge triple.

        Args:
            edge: Dict with "s", "p", "o" keys
            user: User/keyspace identifier
            collection: Collection identifier

        Returns:
            Tuple of (s_label, p_label, o_label)
        """
        s_label = self.resolve_label(edge.get("s", ""), user, collection)
        p_label = self.resolve_label(edge.get("p", ""), user, collection)
        o_label = self.resolve_label(edge.get("o", ""), user, collection)
        return (s_label, p_label, o_label)

    def fetch_synthesis_content(
        self,
        synthesis: Synthesis,
        api: Any,
        user: Optional[str] = None,
        max_content: int = 10000
    ) -> str:
        """
        Fetch the content for a Synthesis entity.

        If synthesis has inline content, returns that.
        If synthesis has a document_uri, fetches from librarian with retry.

        Args:
            synthesis: The Synthesis entity
            api: TrustGraph Api instance for librarian access
            user: User identifier for librarian
            max_content: Maximum content length to return

        Returns:
            The synthesis content as a string
        """
        # If inline content exists, use it
        if synthesis.content:
            if len(synthesis.content) > max_content:
                return synthesis.content[:max_content] + "... [truncated]"
            return synthesis.content

        # Otherwise fetch from librarian
        if not synthesis.document_uri:
            return ""

        # Extract document ID from URI (e.g., "urn:document:abc123" -> "abc123")
        doc_id = synthesis.document_uri
        if doc_id.startswith("urn:document:"):
            doc_id = doc_id[len("urn:document:"):]

        # Retry fetching from librarian for eventual consistency
        for attempt in range(self.max_retries):
            try:
                library = api.library()
                content_bytes = library.get_document_content(user=user, id=doc_id)

                # Decode as text
                try:
                    content = content_bytes.decode('utf-8')
                    if len(content) > max_content:
                        return content[:max_content] + "... [truncated]"
                    return content
                except UnicodeDecodeError:
                    return f"[Binary: {len(content_bytes)} bytes]"

            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return f"[Error fetching content: {e}]"

        return ""

    def fetch_conclusion_content(
        self,
        conclusion: Conclusion,
        api: Any,
        user: Optional[str] = None,
        max_content: int = 10000
    ) -> str:
        """
        Fetch the content for a Conclusion entity (Agent final answer).

        If conclusion has inline answer, returns that.
        If conclusion has a document_uri, fetches from librarian with retry.

        Args:
            conclusion: The Conclusion entity
            api: TrustGraph Api instance for librarian access
            user: User identifier for librarian
            max_content: Maximum content length to return

        Returns:
            The conclusion answer as a string
        """
        # If inline answer exists, use it
        if conclusion.answer:
            if len(conclusion.answer) > max_content:
                return conclusion.answer[:max_content] + "... [truncated]"
            return conclusion.answer

        # Otherwise fetch from librarian
        if not conclusion.document_uri:
            return ""

        # Use document URI directly (it's already a full URN)
        doc_id = conclusion.document_uri

        # Retry fetching from librarian for eventual consistency
        for attempt in range(self.max_retries):
            try:
                library = api.library()
                content_bytes = library.get_document_content(user=user, id=doc_id)

                # Decode as text
                try:
                    content = content_bytes.decode('utf-8')
                    if len(content) > max_content:
                        return content[:max_content] + "... [truncated]"
                    return content
                except UnicodeDecodeError:
                    return f"[Binary: {len(content_bytes)} bytes]"

            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return f"[Error fetching content: {e}]"

        return ""

    def fetch_analysis_content(
        self,
        analysis: Analysis,
        api: Any,
        user: Optional[str] = None,
        max_content: int = 10000
    ) -> None:
        """
        Fetch thought and observation content for an Analysis entity.

        If analysis has inline content, uses that.
        If analysis has document URIs, fetches from librarian with retry.
        Modifies the analysis object in place.

        Args:
            analysis: The Analysis entity (modified in place)
            api: TrustGraph Api instance for librarian access
            user: User identifier for librarian
            max_content: Maximum content length to return
        """
        # Fetch thought if needed
        if not analysis.thought and analysis.thought_document_uri:
            doc_id = analysis.thought_document_uri
            for attempt in range(self.max_retries):
                try:
                    library = api.library()
                    content_bytes = library.get_document_content(user=user, id=doc_id)
                    try:
                        content = content_bytes.decode('utf-8')
                        if len(content) > max_content:
                            analysis.thought = content[:max_content] + "... [truncated]"
                        else:
                            analysis.thought = content
                        break
                    except UnicodeDecodeError:
                        analysis.thought = f"[Binary: {len(content_bytes)} bytes]"
                        break
                except Exception as e:
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    analysis.thought = f"[Error fetching thought: {e}]"

        # Fetch observation if needed
        if not analysis.observation and analysis.observation_document_uri:
            doc_id = analysis.observation_document_uri
            for attempt in range(self.max_retries):
                try:
                    library = api.library()
                    content_bytes = library.get_document_content(user=user, id=doc_id)
                    try:
                        content = content_bytes.decode('utf-8')
                        if len(content) > max_content:
                            analysis.observation = content[:max_content] + "... [truncated]"
                        else:
                            analysis.observation = content
                        break
                    except UnicodeDecodeError:
                        analysis.observation = f"[Binary: {len(content_bytes)} bytes]"
                        break
                except Exception as e:
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    analysis.observation = f"[Error fetching observation: {e}]"

    def fetch_graphrag_trace(
        self,
        question_uri: str,
        graph: Optional[str] = None,
        user: Optional[str] = None,
        collection: Optional[str] = None,
        api: Any = None,
        max_content: int = 10000
    ) -> Dict[str, Any]:
        """
        Fetch the complete GraphRAG trace starting from a question URI.

        Follows the provenance chain: Question -> Exploration -> Focus -> Synthesis

        Args:
            question_uri: The question entity URI
            graph: Named graph (default: urn:graph:retrieval)
            user: User/keyspace identifier
            collection: Collection identifier
            api: TrustGraph Api instance for librarian access (optional)
            max_content: Maximum content length for synthesis

        Returns:
            Dict with question, exploration, focus, synthesis entities
        """
        if graph is None:
            graph = "urn:graph:retrieval"

        trace = {
            "question": None,
            "exploration": None,
            "focus": None,
            "synthesis": None,
        }

        # Fetch question
        question = self.fetch_entity(question_uri, graph, user, collection)
        if not isinstance(question, Question):
            return trace
        trace["question"] = question

        # Find exploration: ?exploration prov:wasGeneratedBy question_uri
        exploration_triples = self.flow.triples_query(
            p=PROV_WAS_GENERATED_BY,
            o=question_uri,
            g=graph,
            user=user,
            collection=collection,
            limit=10
        )

        if exploration_triples:
            exploration_uris = [
                extract_term_value(t.get("s", {}))
                for t in exploration_triples
            ]
            for exp_uri in exploration_uris:
                exploration = self.fetch_entity(exp_uri, graph, user, collection)
                if isinstance(exploration, Exploration):
                    trace["exploration"] = exploration
                    break

        if not trace["exploration"]:
            return trace

        # Find focus: ?focus prov:wasDerivedFrom exploration_uri
        focus_triples = self.flow.triples_query(
            p=PROV_WAS_DERIVED_FROM,
            o=trace["exploration"].uri,
            g=graph,
            user=user,
            collection=collection,
            limit=10
        )

        if focus_triples:
            focus_uris = [
                extract_term_value(t.get("s", {}))
                for t in focus_triples
            ]
            for focus_uri in focus_uris:
                focus = self.fetch_focus_with_edges(focus_uri, graph, user, collection)
                if focus:
                    trace["focus"] = focus
                    break

        if not trace["focus"]:
            return trace

        # Find synthesis: ?synthesis prov:wasDerivedFrom focus_uri
        synthesis_triples = self.flow.triples_query(
            p=PROV_WAS_DERIVED_FROM,
            o=trace["focus"].uri,
            g=graph,
            user=user,
            collection=collection,
            limit=10
        )

        if synthesis_triples:
            synthesis_uris = [
                extract_term_value(t.get("s", {}))
                for t in synthesis_triples
            ]
            for synth_uri in synthesis_uris:
                synthesis = self.fetch_entity(synth_uri, graph, user, collection)
                if isinstance(synthesis, Synthesis):
                    # Fetch content if needed
                    if api and not synthesis.content and synthesis.document_uri:
                        synthesis.content = self.fetch_synthesis_content(
                            synthesis, api, user, max_content
                        )
                    trace["synthesis"] = synthesis
                    break

        return trace

    def fetch_docrag_trace(
        self,
        question_uri: str,
        graph: Optional[str] = None,
        user: Optional[str] = None,
        collection: Optional[str] = None,
        api: Any = None,
        max_content: int = 10000
    ) -> Dict[str, Any]:
        """
        Fetch the complete DocumentRAG trace starting from a question URI.

        Follows the provenance chain: Question -> Exploration -> Synthesis
        (No Focus step for DocRAG since it doesn't do edge selection)

        Args:
            question_uri: The question entity URI
            graph: Named graph (default: urn:graph:retrieval)
            user: User/keyspace identifier
            collection: Collection identifier
            api: TrustGraph Api instance for librarian access (optional)
            max_content: Maximum content length for synthesis

        Returns:
            Dict with question, exploration, synthesis entities
        """
        if graph is None:
            graph = "urn:graph:retrieval"

        trace = {
            "question": None,
            "exploration": None,
            "synthesis": None,
        }

        # Fetch question
        question = self.fetch_entity(question_uri, graph, user, collection)
        if not isinstance(question, Question):
            return trace
        trace["question"] = question

        # Find exploration: ?exploration prov:wasGeneratedBy question_uri
        exploration_triples = self.flow.triples_query(
            p=PROV_WAS_GENERATED_BY,
            o=question_uri,
            g=graph,
            user=user,
            collection=collection,
            limit=10
        )

        if exploration_triples:
            exploration_uris = [
                extract_term_value(t.get("s", {}))
                for t in exploration_triples
            ]
            for exp_uri in exploration_uris:
                exploration = self.fetch_entity(exp_uri, graph, user, collection)
                if isinstance(exploration, Exploration):
                    trace["exploration"] = exploration
                    break

        if not trace["exploration"]:
            return trace

        # Find synthesis: ?synthesis prov:wasDerivedFrom exploration_uri
        # (DocRAG goes directly from exploration to synthesis, no focus step)
        synthesis_triples = self.flow.triples_query(
            p=PROV_WAS_DERIVED_FROM,
            o=trace["exploration"].uri,
            g=graph,
            user=user,
            collection=collection,
            limit=10
        )

        if synthesis_triples:
            synthesis_uris = [
                extract_term_value(t.get("s", {}))
                for t in synthesis_triples
            ]
            for synth_uri in synthesis_uris:
                synthesis = self.fetch_entity(synth_uri, graph, user, collection)
                if isinstance(synthesis, Synthesis):
                    # Fetch content if needed
                    if api and not synthesis.content and synthesis.document_uri:
                        synthesis.content = self.fetch_synthesis_content(
                            synthesis, api, user, max_content
                        )
                    trace["synthesis"] = synthesis
                    break

        return trace

    def fetch_agent_trace(
        self,
        session_uri: str,
        graph: Optional[str] = None,
        user: Optional[str] = None,
        collection: Optional[str] = None,
        api: Any = None,
        max_content: int = 10000
    ) -> Dict[str, Any]:
        """
        Fetch the complete Agent trace starting from a session URI.

        Follows the provenance chain: Question -> Analysis(s) -> Conclusion

        Args:
            session_uri: The agent session/question URI
            graph: Named graph (default: urn:graph:retrieval)
            user: User/keyspace identifier
            collection: Collection identifier
            api: TrustGraph Api instance for librarian access (optional)
            max_content: Maximum content length for conclusion

        Returns:
            Dict with question, iterations (Analysis list), conclusion entities
        """
        if graph is None:
            graph = "urn:graph:retrieval"

        trace = {
            "question": None,
            "iterations": [],
            "conclusion": None,
        }

        # Fetch question/session
        question = self.fetch_entity(session_uri, graph, user, collection)
        if not isinstance(question, Question):
            return trace
        trace["question"] = question

        # Follow the chain of wasDerivedFrom
        current_uri = session_uri
        max_iterations = 50  # Safety limit

        for _ in range(max_iterations):
            # Find entity derived from current
            derived_triples = self.flow.triples_query(
                p=PROV_WAS_DERIVED_FROM,
                o=current_uri,
                g=graph,
                user=user,
                collection=collection,
                limit=10
            )

            if not derived_triples:
                break

            derived_uri = extract_term_value(derived_triples[0].get("s", {}))
            if not derived_uri:
                break

            entity = self.fetch_entity(derived_uri, graph, user, collection)

            if isinstance(entity, Analysis):
                # Fetch thought/observation content from librarian if needed
                if api:
                    self.fetch_analysis_content(
                        entity, api, user=user, max_content=max_content
                    )
                trace["iterations"].append(entity)
                current_uri = derived_uri
            elif isinstance(entity, Conclusion):
                # Fetch answer content from librarian if needed
                if api and not entity.answer and entity.document_uri:
                    entity.answer = self.fetch_conclusion_content(
                        entity, api, user=user, max_content=max_content
                    )
                trace["conclusion"] = entity
                break
            else:
                # Unknown entity type, stop
                break

        return trace

    def list_sessions(
        self,
        graph: Optional[str] = None,
        user: Optional[str] = None,
        collection: Optional[str] = None,
        limit: int = 50
    ) -> List[Question]:
        """
        List all explainability sessions (questions) in a collection.

        Args:
            graph: Named graph (default: urn:graph:retrieval)
            user: User/keyspace identifier
            collection: Collection identifier
            limit: Maximum number of sessions to return

        Returns:
            List of Question entities sorted by timestamp (newest first)
        """
        if graph is None:
            graph = "urn:graph:retrieval"

        # Query for all triples with predicate = tg:query
        query_triples = self.flow.triples_query(
            p=TG_QUERY,
            g=graph,
            user=user,
            collection=collection,
            limit=limit
        )

        questions = []
        for t in query_triples:
            question_uri = extract_term_value(t.get("s", {}))
            if question_uri:
                entity = self.fetch_entity(question_uri, graph, user, collection)
                if isinstance(entity, Question):
                    questions.append(entity)

        # Sort by timestamp (newest first)
        questions.sort(key=lambda q: q.timestamp or "", reverse=True)

        return questions

    def detect_session_type(
        self,
        session_uri: str,
        graph: Optional[str] = None,
        user: Optional[str] = None,
        collection: Optional[str] = None
    ) -> str:
        """
        Detect whether a session is GraphRAG or Agent type.

        Args:
            session_uri: The session/question URI
            graph: Named graph
            user: User/keyspace identifier
            collection: Collection identifier

        Returns:
            "graphrag" or "agent"
        """
        if graph is None:
            graph = "urn:graph:retrieval"

        # Fast path: check URI pattern
        if "agent" in session_uri:
            return "agent"
        if "question" in session_uri:
            return "graphrag"
        if "docrag" in session_uri:
            return "docrag"

        # Check what's derived from this entity
        derived_triples = self.flow.triples_query(
            p=PROV_WAS_DERIVED_FROM,
            o=session_uri,
            g=graph,
            user=user,
            collection=collection,
            limit=5
        )

        generated_triples = self.flow.triples_query(
            p=PROV_WAS_GENERATED_BY,
            o=session_uri,
            g=graph,
            user=user,
            collection=collection,
            limit=5
        )

        all_child_uris = [
            extract_term_value(t.get("s", {}))
            for t in (derived_triples + generated_triples)
        ]

        for child_uri in all_child_uris:
            entity = self.fetch_entity(child_uri, graph, user, collection)
            if isinstance(entity, Analysis):
                return "agent"
            if isinstance(entity, Exploration):
                return "graphrag"

        return "graphrag"  # Default
