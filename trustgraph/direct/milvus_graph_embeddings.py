
from pymilvus import MilvusClient, CollectionSchema, FieldSchema, DataType
import time

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
        print("Reload at", self.next_reload)

    def init_collection(self, dimension):

        collection_name = self.prefix + "_" + str(dimension)

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

        self.collections[dimension] = collection_name

    def insert(self, embeds, entity):

        dim = len(embeds)

        if dim not in self.collections:
            self.init_collection(dim)
    
        data = [
            {
                "vector": embeds,
                "entity": entity,
            }
        ]

        self.client.insert(
            collection_name=self.collections[dim],
            data=data
        )

    def search(self, embeds, fields=["entity"], limit=10):

        dim = len(embeds)

        if dim not in self.collections:
            self.init_collection(dim)

        coll = self.collections[dim]

        search_params = {
            "metric_type": "COSINE",
            "params": {
                "radius": 0.1,
                "range_filter": 0.8
            }
        }

        print("Loading...")
        self.client.load_collection(
            collection_name=coll,
        )

        print("Searching...")

        res = self.client.search(
            collection_name=coll,
            data=[embeds],
            limit=limit,
            output_fields=fields,
            search_params=search_params,
        )[0]


        # If reload time has passed, unload collection
        if time.time() > self.next_reload:
            print("Unloading, reload at", self.next_reload)
            self.client.release_collection(
                collection_name=coll,
            )
            self.next_reload = time.time() + self.reload_time

        return res

