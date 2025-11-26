
import asyncio
import logging
import time
from collections import OrderedDict

# Module logger
logger = logging.getLogger(__name__)

LABEL="http://www.w3.org/2000/01/rdf-schema#label"

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

        qembeds = await  self.rag.embeddings_client.embed(query)

        if self.verbose:
            logger.debug("Done.")

        return qembeds

    async def get_entities(self, query):

        vectors = await self.get_vector(query)

        if self.verbose:
            logger.debug("Getting entities...")

        entities = await self.rag.graph_embeddings_client.query(
            vectors=vectors, limit=self.entity_limit,
            user=self.user, collection=self.collection,
        )

        entities = [
            str(e)
            for e in entities
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
        """Execute triple queries for multiple entities concurrently"""
        tasks = []

        for entity in entities:
            # Create concurrent tasks for all 3 query types per entity
            tasks.extend([
                self.rag.triples_client.query(
                    s=entity, p=None, o=None,
                    limit=limit_per_entity,
                    user=self.user, collection=self.collection
                ),
                self.rag.triples_client.query(
                    s=None, p=entity, o=None,
                    limit=limit_per_entity,
                    user=self.user, collection=self.collection
                ),
                self.rag.triples_client.query(
                    s=None, p=None, o=entity,
                    limit=limit_per_entity,
                    user=self.user, collection=self.collection
                )
            ])

        # Execute all queries concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine all results
        all_triples = []
        for result in results:
            if not isinstance(result, Exception):
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

        # Apply labels to subgraph
        sg2 = []
        for s, p, o in filtered_subgraph:
            labeled_triple = (
                label_map.get(s, s),
                label_map.get(p, p),
                label_map.get(o, o)
            )
            sg2.append(labeled_triple)

        sg2 = sg2[0:self.max_subgraph_size]

        if self.verbose:
            logger.debug("Subgraph:")
            for edge in sg2:
                logger.debug(f"  {str(edge)}")

        if self.verbose:
            logger.debug("Done.")

        return sg2
    
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
    ):

        if self.verbose:
            logger.debug("Constructing prompt...")

        q = Query(
            rag = self, user = user, collection = collection,
            verbose = self.verbose, entity_limit = entity_limit,
            triple_limit = triple_limit,
            max_subgraph_size = max_subgraph_size,
            max_path_length = max_path_length,
        )

        kg = await q.get_labelgraph(query)

        if self.verbose:
            logger.debug("Invoking LLM...")
            logger.debug(f"Knowledge graph: {kg}")
            logger.debug(f"Query: {query}")

        if streaming and chunk_callback:
            resp = await self.prompt_client.kg_prompt(
                query, kg,
                streaming=True,
                chunk_callback=chunk_callback
            )
        else:
            resp = await self.prompt_client.kg_prompt(query, kg)

        if self.verbose:
            logger.debug("Query processing complete")

        return resp

