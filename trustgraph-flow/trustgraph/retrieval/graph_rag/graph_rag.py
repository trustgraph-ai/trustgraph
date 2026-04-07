
import asyncio
import hashlib
import json
import logging
import math
import time
import uuid
from collections import OrderedDict
from datetime import datetime

from ... schema import Term, Triple as SchemaTriple, IRI, LITERAL, TRIPLE

# Provenance imports
from trustgraph.provenance import (
    question_uri,
    grounding_uri as make_grounding_uri,
    exploration_uri as make_exploration_uri,
    focus_uri as make_focus_uri,
    synthesis_uri as make_synthesis_uri,
    question_triples,
    grounding_triples,
    exploration_triples,
    focus_triples,
    synthesis_triples,
    set_graph,
    GRAPH_RETRIEVAL, GRAPH_SOURCE,
    TG_CONTAINS, PROV_WAS_DERIVED_FROM,
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

    async def extract_concepts(self, query):
        """Extract key concepts from query for independent embedding."""
        response = await self.rag.prompt_client.prompt(
            "extract-concepts",
            variables={"query": query}
        )

        concepts = []
        if isinstance(response, str):
            for line in response.strip().split('\n'):
                line = line.strip()
                if line:
                    concepts.append(line)

        if self.verbose:
            logger.debug(f"Extracted concepts: {concepts}")

        # Fall back to raw query if extraction returns nothing
        return concepts if concepts else [query]

    async def get_vectors(self, concepts):
        """Embed multiple concepts concurrently."""
        if self.verbose:
            logger.debug("Computing embeddings...")

        qembeds = await self.rag.embeddings_client.embed(concepts)

        if self.verbose:
            logger.debug("Done.")

        return qembeds

    async def get_entities(self, query):
        """
        Extract concepts from query, embed them, and retrieve matching entities.

        Returns:
            tuple: (entities, concepts) where entities is a list of entity URI
                strings and concepts is the list of concept strings extracted
                from the query.
        """

        concepts = await self.extract_concepts(query)

        vectors = await self.get_vectors(concepts)

        if self.verbose:
            logger.debug("Getting entities...")

        # Query entity matches for each concept concurrently
        per_concept_limit = max(
            1, self.entity_limit // len(vectors)
        )

        entity_tasks = [
            self.rag.graph_embeddings_client.query(
                vector=v, limit=per_concept_limit,
                user=self.user, collection=self.collection,
            )
            for v in vectors
        ]

        results = await asyncio.gather(*entity_tasks, return_exceptions=True)

        # Deduplicate while preserving order
        seen = set()
        entities = []
        for result in results:
            if isinstance(result, Exception) or not result:
                continue
            for e in result:
                entity = term_to_string(e.entity)
                if entity not in seen:
                    seen.add(entity)
                    entities.append(entity)

        if self.verbose:
            logger.debug("Entities:")
            for ent in entities:
                logger.debug(f"  {ent}")

        return entities, concepts
        
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
            g="",
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
                    batch_size=20, g="",
                ),
                self.rag.triples_client.query_stream(
                    s=None, p=entity, o=None,
                    limit=limit_per_entity,
                    user=self.user, collection=self.collection,
                    batch_size=20, g="",
                ),
                self.rag.triples_client.query_stream(
                    s=None, p=None, o=entity,
                    limit=limit_per_entity,
                    user=self.user, collection=self.collection,
                    batch_size=20, g="",
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
        """
        Get subgraph by extracting concepts, finding entities, and traversing.

        Returns:
            tuple: (subgraph, entities, concepts) where subgraph is a list of
                (s, p, o) tuples, entities is the seed entity list, and concepts
                is the extracted concept list.
        """

        entities, concepts = await self.get_entities(query)

        if self.verbose:
            logger.debug("Getting subgraph...")

        # Use optimized batch traversal instead of sequential processing
        subgraph = await self.follow_edges_batch(entities, self.max_path_length)

        return list(subgraph), entities, concepts

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
            tuple: (labeled_edges, uri_map, entities, concepts) where:
                - labeled_edges: list of (label_s, label_p, label_o) tuples
                - uri_map: dict mapping edge_id(label_s, label_p, label_o) -> (uri_s, uri_p, uri_o)
                - entities: list of seed entity URI strings
                - concepts: list of concept strings extracted from query
        """
        subgraph, entities, concepts = await self.get_subgraph(query)

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

        return labeled_edges, uri_map, entities, concepts

    async def trace_source_documents(self, edge_uris):
        """
        Trace selected edges back to their source documents via provenance.

        Follows the chain: edge → subgraph (via tg:contains) → chunk →
        page → document (via prov:wasDerivedFrom), all in urn:graph:source.

        Args:
            edge_uris: List of (s, p, o) URI string tuples

        Returns:
            List of unique document titles
        """
        # Step 1: Find subgraphs containing these edges via tg:contains
        subgraph_tasks = []
        for s, p, o in edge_uris:
            quoted = Term(
                type=TRIPLE,
                triple=SchemaTriple(
                    s=Term(type=IRI, iri=s),
                    p=Term(type=IRI, iri=p),
                    o=Term(type=IRI, iri=o),
                )
            )
            subgraph_tasks.append(
                self.rag.triples_client.query(
                    s=None, p=TG_CONTAINS, o=quoted, limit=1,
                    user=self.user, collection=self.collection,
                    g=GRAPH_SOURCE,
                )
            )

        subgraph_results = await asyncio.gather(
            *subgraph_tasks, return_exceptions=True
        )

        # Collect unique subgraph URIs
        subgraph_uris = set()
        for result in subgraph_results:
            if isinstance(result, Exception) or not result:
                continue
            for triple in result:
                subgraph_uris.add(str(triple.s))

        if not subgraph_uris:
            return []

        # Step 2: Walk prov:wasDerivedFrom chain to find documents
        # Each level: query ?entity prov:wasDerivedFrom ?parent
        # Stop when we find entities typed tg:Document
        current_uris = subgraph_uris
        doc_uris = set()

        for depth in range(4):  # Max depth: subgraph → chunk → page → doc
            if not current_uris:
                break

            derivation_tasks = [
                self.rag.triples_client.query(
                    s=uri, p=PROV_WAS_DERIVED_FROM, o=None, limit=5,
                    user=self.user, collection=self.collection,
                    g=GRAPH_SOURCE,
                )
                for uri in current_uris
            ]

            derivation_results = await asyncio.gather(
                *derivation_tasks, return_exceptions=True
            )

            # URIs with no parent are root documents
            next_uris = set()
            for uri, result in zip(current_uris, derivation_results):
                if isinstance(result, Exception) or not result:
                    doc_uris.add(uri)
                    continue
                for triple in result:
                    next_uris.add(str(triple.o))

            current_uris = next_uris - doc_uris

        if not doc_uris:
            return []

        # Step 3: Get all document metadata properties
        # Skip structural predicates that aren't useful context
        SKIP_PREDICATES = {
            PROV_WAS_DERIVED_FROM,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
        }

        metadata_tasks = [
            self.rag.triples_client.query(
                s=uri, p=None, o=None, limit=50,
                user=self.user, collection=self.collection,
            )
            for uri in doc_uris
        ]

        metadata_results = await asyncio.gather(
            *metadata_tasks, return_exceptions=True
        )

        doc_edges = []
        for result in metadata_results:
            if isinstance(result, Exception) or not result:
                continue
            for triple in result:
                p = str(triple.p)
                if p in SKIP_PREDICATES:
                    continue
                doc_edges.append((
                    str(triple.s), p, str(triple.o)
                ))

        return doc_edges

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
            max_path_length = 2, edge_score_limit = 30, edge_limit = 25,
            streaming = False,
            chunk_callback = None,
            explain_callback = None, save_answer_callback = None,
            parent_uri = "",
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
            edge_score_limit: Max edges to pass to LLM scoring (semantic pre-filter)
            edge_limit: Max edges after LLM scoring
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
        gnd_uri = make_grounding_uri(session_id)
        exp_uri = make_exploration_uri(session_id)
        foc_uri = make_focus_uri(session_id)
        syn_uri = make_synthesis_uri(session_id)

        timestamp = datetime.utcnow().isoformat() + "Z"

        # Emit question explainability immediately
        if explain_callback:
            q_triples = set_graph(
                question_triples(
                    q_uri, query, timestamp,
                    parent_uri=parent_uri or None,
                ),
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

        kg, uri_map, seed_entities, concepts = await q.get_labelgraph(query)

        # Emit grounding explain after concept extraction
        if explain_callback:
            gnd_triples = set_graph(
                grounding_triples(gnd_uri, q_uri, concepts),
                GRAPH_RETRIEVAL
            )
            await explain_callback(gnd_triples, gnd_uri)

        # Emit exploration explain after graph retrieval completes
        if explain_callback:
            exp_triples = set_graph(
                exploration_triples(
                    exp_uri, gnd_uri, len(kg),
                    entities=seed_entities,
                ),
                GRAPH_RETRIEVAL
            )
            await explain_callback(exp_triples, exp_uri)

        if self.verbose:
            logger.debug("Invoking LLM...")
            logger.debug(f"Knowledge graph: {kg}")
            logger.debug(f"Query: {query}")

        # Semantic pre-filter: reduce edges before expensive LLM scoring
        if edge_score_limit > 0 and len(kg) > edge_score_limit:

            if self.verbose:
                logger.debug(
                    f"Semantic pre-filter: {len(kg)} edges > "
                    f"limit {edge_score_limit}, filtering..."
                )

            # Embed edge descriptions: "subject, predicate, object"
            edge_descriptions = [
                f"{s}, {p}, {o}" for s, p, o in kg
            ]

            # Embed concepts and edge descriptions concurrently
            concept_embed_task = self.embeddings_client.embed(concepts)
            edge_embed_task = self.embeddings_client.embed(edge_descriptions)

            concept_vectors, edge_vectors = await asyncio.gather(
                concept_embed_task, edge_embed_task
            )

            # Score each edge by max cosine similarity to any concept
            def cosine_similarity(a, b):
                dot = sum(x * y for x, y in zip(a, b))
                norm_a = math.sqrt(sum(x * x for x in a))
                norm_b = math.sqrt(sum(x * x for x in b))
                if norm_a == 0 or norm_b == 0:
                    return 0.0
                return dot / (norm_a * norm_b)

            edge_scores = []
            for i, edge_vec in enumerate(edge_vectors):
                max_sim = max(
                    cosine_similarity(edge_vec, cv)
                    for cv in concept_vectors
                )
                edge_scores.append((max_sim, i))

            # Sort by similarity descending and keep top edge_score_limit
            edge_scores.sort(reverse=True)
            keep_indices = set(
                idx for _, idx in edge_scores[:edge_score_limit]
            )

            # Filter kg and rebuild uri_map
            filtered_kg = []
            filtered_uri_map = {}
            for i, (s, p, o) in enumerate(kg):
                if i in keep_indices:
                    filtered_kg.append((s, p, o))
                    eid = edge_id(s, p, o)
                    if eid in uri_map:
                        filtered_uri_map[eid] = uri_map[eid]

            if self.verbose:
                logger.debug(
                    f"Semantic pre-filter kept {len(filtered_kg)} "
                    f"of {len(kg)} edges"
                )

            kg = filtered_kg
            uri_map = filtered_uri_map

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

        # Step 1a: Edge Scoring - LLM scores edges for relevance
        scoring_response = await self.prompt_client.prompt(
            "kg-edge-scoring",
            variables={
                "query": query,
                "knowledge": edges_with_ids
            }
        )

        if self.verbose:
            logger.debug(f"Edge scoring response: {scoring_response}")

        # Parse scoring response to get edge IDs with scores
        scored_edges = []

        def parse_scored_edge(obj):
            if isinstance(obj, dict) and "id" in obj and "score" in obj:
                try:
                    score = int(obj["score"])
                except (ValueError, TypeError):
                    score = 0
                scored_edges.append({"id": obj["id"], "score": score})

        if isinstance(scoring_response, list):
            for obj in scoring_response:
                parse_scored_edge(obj)
        elif isinstance(scoring_response, str):
            for line in scoring_response.strip().split('\n'):
                line = line.strip()
                if not line:
                    continue
                try:
                    parse_scored_edge(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(
                        f"Failed to parse edge scoring line: {line}"
                    )

        # Select top N edges by score
        scored_edges.sort(key=lambda x: x["score"], reverse=True)
        top_edges = scored_edges[:edge_limit]
        selected_ids = {e["id"] for e in top_edges}

        if self.verbose:
            logger.debug(
                f"Scored {len(scored_edges)} edges, "
                f"selected top {len(selected_ids)}"
            )

        # Filter to selected edges
        selected_edges = []
        for eid in selected_ids:
            if eid in edge_map:
                selected_edges.append(edge_map[eid])

        # Step 1b: Edge Reasoning + Document Tracing (concurrent)
        selected_edges_with_ids = [
            {"id": eid, "s": s, "p": p, "o": o}
            for eid in selected_ids
            if eid in edge_map
            for s, p, o in [edge_map[eid]]
        ]

        # Collect selected edge URIs for document tracing
        selected_edge_uris = [
            uri_map[eid]
            for eid in selected_ids
            if eid in uri_map
        ]

        # Run reasoning and document tracing concurrently
        reasoning_task = self.prompt_client.prompt(
            "kg-edge-reasoning",
            variables={
                "query": query,
                "knowledge": selected_edges_with_ids
            }
        )
        doc_trace_task = q.trace_source_documents(selected_edge_uris)

        reasoning_response, source_documents = await asyncio.gather(
            reasoning_task, doc_trace_task, return_exceptions=True
        )

        # Handle exceptions from gather
        if isinstance(reasoning_response, Exception):
            logger.warning(
                f"Edge reasoning failed: {reasoning_response}"
            )
            reasoning_response = ""
        if isinstance(source_documents, Exception):
            logger.warning(
                f"Document tracing failed: {source_documents}"
            )
            source_documents = []


        if self.verbose:
            logger.debug(f"Edge reasoning response: {reasoning_response}")

        # Parse reasoning response and build explainability data
        reasoning_map = {}

        def parse_reasoning(obj):
            if isinstance(obj, dict) and "id" in obj:
                reasoning_map[obj["id"]] = obj.get("reasoning", "")

        if isinstance(reasoning_response, list):
            for obj in reasoning_response:
                parse_reasoning(obj)
        elif isinstance(reasoning_response, str):
            for line in reasoning_response.strip().split('\n'):
                line = line.strip()
                if not line:
                    continue
                try:
                    parse_reasoning(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(
                        f"Failed to parse edge reasoning line: {line}"
                    )

        selected_edges_with_reasoning = []
        for eid in selected_ids:
            if eid in uri_map:
                uri_s, uri_p, uri_o = uri_map[eid]
                selected_edges_with_reasoning.append({
                    "edge": (uri_s, uri_p, uri_o),
                    "reasoning": reasoning_map.get(eid, ""),
                })

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

        # Add source document metadata as knowledge edges
        for s, p, o in source_documents:
            selected_edge_dicts.append({
                "s": s, "p": p, "o": o,
            })

        synthesis_variables = {
            "query": query,
            "knowledge": selected_edge_dicts,
        }

        if streaming and chunk_callback:
            # Accumulate chunks for answer storage while forwarding to callback
            accumulated_chunks = []

            async def accumulating_callback(chunk, end_of_stream):
                accumulated_chunks.append(chunk)
                await chunk_callback(chunk, end_of_stream)

            await self.prompt_client.prompt(
                "kg-synthesis",
                variables=synthesis_variables,
                streaming=True,
                chunk_callback=accumulating_callback
            )
            # Combine all chunks into full response
            resp = "".join(accumulated_chunks)
        else:
            resp = await self.prompt_client.prompt(
                "kg-synthesis",
                variables=synthesis_variables,
            )

        if self.verbose:
            logger.debug("Query processing complete")

        # Emit synthesis explain after synthesis completes
        if explain_callback:
            synthesis_doc_id = None
            answer_text = resp if resp else ""

            # Save answer to librarian
            if save_answer_callback and answer_text:
                synthesis_doc_id = f"urn:trustgraph:synthesis:{session_id}"
                try:
                    await save_answer_callback(synthesis_doc_id, answer_text)
                    if self.verbose:
                        logger.debug(f"Saved answer to librarian: {synthesis_doc_id}")
                except Exception as e:
                    logger.warning(f"Failed to save answer to librarian: {e}")
                    synthesis_doc_id = None

            syn_triples = set_graph(
                synthesis_triples(
                    syn_uri, foc_uri,
                    document_id=synthesis_doc_id,
                ),
                GRAPH_RETRIEVAL
            )
            await explain_callback(syn_triples, syn_uri)

        if self.verbose:
            logger.debug(f"Emitted explain for session {session_id}")

        return resp

