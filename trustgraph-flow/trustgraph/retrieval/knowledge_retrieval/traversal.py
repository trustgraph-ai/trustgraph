"""
Graph traversal engine extracted from the GraphRAG pipeline.
Performs embedding lookup, entity retrieval, and hop-and-filter
traversal with cross-encoder reranking.
"""

import asyncio
import hashlib
import logging
import time
from collections import OrderedDict

from ... schema import IRI, LITERAL, Term
from ... knowledge import Uri, Literal

logger = logging.getLogger(__name__)

LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#"
OWL_NS = "http://www.w3.org/2002/07/owl#"
RDF_TYPE = RDF_NS + "type"
SCHEMA_NAMESPACES = (RDF_NS, RDFS_NS, OWL_NS)

FROM_S = "from_s"
FROM_P = "from_p"
FROM_O = "from_o"


def is_schema_predicate(predicate):
    if predicate == RDF_TYPE:
        return False
    return predicate.startswith(SCHEMA_NAMESPACES)


def term_to_string(term):
    if term is None:
        return None
    if term.type == IRI:
        return term.iri
    elif term.type == LITERAL:
        return term.value
    return term.iri or term.value or str(term)


def edge_id(s, p, o):
    edge_str = f"{s}|{p}|{o}"
    return hashlib.sha256(edge_str.encode()).hexdigest()[:8]


def _local_name(iri):
    pos = iri.rfind('#')
    if pos < 0:
        pos = iri.rfind('/')
    if pos >= 0 and pos < len(iri) - 1:
        return iri[pos + 1:]
    return iri


class LRUCacheWithTTL:

    def __init__(self, max_size=5000, ttl=300):
        self.cache = OrderedDict()
        self.access_times = {}
        self.max_size = max_size
        self.ttl = ttl

    def get(self, key):
        if key not in self.cache:
            return None
        if time.time() - self.access_times[key] > self.ttl:
            del self.cache[key]
            del self.access_times[key]
            return None
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.max_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                del self.access_times[oldest_key]
        self.cache[key] = value
        self.access_times[key] = time.time()


class TraversalEngine:
    """Performs embedding lookup, entity retrieval, and hop-and-filter
    graph traversal with cross-encoder reranking.

    Extracted from GraphRAG's Query class so it can be used
    independently as a knowledge retrieval service.
    """

    def __init__(
        self,
        embeddings_client,
        graph_embeddings_client,
        triples_client,
        reranker_client,
        collection,
        entity_limit=50,
        triple_limit=30,
        max_path_length=2,
        edge_limit=25,
        max_reranker_input=350,
        max_reranker_text_length=240,
        languages=None,
        graph=None,
    ):
        self.embeddings_client = embeddings_client
        self.graph_embeddings_client = graph_embeddings_client
        self.triples_client = triples_client
        self.reranker_client = reranker_client
        self.collection = collection
        self.entity_limit = entity_limit
        self.triple_limit = triple_limit
        self.max_path_length = max_path_length
        self.edge_limit = edge_limit
        self.max_reranker_input = max_reranker_input
        self.max_reranker_text_length = max_reranker_text_length
        self.languages = languages or []
        self.graph = graph or None

        self.label_cache = LRUCacheWithTTL()

    async def embed_concepts(self, concepts):
        return await self.embeddings_client.embed(concepts)

    async def find_seed_entities(self, concepts):
        """Embed concepts and find matching entities via vector search."""

        vectors = await self.embed_concepts(concepts)

        logger.info(f"Got {len(vectors)} embedding vectors")

        per_concept_limit = max(
            1, self.entity_limit // len(vectors)
        )

        entity_tasks = [
            self.graph_embeddings_client.query(
                vector=v, limit=per_concept_limit,
                collection=self.collection,
            )
            for v in vectors
        ]

        results = await asyncio.gather(*entity_tasks, return_exceptions=True)

        seen = set()
        entities = []
        embed_errors = 0
        for result in results:
            if isinstance(result, Exception):
                embed_errors += 1
                logger.warning(f"Embedding query error: {result}")
                continue
            if not result:
                continue
            for e in result:
                entity = term_to_string(e.entity)
                if entity not in seen:
                    seen.add(entity)
                    entities.append(entity)

        logger.info(
            f"Seed entities: {len(entities)} "
            f"(from {len(results)} embedding queries, "
            f"{embed_errors} errors)"
        )

        return entities

    async def maybe_label(self, e):

        cache_key = f"{self.collection}:{e}"

        cached_label = self.label_cache.get(cache_key)
        if cached_label is not None:
            return cached_label

        res = await self.triples_client.query(
            s=e, p=LABEL, o=None, limit=1,
            collection=self.collection,
            g=self.graph if self.graph is not None else "",
        )

        if len(res) == 0:
            fallback = _local_name(e)
            self.label_cache.put(cache_key, fallback)
            return fallback

        label = str(res[0].o)
        self.label_cache.put(cache_key, label)
        return label

    async def execute_batch_triple_queries(self, entities, limit_per_entity):

        if self.graph is not None:
            graph_list = [self.graph]
        else:
            graph_list = [None]

        tasks = []
        directions = []

        for g in graph_list:
            for entity in entities:
                tasks.append(
                    self.triples_client.query_stream(
                        s=entity, p=None, o=None,
                        limit=limit_per_entity,
                        collection=self.collection,
                        batch_size=20, g=g,
                    ),
                )
                directions.append(FROM_S)

                tasks.append(
                    self.triples_client.query_stream(
                        s=None, p=entity, o=None,
                        limit=limit_per_entity,
                        collection=self.collection,
                        batch_size=20, g=g,
                    ),
                )
                directions.append(FROM_P)

                tasks.append(
                    self.triples_client.query_stream(
                        s=None, p=None, o=entity,
                        limit=limit_per_entity,
                        collection=self.collection,
                        batch_size=20, g=g,
                    ),
                )
                directions.append(FROM_O)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_triples = []
        errors = []
        empty_count = 0
        for direction, result in zip(directions, results):
            if isinstance(result, Exception):
                errors.append(result)
            elif result is not None and len(result) > 0:
                all_triples.extend(
                    (triple, direction) for triple in result
                )
            else:
                empty_count += 1

        if errors:
            logger.error(
                f"Triples query errors: {len(errors)} of "
                f"{len(results)} queries failed: {errors[0]}"
            )

        logger.info(
            f"Batch queries: {len(results)} total, "
            f"{len(all_triples)} triples"
        )

        return all_triples

    async def resolve_labels_batch(self, entities):
        tasks = [self.maybe_label(entity) for entity in entities]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def _matches_language(self, triple):
        if not self.languages:
            return True

        lang_set = set(self.languages)
        has_literal = False

        for val in (triple.s, triple.o):
            if hasattr(val, 'language'):
                has_literal = True
                lang = val.language if val.language is not None else ""
                if lang in lang_set:
                    return True
            elif hasattr(val, 'value'):
                has_literal = True
                if "" in lang_set:
                    return True

        return not has_literal

    async def hop_and_filter(self, seed_entities, concepts):
        """Iterative hop-and-filter graph traversal with cross-encoder.

        Returns list of dicts with keys:
            s, p, o, s_label, p_label, o_label, score, concept
        """
        all_edges = []
        frontier = set(seed_entities)
        visited_entities = set()
        seen_edges = set()

        logger.info(
            f"hop_and_filter: {len(seed_entities)} seed entities, "
            f"{len(concepts)} concepts, "
            f"max_path_length={self.max_path_length}"
        )

        for hop in range(self.max_path_length):
            if not frontier:
                break

            unvisited = [e for e in frontier if e not in visited_entities]
            if not unvisited:
                logger.info(
                    f"Hop {hop + 1}: no unvisited frontier, stopping"
                )
                break

            logger.info(
                f"Hop {hop + 1}: {len(unvisited)} unvisited frontier "
                f"entities"
            )

            triples = await self.execute_batch_triple_queries(
                unvisited, self.triple_limit,
            )

            logger.info(
                f"Hop {hop + 1}: {len(triples)} raw triples"
            )

            hop_triples = []
            hop_directions = {}
            skip_lang = 0
            skip_schema = 0
            skip_seen = 0
            for triple, direction in triples:
                if not self._matches_language(triple):
                    skip_lang += 1
                    continue

                triple_tuple = (
                    str(triple.s), str(triple.p), str(triple.o),
                )
                if is_schema_predicate(triple_tuple[1]):
                    skip_schema += 1
                    continue
                if triple_tuple in seen_edges:
                    skip_seen += 1
                    continue

                seen_edges.add(triple_tuple)
                hop_triples.append(triple_tuple)
                hop_directions[triple_tuple] = direction

            logger.info(
                f"Hop {hop + 1}: {len(hop_triples)} edges after filtering "
                f"(skipped: lang={skip_lang} schema={skip_schema} "
                f"seen={skip_seen})"
            )

            if not hop_triples:
                visited_entities.update(frontier)
                break

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

            filtered_triples = []
            labeled_hop = []
            documents = []
            for s, p, o in hop_triples:
                ls = label_map.get(s, s)
                lp = label_map.get(p, p)
                lo = label_map.get(o, o)

                direction = hop_directions[(s, p, o)]
                if direction == FROM_S:
                    text = f"{lp} {lo}"
                elif direction == FROM_O:
                    text = f"{ls} {lp}"
                else:
                    text = f"{ls} {lo}"

                if len(text) > self.max_reranker_text_length:
                    text = text[:self.max_reranker_text_length]

                idx = len(filtered_triples)
                filtered_triples.append((s, p, o))
                labeled_hop.append((ls, lp, lo))
                documents.append({"id": str(idx), "text": text})

            hop_triples = filtered_triples

            if len(hop_triples) > self.max_reranker_input:
                logger.info(
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

            results = await self.reranker_client.rerank(
                queries=queries,
                documents=documents,
                limit=self.edge_limit,
            )

            logger.info(
                f"Hop {hop + 1}: reranker returned {len(results)} edges"
            )

            next_frontier = set()
            for r in results:
                idx = int(r.document_id)
                ls, lp, lo = labeled_hop[idx]
                s, p, o = hop_triples[idx]

                all_edges.append({
                    "s": s, "p": p, "o": o,
                    "s_label": ls, "p_label": lp, "o_label": lo,
                    "score": r.score,
                    "concept": concepts[int(r.query_id)],
                })

                next_frontier.add(s)
                next_frontier.add(o)

            visited_entities.update(frontier)
            frontier = next_frontier - visited_entities

            logger.info(
                f"Hop {hop + 1}: next frontier {len(frontier)} entities"
            )

        logger.info(
            f"hop_and_filter complete: {len(all_edges)} total edges"
        )

        return all_edges
