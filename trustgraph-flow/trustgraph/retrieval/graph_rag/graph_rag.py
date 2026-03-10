
import asyncio
import hashlib
import json
import logging
import time
import uuid
from collections import OrderedDict
from datetime import datetime

from ... schema import IRI, LITERAL

# Provenance imports
from trustgraph.provenance import (
    question_uri,
    exploration_uri as make_exploration_uri,
    focus_uri as make_focus_uri,
    synthesis_uri as make_synthesis_uri,
    question_triples,
    exploration_triples,
    focus_triples,
    synthesis_triples,
    set_graph,
    GRAPH_RETRIEVAL,
)

# Module logger
logger = logging.getLogger(__name__)

LABEL="http://www.w3.org/2000/01/rdf-schema#label"


def term_to_string(term):
    """Extract string value from a Term object."""
    if term is None:
        return None
    if term.type == IRI:
        return term.iri
    elif term.type == LITERAL:
        return term.value
    # Fallback
    return term.iri or term.value or str(term)


def edge_id(s, p, o):
    """Generate an 8-character hash ID for an edge (s, p, o)."""
    edge_str = f"{s}|{p}|{o}"
    return hashlib.sha256(edge_str.encode()).hexdigest()[:8]

class LRUCacheWithTTL:
    """LRU cache with TTL for label caching

    CRITICAL SECURITY WARNING:
    This cache is shared within a GraphRag instance but GraphRag instances
    are created per-request. Cache keys MUST include user:collection prefix
    to ensure data isolation between different security contexts.
    """

    def __init__(self, max_size=5000, ttl=300):
        self.cache = OrderedDict()
        self.access_times = {}
        self.max_size = max_size
        self.ttl = ttl

    def get(self, key):
        if key not in self.cache:
            return None

        # Check TTL expiration
        if time.time() - self.access_times[key] > self.ttl:
            del self.cache[key]
            del self.access_times[key]
            return None

        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.max_size:
                # Remove least recently used
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                del self.access_times[oldest_key]

        self.cache[key] = value
        self.access_times[key] = time.time()

class Query:

    def __init__(
            self, rag, user, collection, verbose,
            entity_limit=50, triple_limit=30, max_subgraph_size=1000,
            max_path_length=2,
    ):
        self.rag = rag
        self.user = user
        self.collection = collection
        self.verbose = verbose
        self.entity_limit = entity_limit
        self.triple_limit = triple_limit
        self.max_subgraph_size = max_subgraph_size
        self.max_path_length = max_path_length

    async def get_vector(self, query):

        if self.verbose:
            logger.debug("Computing embeddings...")

        qembeds = await self.rag.embeddings_client.embed([query])

        if self.verbose:
            logger.debug("Done.")

        # Return the vector set for the first (only) text
        return qembeds[0] if qembeds else []

    async def get_entities(self, query):

        vectors = await self.get_vector(query)

        if self.verbose:
            logger.debug("Getting entities...")

        entity_matches = await self.rag.graph_embeddings_client.query(
            vector=vectors, limit=self.entity_limit,
            user=self.user, collection=self.collection,
        )

        entities = [
            term_to_string(e.entity)
            for e in entity_matches
        ]

        if self.verbose:
            logger.debug("Entities:")
            for ent in entities:
                logger.debug(f"  {ent}")

        return entities
        
    async def maybe_label(self, e):

        # CRITICAL SECURITY: Cache key MUST include user and collection
        # to prevent data leakage between different contexts
        cache_key = f"{self.user}:{self.collection}:{e}"

        # Check LRU cache first with isolated key
        cached_label = self.rag.label_cache.get(cache_key)
        if cached_label is not None:
            return cached_label

        res = await self.rag.triples_client.query(
            s=e, p=LABEL, o=None, limit=1,
            user=self.user, collection=self.collection,
        )

        if len(res) == 0:
            self.rag.label_cache.put(cache_key, e)
            return e

        label = str(res[0].o)
        self.rag.label_cache.put(cache_key, label)
        return label

    async def execute_batch_triple_queries(self, entities, limit_per_entity):
        """Execute triple queries for multiple entities concurrently using streaming"""
        tasks = []

        for entity in entities:
            # Create concurrent streaming tasks for all 3 query types per entity
            tasks.extend([
                self.rag.triples_client.query_stream(
                    s=entity, p=None, o=None,
                    limit=limit_per_entity,
                    user=self.user, collection=self.collection,
                    batch_size=20,
                ),
                self.rag.triples_client.query_stream(
                    s=None, p=entity, o=None,
                    limit=limit_per_entity,
                    user=self.user, collection=self.collection,
                    batch_size=20,
                ),
                self.rag.triples_client.query_stream(
                    s=None, p=None, o=entity,
                    limit=limit_per_entity,
                    user=self.user, collection=self.collection,
                    batch_size=20,
                )
            ])

        # Execute all queries concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine all results
        all_triples = []
        for result in results:
            if not isinstance(result, Exception) and result is not None:
                all_triples.extend(result)

        return all_triples

    async def follow_edges_batch(self, entities, max_depth):
        """Optimized iterative graph traversal with batching"""
        visited = set()
        current_level = set(entities)
        subgraph = set()

        for depth in range(max_depth):
            if not current_level or len(subgraph) >= self.max_subgraph_size:
                break

            # Filter out already visited entities
            unvisited_entities = [e for e in current_level if e not in visited]
            if not unvisited_entities:
                break

            # Batch query all unvisited entities at current level
            triples = await self.execute_batch_triple_queries(
                unvisited_entities, self.triple_limit
            )

            # Process results and collect next level entities
            next_level = set()
            for triple in triples:
                triple_tuple = (str(triple.s), str(triple.p), str(triple.o))
                subgraph.add(triple_tuple)

                # Collect entities for next level (only from s and o positions)
                if depth < max_depth - 1:  # Don't collect for final depth
                    s, p, o = triple_tuple
                    if s not in visited:
                        next_level.add(s)
                    if o not in visited:
                        next_level.add(o)

                # Stop if subgraph size limit reached
                if len(subgraph) >= self.max_subgraph_size:
                    return subgraph

            # Update for next iteration
            visited.update(current_level)
            current_level = next_level

        return subgraph

    async def follow_edges(self, ent, subgraph, path_length):
        """Legacy method - replaced by follow_edges_batch"""
        # Maintain backward compatibility with early termination checks
        if path_length <= 0:
            return

        if len(subgraph) >= self.max_subgraph_size:
            return

        # For backward compatibility, convert to new approach
        batch_result = await self.follow_edges_batch([ent], path_length)
        subgraph.update(batch_result)

    async def get_subgraph(self, query):

        entities = await self.get_entities(query)

        if self.verbose:
            logger.debug("Getting subgraph...")

        # Use optimized batch traversal instead of sequential processing
        subgraph = await self.follow_edges_batch(entities, self.max_path_length)

        return list(subgraph)

    async def resolve_labels_batch(self, entities):
        """Resolve labels for multiple entities in parallel"""
        tasks = []
        for entity in entities:
            tasks.append(self.maybe_label(entity))

        return await asyncio.gather(*tasks, return_exceptions=True)

    async def get_labelgraph(self, query):
        """
        Get subgraph with labels resolved for display.

        Returns:
            tuple: (labeled_edges, uri_map) where:
                - labeled_edges: list of (label_s, label_p, label_o) tuples
                - uri_map: dict mapping edge_id(label_s, label_p, label_o) -> (uri_s, uri_p, uri_o)
        """
        subgraph = await self.get_subgraph(query)

        # Filter out label triples
        filtered_subgraph = [edge for edge in subgraph if edge[1] != LABEL]

        # Collect all unique entities that need label resolution
        entities_to_resolve = set()
        for s, p, o in filtered_subgraph:
            entities_to_resolve.update([s, p, o])

        # Batch resolve labels for all entities in parallel
        entity_list = list(entities_to_resolve)
        resolved_labels = await self.resolve_labels_batch(entity_list)

        # Create entity-to-label mapping
        label_map = {}
        for entity, label in zip(entity_list, resolved_labels):
            if not isinstance(label, Exception):
                label_map[entity] = label
            else:
                label_map[entity] = entity  # Fallback to entity itself

        # Apply labels to subgraph and build URI mapping
        labeled_edges = []
        uri_map = {}  # Maps edge_id of labeled edge -> original URI triple

        for s, p, o in filtered_subgraph:
            labeled_triple = (
                label_map.get(s, s),
                label_map.get(p, p),
                label_map.get(o, o)
            )
            labeled_edges.append(labeled_triple)

            # Map from labeled edge ID to original URIs
            labeled_eid = edge_id(labeled_triple[0], labeled_triple[1], labeled_triple[2])
            uri_map[labeled_eid] = (s, p, o)

        labeled_edges = labeled_edges[0:self.max_subgraph_size]

        if self.verbose:
            logger.debug("Subgraph:")
            for edge in labeled_edges:
                logger.debug(f"  {str(edge)}")

        if self.verbose:
            logger.debug("Done.")

        return labeled_edges, uri_map
    
class GraphRag:
    """
    CRITICAL SECURITY:
    This class MUST be instantiated per-request to ensure proper isolation
    between users and collections. The cache within this instance will only
    live for the duration of a single request, preventing cross-contamination
    of data between different security contexts.
    """

    def __init__(
            self, prompt_client, embeddings_client, graph_embeddings_client,
            triples_client, verbose=False,
    ):

        self.verbose = verbose

        self.prompt_client = prompt_client
        self.embeddings_client = embeddings_client
        self.graph_embeddings_client = graph_embeddings_client
        self.triples_client = triples_client

        # Replace simple dict with LRU cache with TTL
        # CRITICAL: This cache only lives for one request due to per-request instantiation
        self.label_cache = LRUCacheWithTTL(max_size=5000, ttl=300)

        if self.verbose:
            logger.debug("GraphRag initialized")

    async def query(
            self, query, user = "trustgraph", collection = "default",
            entity_limit = 50, triple_limit = 30, max_subgraph_size = 1000,
            max_path_length = 2, streaming = False, chunk_callback = None,
            explain_callback = None, save_answer_callback = None,
    ):
        """
        Execute a GraphRAG query with real-time explainability tracking.

        Args:
            query: The query string
            user: User identifier
            collection: Collection identifier
            entity_limit: Max entities to retrieve
            triple_limit: Max triples per entity
            max_subgraph_size: Max edges in subgraph
            max_path_length: Max hops from seed entities
            streaming: Enable streaming LLM response
            chunk_callback: async def callback(chunk, end_of_stream) for streaming
            explain_callback: async def callback(triples, explain_id) for real-time explainability
            save_answer_callback: async def callback(doc_id, answer_text) -> doc_id to save answer to librarian

        Returns:
            str: The synthesized answer text
        """
        if self.verbose:
            logger.debug("Constructing prompt...")

        # Generate explainability URIs upfront
        session_id = str(uuid.uuid4())
        q_uri = question_uri(session_id)
        exp_uri = make_exploration_uri(session_id)
        foc_uri = make_focus_uri(session_id)
        syn_uri = make_synthesis_uri(session_id)

        timestamp = datetime.utcnow().isoformat() + "Z"

        # Emit question explainability immediately
        if explain_callback:
            q_triples = set_graph(
                question_triples(q_uri, query, timestamp),
                GRAPH_RETRIEVAL
            )
            await explain_callback(q_triples, q_uri)

        q = Query(
            rag = self, user = user, collection = collection,
            verbose = self.verbose, entity_limit = entity_limit,
            triple_limit = triple_limit,
            max_subgraph_size = max_subgraph_size,
            max_path_length = max_path_length,
        )

        kg, uri_map = await q.get_labelgraph(query)

        # Emit exploration explain after graph retrieval completes
        if explain_callback:
            exp_triples = set_graph(
                exploration_triples(exp_uri, q_uri, len(kg)),
                GRAPH_RETRIEVAL
            )
            await explain_callback(exp_triples, exp_uri)

        if self.verbose:
            logger.debug("Invoking LLM...")
            logger.debug(f"Knowledge graph: {kg}")
            logger.debug(f"Query: {query}")

        # Build edge map: {hash_id: (labeled_s, labeled_p, labeled_o)}
        # uri_map already maps edge_id -> (uri_s, uri_p, uri_o)
        edge_map = {}
        edges_with_ids = []
        for s, p, o in kg:
            eid = edge_id(s, p, o)
            edge_map[eid] = (s, p, o)
            edges_with_ids.append({
                "id": eid,
                "s": s,
                "p": p,
                "o": o
            })

        if self.verbose:
            logger.debug(f"Built edge map with {len(edge_map)} edges")

        # Step 1: Edge Selection - LLM selects relevant edges with reasoning
        selection_response = await self.prompt_client.prompt(
            "kg-edge-selection",
            variables={
                "query": query,
                "knowledge": edges_with_ids
            }
        )

        if self.verbose:
            logger.debug(f"Edge selection response: {selection_response}")

        # Parse response to get selected edge IDs and reasoning
        # Response can be a string (JSONL) or a list (JSON array)
        selected_ids = set()
        selected_edges_with_reasoning = []  # For explain

        if isinstance(selection_response, list):
            # JSON array response
            for obj in selection_response:
                if isinstance(obj, dict) and "id" in obj:
                    selected_ids.add(obj["id"])
                    # Capture original URI edge (not labels) and reasoning for explain
                    eid = obj["id"]
                    if eid in uri_map:
                        # Use original URIs for provenance tracing
                        uri_s, uri_p, uri_o = uri_map[eid]
                        selected_edges_with_reasoning.append({
                            "edge": (uri_s, uri_p, uri_o),
                            "reasoning": obj.get("reasoning", ""),
                        })
        elif isinstance(selection_response, str):
            # JSONL string response
            for line in selection_response.strip().split('\n'):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if "id" in obj:
                        selected_ids.add(obj["id"])
                        # Capture original URI edge (not labels) and reasoning for explain
                        eid = obj["id"]
                        if eid in uri_map:
                            # Use original URIs for provenance tracing
                            uri_s, uri_p, uri_o = uri_map[eid]
                            selected_edges_with_reasoning.append({
                                "edge": (uri_s, uri_p, uri_o),
                                "reasoning": obj.get("reasoning", ""),
                            })
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse edge selection line: {line}")
                    continue

        if self.verbose:
            logger.debug(f"Selected {len(selected_ids)} edges: {selected_ids}")

        # Filter to selected edges
        selected_edges = []
        for eid in selected_ids:
            if eid in edge_map:
                selected_edges.append(edge_map[eid])

        if self.verbose:
            logger.debug(f"Filtered to {len(selected_edges)} edges")

        # Emit focus explain after edge selection completes
        if explain_callback:
            foc_triples = set_graph(
                focus_triples(
                    foc_uri, exp_uri, selected_edges_with_reasoning, session_id
                ),
                GRAPH_RETRIEVAL
            )
            await explain_callback(foc_triples, foc_uri)

        # Step 2: Synthesis - LLM generates answer from selected edges only
        selected_edge_dicts = [
            {"s": s, "p": p, "o": o}
            for s, p, o in selected_edges
        ]
        if streaming and chunk_callback:
            # Accumulate chunks for answer storage while forwarding to callback
            accumulated_chunks = []

            async def accumulating_callback(chunk, end_of_stream):
                accumulated_chunks.append(chunk)
                await chunk_callback(chunk, end_of_stream)

            await self.prompt_client.prompt(
                "kg-synthesis",
                variables={
                    "query": query,
                    "knowledge": selected_edge_dicts
                },
                streaming=True,
                chunk_callback=accumulating_callback
            )
            # Combine all chunks into full response
            resp = "".join(accumulated_chunks)
        else:
            resp = await self.prompt_client.prompt(
                "kg-synthesis",
                variables={
                    "query": query,
                    "knowledge": selected_edge_dicts
                }
            )

        if self.verbose:
            logger.debug("Query processing complete")

        # Emit synthesis explain after synthesis completes
        if explain_callback:
            synthesis_doc_id = None
            answer_text = resp if resp else ""

            # Save answer to librarian if callback provided
            if save_answer_callback and answer_text:
                # Generate document ID as URN matching query-time provenance format
                synthesis_doc_id = f"urn:trustgraph:synthesis:{session_id}"
                try:
                    await save_answer_callback(synthesis_doc_id, answer_text)
                    if self.verbose:
                        logger.debug(f"Saved answer to librarian: {synthesis_doc_id}")
                except Exception as e:
                    logger.warning(f"Failed to save answer to librarian: {e}")
                    synthesis_doc_id = None  # Fall back to inline content

            # Generate triples with document reference or inline content
            syn_triples = set_graph(
                synthesis_triples(
                    syn_uri, foc_uri,
                    answer_text="" if synthesis_doc_id else answer_text,
                    document_id=synthesis_doc_id,
                ),
                GRAPH_RETRIEVAL
            )
            await explain_callback(syn_triples, syn_uri)

        if self.verbose:
            logger.debug(f"Emitted explain for session {session_id}")

        return resp

