
from pymilvus import MilvusClient, CollectionSchema, FieldSchema, DataType
import time
import logging

logger = logging.getLogger(__name__)

class ObjectVectors:

    def __init__(self, uri="http://localhost:19530", prefix='obj'):

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

    def init_collection(self, dimension, name):

        collection_name = self.prefix + "_" + name + "_" + str(dimension)

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

        name_field = FieldSchema(
            name="name",
            dtype=DataType.VARCHAR,
            max_length=65535,
        )

        key_name_field = FieldSchema(
            name="key_name",
            dtype=DataType.VARCHAR,
            max_length=65535,
        )

        key_field = FieldSchema(
            name="key",
            dtype=DataType.VARCHAR,
            max_length=65535,
        )

        schema = CollectionSchema(
            fields = [
                pkey_field, vec_field, name_field, key_name_field, key_field
            ],
            description = "Object embedding schema",
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

        self.collections[(dimension, name)] = collection_name

    def insert(self, embeds, name, key_name, key):

        dim = len(embeds)

        if (dim, name) not in self.collections:
            self.init_collection(dim, name)
    
        data = [
            {
                "vector": embeds,
                "name": name,
                "key_name": key_name,
                "key": key,
            }
        ]

        self.client.insert(
            collection_name=self.collections[(dim, name)],
            data=data
        )

    def search(self, embeds, name, fields=["key_name", "name"], limit=10):

        dim = len(embeds)

        if dim not in self.collections:
            self.init_collection(dim, name)

        coll = self.collections[(dim, name)]

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

