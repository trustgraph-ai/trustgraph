
import asyncio
import hashlib
import json
import logging
import math
import time
import uuid
from collections import OrderedDict
from datetime import datetime, timezone

from ... schema import Term, Triple as SchemaTriple, IRI, LITERAL, TRIPLE
from ... knowledge import Uri, Literal

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

RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#"
OWL_NS = "http://www.w3.org/2002/07/owl#"
RDF_TYPE = RDF_NS + "type"
SCHEMA_NAMESPACES = (RDF_NS, RDFS_NS, OWL_NS)


def is_schema_predicate(predicate):
    """Return True if the predicate is an RDF/RDFS/OWL schema predicate.

    rdf:type is excluded from filtering as it carries useful data signal.
    """
    if predicate == RDF_TYPE:
        return False
    return predicate.startswith(SCHEMA_NAMESPACES)


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


def to_term(val):
    """Convert a Uri, Literal, or string to a schema Term.

    The triples client returns Uri/Literal (str subclasses) rather than
    Term objects. This converts them back so provenance quoted triples
    preserve the correct type.
    """
    if isinstance(val, Term):
        return val
    if isinstance(val, Uri):
        return Term(type=IRI, iri=str(val))
    if isinstance(val, Literal):
        return Term(type=LITERAL, value=str(val))
    # Fallback: treat as IRI if it looks like one, otherwise literal
    s = str(val)
    if s.startswith(("http://", "https://", "urn:")):
        return Term(type=IRI, iri=s)
    return Term(type=LITERAL, value=s)


def edge_id(s, p, o):
    """Generate an 8-character hash ID for an edge (s, p, o)."""
    edge_str = f"{s}|{p}|{o}"
    return hashlib.sha256(edge_str.encode()).hexdigest()[:8]



class LRUCacheWithTTL:
    """LRU cache with TTL for label caching.

    GraphRag instances are created per-request, so this cache is
    request-scoped. Cache keys include the collection prefix to keep
    entries from different collections distinct within one request.
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
            self, rag, collection, verbose,
            entity_limit=50, triple_limit=30, max_subgraph_size=1000,
            max_path_length=2, edge_limit=25, max_reranker_input=350,
            track_usage=None,
    ):
        self.rag = rag
        self.collection = collection
        self.verbose = verbose
        self.entity_limit = entity_limit
        self.triple_limit = triple_limit
        self.max_subgraph_size = max_subgraph_size
        self.max_path_length = max_path_length
        self.edge_limit = edge_limit
        self.max_reranker_input = max_reranker_input
        self.track_usage = track_usage

    async def extract_concepts(self, query):
        """Extract key concepts from query for independent embedding."""
        result = await self.rag.prompt_client.prompt(
            "extract-concepts",
            variables={"query": query}
        )
        if self.track_usage:
            self.track_usage(result)

        concepts = []
        if result.text:
            for line in result.text.strip().split('\n'):
                line = line.strip()
                if line:
                    concepts.append(line)

        if self.verbose:
            logger.debug(f"Extracted concepts: {concepts}")

        self.concepts_usage = result

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
                collection=self.collection,
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

        cache_key = f"{self.collection}:{e}"

        cached_label = self.rag.label_cache.get(cache_key)
        if cached_label is not None:
            return cached_label

        res = await self.rag.triples_client.query(
            s=e, p=LABEL, o=None, limit=1,
            collection=self.collection,
            g="",
        )

        if len(res) == 0:
            self.rag.label_cache.put(cache_key, e)
            return e

        label = str(res[0].o)
        self.rag.label_cache.put(cache_key, label)
        return label

    FROM_S = "from_s"
    FROM_P = "from_p"
    FROM_O = "from_o"

    async def execute_batch_triple_queries(self, entities, limit_per_entity):
        """Execute triple queries for multiple entities concurrently.

        Returns a list of (triple, direction) tuples where direction
        indicates which position the frontier entity occupied.
        """
        tasks = []
        directions = []

        for entity in entities:
            tasks.append(
                self.rag.triples_client.query_stream(
                    s=entity, p=None, o=None,
                    limit=limit_per_entity,
                    collection=self.collection,
                    batch_size=20, g="",
                ),
            )
            directions.append(self.FROM_S)

            tasks.append(
                self.rag.triples_client.query_stream(
                    s=None, p=entity, o=None,
                    limit=limit_per_entity,
                    collection=self.collection,
                    batch_size=20, g="",
                ),
            )
            directions.append(self.FROM_P)

            tasks.append(
                self.rag.triples_client.query_stream(
                    s=None, p=None, o=entity,
                    limit=limit_per_entity,
                    collection=self.collection,
                    batch_size=20, g="",
                ),
            )
            directions.append(self.FROM_O)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_triples = []
        for direction, result in zip(directions, results):
            if not isinstance(result, Exception) and result is not None:
                all_triples.extend((triple, direction) for triple in result)

        return all_triples

    async def resolve_labels_batch(self, entities):
        """Resolve labels for multiple entities in parallel."""
        tasks = [self.maybe_label(entity) for entity in entities]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def hop_and_filter(self, seed_entities, concepts):
        """Iterative hop-and-filter graph traversal with cross-encoder.

        At each hop:
        1. Retrieve all edges one hop from the frontier.
        2. Resolve labels and represent each edge as "{p} {o}".
        3. Score edges against concepts using the cross-encoder.
        4. Select the top edges; their target nodes become the next
           frontier.

        Returns:
            tuple: (selected_edges, uri_map, edge_metadata) where:
                - selected_edges: list of (label_s, label_p, label_o)
                - uri_map: dict mapping edge_id -> (Term, Term, Term)
                - edge_metadata: dict mapping edge_id -> {concept, score}
        """
        all_selected_edges = []
        uri_map = {}
        edge_metadata = {}
        frontier = set(seed_entities)
        visited_entities = set()
        seen_edges = set()

        for hop in range(self.max_path_length):
            if not frontier:
                break

            unvisited = [e for e in frontier if e not in visited_entities]
            if not unvisited:
                break

            if self.verbose:
                logger.debug(
                    f"Hop {hop + 1}: {len(unvisited)} frontier entities"
                )

            # Retrieve edges one hop from frontier
            triples = await self.execute_batch_triple_queries(
                unvisited, self.triple_limit,
            )

            # Deduplicate and filter already-seen edges
            hop_triples = []
            hop_term_map = {}
            hop_directions = {}
            for triple, direction in triples:
                triple_tuple = (str(triple.s), str(triple.p), str(triple.o))
                if is_schema_predicate(triple_tuple[1]):
                    continue
                if triple_tuple in seen_edges:
                    continue
                seen_edges.add(triple_tuple)
                hop_triples.append(triple_tuple)
                hop_term_map[triple_tuple] = (
                    to_term(triple.s), to_term(triple.p), to_term(triple.o),
                )
                hop_directions[triple_tuple] = direction

            if not hop_triples:
                visited_entities.update(frontier)
                break

            if self.verbose:
                logger.debug(
                    f"Hop {hop + 1}: {len(hop_triples)} candidate edges"
                )

            # Resolve labels for all entities in hop edges
            entities_to_resolve = set()
            for s, p, o in hop_triples:
                entities_to_resolve.update([s, p, o])

            entity_list = list(entities_to_resolve)
            resolved = await self.resolve_labels_batch(entity_list)

            label_map = {}
            for entity, label in zip(entity_list, resolved):
                if not isinstance(label, Exception):
                    label_map[entity] = label
                else:
                    label_map[entity] = entity

            # Build labeled edges and documents for cross-encoder.
            # The reranker text highlights the NEW information relative
            # to the traversal direction: arriving from S means p,o are
            # new; from O means s,p are new; from P means s,o are new.
            # Edges where the reranker-visible components are unlabeled
            # IRIs are skipped — the cross-encoder can't score them.
            def is_iri(val):
                return val.startswith(("http://", "https://", "urn:"))

            filtered_triples = []
            labeled_hop = []
            documents = []
            for s, p, o in hop_triples:
                ls = label_map.get(s, s)
                lp = label_map.get(p, p)
                lo = label_map.get(o, o)

                direction = hop_directions[(s, p, o)]
                if direction == self.FROM_S:
                    if is_iri(lp) or is_iri(lo):
                        continue
                    text = f"{lp} {lo}"
                elif direction == self.FROM_O:
                    if is_iri(ls) or is_iri(lp):
                        continue
                    text = f"{ls} {lp}"
                else:
                    if is_iri(ls) or is_iri(lo):
                        continue
                    text = f"{ls} {lo}"

                idx = len(filtered_triples)
                filtered_triples.append((s, p, o))
                labeled_hop.append((ls, lp, lo))
                documents.append({"id": str(idx), "text": text})

            hop_triples = filtered_triples

            # Cap the number of candidates sent to the reranker
            if len(hop_triples) > self.max_reranker_input:
                if self.verbose:
                    logger.debug(
                        f"Hop {hop + 1}: truncating {len(hop_triples)} "
                        f"candidates to {self.max_reranker_input}"
                    )
                hop_triples = hop_triples[:self.max_reranker_input]
                labeled_hop = labeled_hop[:self.max_reranker_input]
                documents = documents[:self.max_reranker_input]

            queries = [
                {"id": str(i), "text": c}
                for i, c in enumerate(concepts)
            ]

            # Score with cross-encoder
            results = await self.rag.reranker_client.rerank(
                queries=queries,
                documents=documents,
                limit=self.edge_limit,
            )

            # Collect selected edges and metadata
            next_frontier = set()
            for r in results:
                idx = int(r.document_id)
                ls, lp, lo = labeled_hop[idx]
                s, p, o = hop_triples[idx]
                eid = edge_id(ls, lp, lo)

                all_selected_edges.append((ls, lp, lo))
                uri_map[eid] = hop_term_map[(s, p, o)]
                edge_metadata[eid] = {
                    "concept": concepts[int(r.query_id)],
                    "score": r.score,
                }

                # Target nodes become next frontier
                next_frontier.add(s)
                next_frontier.add(o)

            if self.verbose:
                logger.debug(
                    f"Hop {hop + 1}: selected {len(results)} edges"
                )

            visited_entities.update(frontier)
            frontier = next_frontier - visited_entities

        return all_selected_edges, uri_map, edge_metadata

    async def trace_source_documents(self, edge_uris):
        """
        Trace selected edges back to their source documents via provenance.

        Follows the chain: edge -> subgraph (via tg:contains) -> chunk ->
        page -> document (via prov:wasDerivedFrom), all in urn:graph:source.

        Args:
            edge_uris: List of (s, p, o) URI string tuples

        Returns:
            List of unique document titles
        """
        # Step 1: Find subgraphs containing these edges via tg:contains
        subgraph_tasks = []
        for s, p, o in edge_uris:
            s_term = s if isinstance(s, Term) else Term(type=IRI, iri=s)
            p_term = p if isinstance(p, Term) else Term(type=IRI, iri=p)
            o_term = o if isinstance(o, Term) else Term(type=IRI, iri=o)
            quoted = Term(
                type=TRIPLE,
                triple=SchemaTriple(
                    s=s_term, p=p_term, o=o_term,
                )
            )
            subgraph_tasks.append(
                self.rag.triples_client.query(
                    s=None, p=TG_CONTAINS, o=quoted, limit=1,
                    collection=self.collection,
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
        current_uris = subgraph_uris
        doc_uris = set()

        for depth in range(4):
            if not current_uris:
                break

            derivation_tasks = [
                self.rag.triples_client.query(
                    s=uri, p=PROV_WAS_DERIVED_FROM, o=None, limit=5,
                    collection=self.collection,
                    g=GRAPH_SOURCE,
                )
                for uri in current_uris
            ]

            derivation_results = await asyncio.gather(
                *derivation_tasks, return_exceptions=True
            )

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
        SKIP_PREDICATES = {
            PROV_WAS_DERIVED_FROM,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
        }

        metadata_tasks = [
            self.rag.triples_client.query(
                s=uri, p=None, o=None, limit=50,
                collection=self.collection,
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
    Must be instantiated per-request so the label cache lives only for
    the duration of a single request. Workspace isolation is enforced
    by the trusted flow layer (flow.workspace), not by this class.
    """

    def __init__(
            self, prompt_client, embeddings_client, graph_embeddings_client,
            triples_client, reranker_client, verbose=False,
    ):

        self.verbose = verbose

        self.prompt_client = prompt_client
        self.embeddings_client = embeddings_client
        self.graph_embeddings_client = graph_embeddings_client
        self.triples_client = triples_client
        self.reranker_client = reranker_client

        self.label_cache = LRUCacheWithTTL(max_size=5000, ttl=300)

        if self.verbose:
            logger.debug("GraphRag initialized")

    async def query(
            self, query, collection = "default",
            entity_limit = 50, triple_limit = 30, max_subgraph_size = 1000,
            max_path_length = 2, edge_limit = 25, max_reranker_input = 350,
            streaming = False,
            chunk_callback = None,
            explain_callback = None, save_answer_callback = None,
            parent_uri = "",
    ):
        # Accumulate token usage across all prompt calls
        total_in = 0
        total_out = 0
        last_model = None

        def track_usage(result):
            nonlocal total_in, total_out, last_model
            if result is not None:
                if result.in_token is not None:
                    total_in += result.in_token
                if result.out_token is not None:
                    total_out += result.out_token
                if result.model is not None:
                    last_model = result.model

        if self.verbose:
            logger.debug("Constructing prompt...")

        # Generate explainability URIs upfront
        session_id = str(uuid.uuid4())
        q_uri = question_uri(session_id)
        gnd_uri = make_grounding_uri(session_id)
        exp_uri = make_exploration_uri(session_id)
        foc_uri = make_focus_uri(session_id)
        syn_uri = make_synthesis_uri(session_id)

        timestamp = datetime.now(timezone.utc).isoformat().replace(
            "+00:00", "Z",
        )

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
            rag = self, collection = collection,
            verbose = self.verbose, entity_limit = entity_limit,
            triple_limit = triple_limit,
            max_subgraph_size = max_subgraph_size,
            max_path_length = max_path_length,
            edge_limit = edge_limit,
            max_reranker_input = max_reranker_input,
            track_usage = track_usage,
        )

        # Step 1: Extract concepts and find seed entities
        seed_entities, concepts = await q.get_entities(query)

        # Emit grounding explain after concept extraction
        if explain_callback:
            cu = getattr(q, 'concepts_usage', None)
            gnd_triples = set_graph(
                grounding_triples(
                    gnd_uri, q_uri, concepts,
                    in_token=cu.in_token if cu else None,
                    out_token=cu.out_token if cu else None,
                    model=cu.model if cu else None,
                ),
                GRAPH_RETRIEVAL
            )
            await explain_callback(gnd_triples, gnd_uri)

        # Step 2: Iterative hop-and-filter with cross-encoder
        selected_edges, uri_map, edge_metadata = await q.hop_and_filter(
            seed_entities, concepts,
        )

        # Emit exploration explain
        if explain_callback:
            exp_triples = set_graph(
                exploration_triples(
                    exp_uri, gnd_uri, len(selected_edges),
                    entities=seed_entities,
                ),
                GRAPH_RETRIEVAL
            )
            await explain_callback(exp_triples, exp_uri)

        if self.verbose:
            logger.debug(f"Selected {len(selected_edges)} edges")
            for s, p, o in selected_edges:
                eid = edge_id(s, p, o)
                meta = edge_metadata.get(eid, {})
                logger.debug(
                    f"  {meta.get('score', 0):.4f} "
                    f"[{meta.get('concept', '')}] "
                    f"{s} | {p} | {o}"
                )

        # Step 3: Document tracing
        selected_edge_uris = [
            uri_map[edge_id(s, p, o)]
            for s, p, o in selected_edges
            if edge_id(s, p, o) in uri_map
        ]

        source_documents = await q.trace_source_documents(
            selected_edge_uris,
        )

        if isinstance(source_documents, Exception):
            logger.warning(
                f"Document tracing failed: {source_documents}"
            )
            source_documents = []

        # Build focus explainability data with cross-encoder metadata
        selected_edges_with_reasoning = []
        for s, p, o in selected_edges:
            eid = edge_id(s, p, o)
            if eid in uri_map:
                uri_s, uri_p, uri_o = uri_map[eid]
                meta = edge_metadata.get(eid, {})
                selected_edges_with_reasoning.append({
                    "edge": (uri_s, uri_p, uri_o),
                    "concept": meta.get("concept", ""),
                    "score": meta.get("score", 0),
                })

        # Emit focus explain
        if explain_callback:
            foc_triples = set_graph(
                focus_triples(
                    foc_uri, exp_uri,
                    selected_edges_with_reasoning, session_id,
                ),
                GRAPH_RETRIEVAL
            )
            await explain_callback(foc_triples, foc_uri)

        # Step 4: Synthesis
        selected_edge_dicts = [
            {"s": s, "p": p, "o": o}
            for s, p, o in selected_edges
        ]

        for s, p, o in source_documents:
            selected_edge_dicts.append({
                "s": s, "p": p, "o": o,
            })

        synthesis_variables = {
            "query": query,
            "knowledge": selected_edge_dicts,
        }

        if streaming and chunk_callback:
            accumulated_chunks = []

            async def accumulating_callback(chunk, end_of_stream):
                accumulated_chunks.append(chunk)
                await chunk_callback(chunk, end_of_stream)

            synthesis_result = await self.prompt_client.prompt(
                "kg-synthesis",
                variables=synthesis_variables,
                streaming=True,
                chunk_callback=accumulating_callback
            )
            track_usage(synthesis_result)
            resp = "".join(accumulated_chunks)
        else:
            synthesis_result = await self.prompt_client.prompt(
                "kg-synthesis",
                variables=synthesis_variables,
            )
            track_usage(synthesis_result)
            resp = synthesis_result.text

        if self.verbose:
            logger.debug("Query processing complete")

        # Emit synthesis explain
        if explain_callback:
            synthesis_doc_id = None
            answer_text = resp if resp else ""

            if save_answer_callback and answer_text:
                synthesis_doc_id = f"urn:trustgraph:synthesis:{session_id}"
                try:
                    await save_answer_callback(synthesis_doc_id, answer_text)
                    if self.verbose:
                        logger.debug(
                            f"Saved answer to librarian: "
                            f"{synthesis_doc_id}"
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to save answer to librarian: {e}"
                    )
                    synthesis_doc_id = None

            syn_triples = set_graph(
                synthesis_triples(
                    syn_uri, foc_uri,
                    document_id=synthesis_doc_id,
                    in_token=(
                        synthesis_result.in_token
                        if synthesis_result else None
                    ),
                    out_token=(
                        synthesis_result.out_token
                        if synthesis_result else None
                    ),
                    model=(
                        synthesis_result.model
                        if synthesis_result else None
                    ),
                ),
                GRAPH_RETRIEVAL
            )
            await explain_callback(syn_triples, syn_uri)

        if self.verbose:
            logger.debug(f"Emitted explain for session {session_id}")

        usage = {
            "in_token": total_in if total_in > 0 else None,
            "out_token": total_out if total_out > 0 else None,
            "model": last_model,
        }

        return resp, usage
