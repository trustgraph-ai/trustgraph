
from pymilvus import MilvusClient, CollectionSchema, FieldSchema, DataType
import time
import logging
import re

logger = logging.getLogger(__name__)

def make_safe_collection_name(user, collection, dimension, prefix):
    """
    Create a safe Milvus collection name from user/collection parameters.
    Milvus only allows letters, numbers, and underscores.
    """
    def sanitize(s):
        # Replace non-alphanumeric characters (except underscore) with underscore
        # Then collapse multiple underscores into single underscore
        safe = re.sub(r'[^a-zA-Z0-9_]', '_', s)
        safe = re.sub(r'_+', '_', safe)
        # Remove leading/trailing underscores
        safe = safe.strip('_')
        # Ensure it's not empty
        if not safe:
            safe = 'default'
        return safe
    
    safe_user = sanitize(user)
    safe_collection = sanitize(collection)
    
    return f"{prefix}_{safe_user}_{safe_collection}_{dimension}"

class EntityVectors:

    def __init__(self, uri="http://localhost:19530", prefix='entity'):

        self.client = MilvusClient(uri=uri)

        # Strategy is to create collections per dimension.  Probably only
        # going to be using 1 anyway, but that means we don't need to
        # hard-code the dimension anywhere, and no big deal if more than
        # one are created.
        self.collections = {}

        self.prefix = prefix

        # Time between reloads
        self.reload_time = 90

        # Next time to reload - this forces a reload at next window
        self.next_reload = time.time() + self.reload_time
        logger.debug(f"Reload at {self.next_reload}")

    def init_collection(self, dimension, user, collection):

        collection_name = make_safe_collection_name(user, collection, dimension, self.prefix)

        pkey_field = FieldSchema(
            name="id",
            dtype=DataType.INT64,
            is_primary=True,
            auto_id=True,
        )

        vec_field = FieldSchema(
            name="vector",
            dtype=DataType.FLOAT_VECTOR,
            dim=dimension,
        )

        entity_field = FieldSchema(
            name="entity",
            dtype=DataType.VARCHAR,
            max_length=65535,
        )

        schema = CollectionSchema(
            fields = [pkey_field, vec_field, entity_field],
            description = "Graph embedding schema",
        )

        self.client.create_collection(
            collection_name=collection_name,
            schema=schema,
            metric_type="COSINE",
        )

        index_params = MilvusClient.prepare_index_params()

        index_params.add_index(
            field_name="vector",
            metric_type="COSINE",
            index_type="IVF_SQ8",
            index_name="vector_index",
            params={ "nlist": 128 }
        )

        self.client.create_index(
            collection_name=collection_name,
            index_params=index_params
        )

        self.collections[(dimension, user, collection)] = collection_name

    def insert(self, embeds, entity, user, collection):

        dim = len(embeds)

        if (dim, user, collection) not in self.collections:
            self.init_collection(dim, user, collection)
    
        data = [
            {
                "vector": embeds,
                "entity": entity,
            }
        ]

        self.client.insert(
            collection_name=self.collections[(dim, user, collection)],
            data=data
        )

    def search(self, embeds, user, collection, fields=["entity"], limit=10):

        dim = len(embeds)

        if (dim, user, collection) not in self.collections:
            self.init_collection(dim, user, collection)

        coll = self.collections[(dim, user, collection)]

        search_params = {
            "metric_type": "COSINE",
            "params": {
                "radius": 0.1,
                "range_filter": 0.8
            }
        }

        logger.debug("Loading...")
        self.client.load_collection(
            collection_name=coll,
        )

        logger.debug("Searching...")

        res = self.client.search(
            collection_name=coll,
            data=[embeds],
            limit=limit,
            output_fields=fields,
            search_params=search_params,
        )[0]


        # If reload time has passed, unload collection
        if time.time() > self.next_reload:
            logger.debug(f"Unloading, reload at {self.next_reload}")
            self.client.release_collection(
                collection_name=coll,
            )
            self.next_reload = time.time() + self.reload_time

        return res

