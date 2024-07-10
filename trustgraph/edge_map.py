
from pymilvus import MilvusClient, CollectionSchema, FieldSchema, DataType

class VectorStore:

    def __init__(self, uri="http://localhost:19530"):

        self.client = MilvusClient(uri=uri)

        self.collection = "edges"
        self.dimension = 384

        if not self.client.has_collection(collection_name=self.collection):
            self.init_collection()

    def init_collection(self):

        pkey_field = FieldSchema(
            name="id",
            dtype=DataType.INT64,
            is_primary=True,
            auto_id=True,
        )

        vec_field = FieldSchema(
            name="vector",
            dtype=DataType.FLOAT_VECTOR,
            dim=self.dimension,
        )

        entity_field = FieldSchema(
            name="entity",
            dtype=DataType.VARCHAR,
            max_length=65535,
        )

        schema = CollectionSchema(
            fields = [pkey_field, vec_field, entity_field],
            description = "Edge map schema",
        )

        self.client.create_collection(
            collection_name=self.collection,
            schema=schema,
            metric_type="IP",
        )

        index_params = MilvusClient.prepare_index_params()

        index_params.add_index(
            field_name="vector",
            metric_type="COSINE",
            index_type="FLAT",  # IVF_FLAT?!
            index_name="vector_index",
            params={ "nlist": 128 }
        )

        self.client.create_index(
            collection_name=self.collection,
            index_params=index_params
        )

    def insert(self, embeds, entity):
    
        data = [
            {
                "vector": embeds,
                "entity": entity,
            }
        ]

        self.client.insert(collection_name=self.collection, data=data)

    def search(self, embeds, fields=["entity"], limit=10):

        search_params = {
            "metric_type": "COSINE",
            "params": {
                "radius": 0.1,
                "range_filter": 0.8
            }
        }

        self.client.load_collection(
            collection_name=self.collection,
#             replica_number=1
        )

        res = self.client.search(
            collection_name=self.collection,
            data=[embeds],
            limit=limit,
            output_fields=fields,
            search_params=search_params,
        )[0]

        self.client.release_collection(
            collection_name=self.collection,
        )

        return res

