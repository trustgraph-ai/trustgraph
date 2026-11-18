
import asyncio
import logging
import uuid
from datetime import datetime, timezone

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
    DC_TITLE, RDFS_LABEL,
)

# Module logger
logger = logging.getLogger(__name__)

SKIP_PREDICATES = {
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
    TG_CONTAINS,
    PROV_WAS_DERIVED_FROM,
}


class GraphRag:
    """
    Graph RAG pipeline composed from concept extraction and knowledge
    retrieval services.  Performs:

    1. Concept extraction (via service)
    2. Knowledge retrieval (via service)
    3. Document tracing (local, uses triples client)
    4. Synthesis (via prompt service)
    5. Explainability (emitted throughout)

    Must be instantiated per-request.  Workspace isolation is enforced
    by the trusted flow layer (flow.workspace), not by this class.
    """

    def __init__(
            self, concept_extraction_client, knowledge_retrieval_client,
            triples_client, prompt_client,
            verbose=False,
    ):
        self.verbose = verbose
        self.concept_extraction_client = concept_extraction_client
        self.knowledge_retrieval_client = knowledge_retrieval_client
        self.triples_client = triples_client
        self.prompt_client = prompt_client

        if self.verbose:
            logger.debug("GraphRag initialized")

    async def query(
            self, query, collection="default",
            entity_limit=50, triple_limit=30,
            max_path_length=2, edge_limit=25, max_reranker_input=350,
            streaming=False,
            chunk_callback=None,
            explain_callback=None, save_answer_callback=None,
            parent_uri="",
            user_context=None,
            grounding_seeds=None,
            graph_seeds=None,
            languages=None,
            graph=None,
    ):
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

        session_id = str(uuid.uuid4())
        q_uri = question_uri(session_id)
        gnd_uri = make_grounding_uri(session_id)
        exp_uri = make_exploration_uri(session_id)
        foc_uri = make_focus_uri(session_id)
        syn_uri = make_synthesis_uri(session_id)

        timestamp = datetime.now(timezone.utc).isoformat().replace(
            "+00:00", "Z",
        )

        if explain_callback:
            q_triples = set_graph(
                question_triples(
                    q_uri, query, timestamp,
                    parent_uri=parent_uri or None,
                ),
                GRAPH_RETRIEVAL
            )
            await explain_callback(q_triples, q_uri)

        # Step 1: Concept extraction
        if graph_seeds:
            logger.info(
                f"Using {len(graph_seeds)} graph seeds, "
                "skipping concept extraction"
            )
            concepts = []
            entities = list(graph_seeds)
        elif grounding_seeds:
            logger.info(
                f"Using {len(grounding_seeds)} grounding seeds"
            )
            concepts = list(grounding_seeds)
            entities = []
        else:
            concepts = await self.concept_extraction_client.extract(
                query, timeout=300,
            )
            entities = []
            logger.info(f"Extracted concepts: {concepts}")

        if explain_callback:
            gnd_triples = set_graph(
                grounding_triples(
                    gnd_uri, q_uri, concepts or [query],
                ),
                GRAPH_RETRIEVAL
            )
            await explain_callback(gnd_triples, gnd_uri)

        # Step 2: Knowledge retrieval
        kr_resp = await self.knowledge_retrieval_client.retrieve(
            concepts=concepts or None,
            entities=entities or None,
            entity_limit=entity_limit,
            triple_limit=triple_limit,
            max_path_length=max_path_length,
            edge_limit=edge_limit,
            max_reranker_input=max_reranker_input,
            languages=languages or [],
            graph=graph or "",
            timeout=300,
        )

        seed_entities = kr_resp.seed_entities
        edges = kr_resp.edges

        if explain_callback:
            exp_triples = set_graph(
                exploration_triples(
                    exp_uri, gnd_uri, len(edges),
                    entities=seed_entities,
                ),
                GRAPH_RETRIEVAL
            )
            await explain_callback(exp_triples, exp_uri)

        logger.info(f"Knowledge retrieval: {len(edges)} edges")

        # Build edge data for synthesis and explainability
        selected_edges = [
            (e.s_label, e.p_label, e.o_label)
            for e in edges
        ]

        selected_edges_with_reasoning = [
            {
                "edge": (
                    Term(type=IRI, iri=e.s),
                    Term(type=IRI, iri=e.p),
                    Term(type=IRI, iri=e.o),
                ),
                "concept": e.concept,
                "score": e.score,
            }
            for e in edges
        ]

        edge_uris = [
            (e.s, e.p, e.o) for e in edges
        ]

        if explain_callback:
            foc_triples = set_graph(
                focus_triples(
                    foc_uri, exp_uri,
                    selected_edges_with_reasoning, session_id,
                ),
                GRAPH_RETRIEVAL
            )
            await explain_callback(foc_triples, foc_uri)

        # Step 3: Document tracing
        try:
            source_documents, sources = await self.trace_source_documents(
                edge_uris, collection, graph, user_context,
            )
        except Exception as e:
            logger.warning(f"Document tracing failed: {e}")
            source_documents, sources = [], []

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

        if explain_callback:
            synthesis_doc_id = None
            answer_text = resp if resp else ""

            if save_answer_callback and answer_text:
                synthesis_doc_id = (
                    f"urn:trustgraph:synthesis:{session_id}"
                )
                try:
                    await save_answer_callback(
                        synthesis_doc_id, answer_text,
                    )
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

        return resp, usage, sources

    async def trace_source_documents(
        self, edge_uris, collection, graph, user_context,
    ):
        """Trace selected edges back to source documents via provenance."""

        subgraph_tasks = []
        for s, p, o in edge_uris:
            s_term = Term(type=IRI, iri=s) if isinstance(s, str) else s
            p_term = Term(type=IRI, iri=p) if isinstance(p, str) else p
            o_term = Term(type=IRI, iri=o) if isinstance(o, str) else o
            quoted = Term(
                type=TRIPLE,
                triple=SchemaTriple(
                    s=s_term, p=p_term, o=o_term,
                )
            )
            subgraph_tasks.append(
                self.triples_client.query(
                    s=None, p=TG_CONTAINS, o=quoted, limit=1,
                    collection=collection,
                    g=GRAPH_SOURCE,
                    user_context=user_context,
                )
            )

        subgraph_results = await asyncio.gather(
            *subgraph_tasks, return_exceptions=True
        )

        subgraph_uris = set()
        for result in subgraph_results:
            if isinstance(result, Exception) or not result:
                continue
            for triple in result:
                subgraph_uris.add(str(triple.s))

        if not subgraph_uris:
            return [], []

        current_uris = subgraph_uris
        doc_uris = set()

        for depth in range(4):
            if not current_uris:
                break

            derivation_tasks = [
                self.triples_client.query(
                    s=uri, p=PROV_WAS_DERIVED_FROM, o=None, limit=5,
                    collection=collection,
                    g=GRAPH_SOURCE,
                    user_context=user_context,
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

            current_uris = next_uris

        doc_uris.update(current_uris)

        metadata_tasks = [
            self.triples_client.query(
                s=uri, p=None, o=None, limit=50,
                collection=collection,
                g=GRAPH_SOURCE,
                user_context=user_context,
            )
            for uri in doc_uris
        ]

        metadata_results = await asyncio.gather(
            *metadata_tasks, return_exceptions=True
        )

        doc_edges = []
        sources = []
        for uri, result in zip(doc_uris, metadata_results):
            title = ""
            if not isinstance(result, Exception) and result:
                for triple in result:
                    p = str(triple.p)
                    if p in SKIP_PREDICATES:
                        continue
                    doc_edges.append((
                        str(triple.s), p, str(triple.o)
                    ))
                    if p == DC_TITLE or (p == RDFS_LABEL and not title):
                        title = str(triple.o)
            sources.append({"uri": uri, "title": title})

        return doc_edges, sources
