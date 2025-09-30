
from pymilvus import MilvusClient, CollectionSchema, FieldSchema, DataType
import time
import logging
import re

logger = logging.getLogger(__name__)

def make_safe_collection_name(user, collection, prefix):
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
    
    return f"{prefix}_{safe_user}_{safe_collection}"

class DocVectors:

    def __init__(self, uri="http://localhost:19530", prefix='doc'):

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

    def collection_exists(self, user, collection):
        """Check if collection exists (dimension-independent check)"""
        collection_name = make_safe_collection_name(user, collection, self.prefix)
        return self.client.has_collection(collection_name)

    def create_collection(self, user, collection, dimension=384):
        """Create collection with default dimension"""
        collection_name = make_safe_collection_name(user, collection, self.prefix)

        if self.client.has_collection(collection_name):
            logger.info(f"Collection {collection_name} already exists")
            return

        self.init_collection(dimension, user, collection)
        logger.info(f"Created Milvus collection {collection_name} with dimension {dimension}")

    def init_collection(self, dimension, user, collection):

        collection_name = make_safe_collection_name(user, collection, self.prefix)

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

        doc_field = FieldSchema(
            name="doc",
            dtype=DataType.VARCHAR,
            max_length=65535,
        )

        schema = CollectionSchema(
            fields = [pkey_field, vec_field, doc_field],
            description = "Document embedding schema",
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

    def insert(self, embeds, doc, user, collection):

        dim = len(embeds)

        print("INSERT VEC", dim, flush=True)

        if (dim, user, collection) not in self.collections:
            self.init_collection(dim, user, collection)
    
        data = [
            {
                "vector": embeds,
                "doc": doc,
            }
        ]

        self.client.insert(
            collection_name=self.collections[(dim, user, collection)],
            data=data
        )

    def search(self, embeds, user, collection, fields=["doc"], limit=10):

        dim = len(embeds)

        if (dim, user, collection) not in self.collections:
            self.init_collection(dim, user, collection)

        coll = self.collections[(dim, user, collection)]

        logger.debug("Loading...")
        self.client.load_collection(
            collection_name=coll,
        )

        logger.debug("Searching...")

        res = self.client.search(
            collection_name=coll,
            anns_field="vector",
            data=[embeds],
            limit=limit,
            output_fields=fields,
            search_params={ "metric_type": "COSINE" },
        )[0]


        # If reload time has passed, unload collection
        if time.time() > self.next_reload:
            logger.debug(f"Unloading, reload at {self.next_reload}")
            self.client.release_collection(
                collection_name=coll,
            )
            self.next_reload = time.time() + self.reload_time

        return res

    def delete_collection(self, user, collection):
        """Delete a collection for the given user and collection"""
        collection_name = make_safe_collection_name(user, collection, self.prefix)

        # Check if collection exists
        if self.client.has_collection(collection_name):
            # Drop the collection
            self.client.drop_collection(collection_name)
            logger.info(f"Deleted Milvus collection: {collection_name}")

            # Remove from our local cache
            keys_to_remove = [key for key in self.collections.keys() if key[1] == user and key[2] == collection]
            for key in keys_to_remove:
                del self.collections[key]
        else:
            logger.info(f"Collection {collection_name} does not exist, nothing to delete")

