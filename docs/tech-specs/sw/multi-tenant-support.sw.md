---
layout: default
title: "Maelezo ya Kiufundi: Usaidizi wa Matumizi Mbalimbali (Multi-Tenant)"
parent: "Swahili (Beta)"
---

# Maelezo ya Kiufundi: Usaidizi wa Matumizi Mbalimbali (Multi-Tenant)

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Muhtasari

Wezesha matumizi mbalimbali kwa kurekebisha kutofautiana kwa majina ya vigezo ambavyo huuzuia utengenezaji wa folyo (queue) na kwa kuongeza utaratibu wa kuweka vigezo kwa Cassandra.

## Mfumo wa Uendeshaji

### Utatuzi wa Folyo Kulingana na Mchakato

Mfumo wa TrustGraph hutumia **mfumo wa usanifu unaozingatia mchakato** (flow-based architecture) kwa utatuzi wa folyo, ambao kwa asili unao na uwezo wa kuunga mkono matumizi mbalimbali:

**Maelezo ya Mchakato** (Flow Definitions) huhifadhiwa katika Cassandra na yanaeleza majina ya folyo kupitia maelezo ya kiungo (interface).
**Majina ya folyo hutumia vipengele** (templates) na vigezo vya `{id}` ambavyo hubadilishwa na kitambulisho cha mfano wa mchakato.
**Huduma zinatatua folyo kwa njia ya moja kwa moja** kwa kutafuta mipangilio ya mchakato wakati wa ombi.
**Kila mtumiaji anaweza kuwa na mchakato wake wa kipekee** na majina tofauti ya folyo, ambayo hutoa upekee.

Kielelezo cha maelezo ya kiungo ya mchakato:
```json
{
  "interfaces": {
    "triples-store": "persistent://tg/flow/triples-store:{id}",
    "graph-embeddings-store": "persistent://tg/flow/graph-embeddings-store:{id}"
  }
}
```

Wakati mwendeshaji A anaanza mtiririko `tenant-a-prod` na mwendeshaji B anaanza mtiririko `tenant-b-prod`, wanapata moja kwa moja folyo zisizo na muunganisho:
`persistent://tg/flow/triples-store:tenant-a-prod`
`persistent://tg/flow/triples-store:tenant-b-prod`

**Huduma zilizoundwa vizuri kwa utumiaji wa wateja wengi:**
✅ **Usimamizi wa Maarifa (msingi)** - Inatatua moja kwa moja folyo kutoka usanidi wa mtiririko uliopitishwa katika ombi.

**Huduma zinazohitaji marekebisho:**
🔴 **Huduma ya Usanidi** - Utangamano wa jina la parameter unazuia utengenezaji wa folyo
🔴 **Huduma ya Maktaba** - Mada ya uhifadhi iliyopangwa (iliyozungumzwa hapa chini)
🔴 **Huduma Zote** - Haiwezi kubadilisha nafasi ya Cassandra

## Taarifa ya Tatizo

### Tatizo #1: Utangamano wa Jina la Parameter katika AsyncProcessor
**CLI inafafanua:** `--config-queue` (jina lisilo wazi)
**Argparse inabadilisha kuwa:** `config_queue` (katika kamusi ya params)
**Msimu unatafuta:** `config_push_queue`
**Matokeo:** Parameter inakwama, inarudisha `persistent://tg/config/config`
**Athari:** Huathiri huduma zote 32+ zinazorithi kutoka kwa AsyncProcessor
**Inazuia:** Uwekaji wa wateja wengi hauna uwezo wa kutumia folyo maalum za mteja
**Suluhisho:** Badilisha parameter ya CLI kuwa `--config-push-queue` kwa uwazi (mabadiliko ya kuvunja yanakubalika kwani kipengele hicho kwa sasa kimevunjika)

### Tatizo #2: Utangamano wa Jina la Parameter katika Huduma ya Usanidi
**CLI inafafanua:** `--push-queue` (jina lisilo wazi)
**Argparse inabadilisha kuwa:** `push_queue` (katika kamusi ya params)
**Msimu unatafuta:** `config_push_queue`
**Matokeo:** Parameter inakwama
**Athari:** Huduma ya usanidi haiwezi kutumia folyo ya kushinikiza maalum
**Suluhisho:** Badilisha parameter ya CLI kuwa `--config-push-queue` kwa utangamano na uwazi (mabadiliko ya kuvunja yanakubalika)

### Tatizo #3: Nafasi ya Cassandra Iliyopangwa
**Sasa:** Nafasi ya Cassandra imepangwa kama `"config"`, `"knowledge"`, `"librarian"` katika huduma mbalimbali
**Matokeo:** Haiwezi kubadilisha nafasi ya utumiaji wa wateja wengi
**Athari:** Huduma za usanidi, msingi, na maktaba
**Inazuia:** Wateja wengi hawawezi kutumia nafasi tofauti za Cassandra

### Tatizo #4: Usanidi wa Usimamizi wa Mkusanyiko ✅ IMEKAMILIKA
**Hapo awali:** Mkusanyiko ulihifadhiwa katika nafasi ya maktaba ya Cassandra kupitia meza tofauti ya mkusanyiko
**Hapo awali:** Maktaba ilitumia mada 4 zilizopangwa za usimamizi wa uhifadhi ili kuratibu uundaji/ufutaji wa mkusanyiko:
  `vector_storage_management_topic`
  `object_storage_management_topic`
  `triples_storage_management_topic`
  `storage_management_response_topic`
**Matatizo (Yaliyoshughulikiwa):**
  Mada iliyopangwa haikuweza kubadilishwa kwa utumiaji wa wateja wengi
  Uratibu wa async tata kati ya maktaba na huduma 4+ za uhifadhi
  Meza tofauti ya Cassandra na miundombinu ya usimamizi
  Folyo za ombi/jibu zisizo na uhai kwa operesheni muhimu
**Suluhisho Liliofanywa:** Kuhamishia mkusanyiko kwenye uhifadhi wa huduma ya usanidi, tumia kushinikiza usanidi kwa usambazaji
**Hali:** Uhifadhi wote wa nyuma umehamishwa kwenye mtindo wa `CollectionConfigHandler`

## Suluhisho

Hii inahusu Matatizo #1, #2, #3, na #4.

### Sehemu ya 1: Marekebisho ya Utangamano wa Jina la Parameter

#### Mabadiliko ya 1: Darasa la Msingi la AsyncProcessor - Badilisha Jina la Parameter ya CLI
**Faili:** `trustgraph-base/trustgraph/base/async_processor.py`
**Laini:** 260-264

**Sasa:**
```python
parser.add_argument(
    '--config-queue',
    default=default_config_queue,
    help=f'Config push queue {default_config_queue}',
)
```

**Imara:**
```python
parser.add_argument(
    '--config-push-queue',
    default=default_config_queue,
    help=f'Config push queue (default: {default_config_queue})',
)
```

**Sababu:**
Majina wazi na ya dhahiri zaidi
Inafanana na jina la ndani la `config_push_queue`
Mabadiliko yanayoweza kusababisha migogoro yanafaa kwani kipengele hivi sasa hakifanyi kazi
Hakuna mabadiliko ya msimbo yanayohitajika katika params.get() - tayari inatafuta jina sahihi

#### Mabadiliko ya 2: Huduma ya Usanidi - Badilisha Jina la Paramu ya CLI
**Faili:** `trustgraph-flow/trustgraph/config/service/service.py`
**Laini:** 276-279

**Sasa:**
```python
parser.add_argument(
    '--push-queue',
    default=default_config_push_queue,
    help=f'Config push queue (default: {default_config_push_queue})'
)
```

**Imara:**
```python
parser.add_argument(
    '--config-push-queue',
    default=default_config_push_queue,
    help=f'Config push queue (default: {default_config_push_queue})'
)
```

**Sababu:**
Majina wazi zaidi - "config-push-queue" yanaeleza zaidi kuliko "push-queue" tu.
Inalingana na jina la ndani `config_push_queue`.
Inafanana na parameter ya `--config-push-queue` ya AsyncProcessor.
Mabadiliko yanayoweza kusababisha migogoro yanafaa kwani kipengele hicho kwa sasa hakifanyi kazi.
Hakuna mabadiliko ya msimbo yanayohitajika katika params.get() - tayari inatafuta jina sahihi.

### Sehemu ya 2: Ongeza Uwekaji wa Vigezo vya Keyspace ya Cassandra

#### Mabadiliko ya 3: Ongeza Parameter ya Keyspace kwenye Moduli ya cassandra_config
**Faili:** `trustgraph-base/trustgraph/base/cassandra_config.py`

**Ongeza hoja ya CLI** (katika kazi ya `add_cassandra_args()`):
```python
parser.add_argument(
    '--cassandra-keyspace',
    default=None,
    help='Cassandra keyspace (default: service-specific)'
)
```

**Ongeza utumiaji wa vigezo vya mazingira** (katika kitendwa `resolve_cassandra_config()`):
```python
keyspace = params.get(
    "cassandra_keyspace",
    os.environ.get("CASSANDRA_KEYSPACE")
)
```

**Sasisha thamani ya kurudiwa** ya `resolve_cassandra_config()`:
Hivi sasa inarudisha: `(hosts, username, password)`
Badilisha ili irudishe: `(hosts, username, password, keyspace)`

**Sababu:**
Inafanana na mtindo uliopo wa usanidi wa Cassandra
Inapatikana kwa huduma zote kupitia `add_cassandra_args()`
Inasaidia usanidi wa CLI na wa vigezo vya mazingira

#### Mabadiliko ya 4: Huduma ya Usanidi - Tumia Vipengele Vilivyobadilishwa
**Faili:** `trustgraph-flow/trustgraph/config/service/service.py`

**Laini ya 30** - Ondoa jina la keyspace lililokodishwa:
```python
# DELETE THIS LINE:
keyspace = "config"
```

**Mishale 69-73** - Sasisha utatuzi wa usanidi wa Cassandra:

**Sasa:**
```python
cassandra_host, cassandra_username, cassandra_password = \
    resolve_cassandra_config(params)
```

**Imara:**
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="config")
```

**Sababu:**
Inahifadhi utangamano na "config" kama chaguo-msingi.
Inaruhusu kubadilishwa kupitia `--cassandra-keyspace` au `CASSANDRA_KEYSPACE`.

#### Mabadiliko ya 5: Huduma za Msingi/Huduma ya Maarifa - Tumia Vipengele vya Kubadilika vya Nafasi ya Kuhifadhia
**Faili:** `trustgraph-flow/trustgraph/cores/service.py`

**Laini ya 37** - Ondoa jina la nafasi ya kuhifadhia lililopangwa:
```python
# DELETE THIS LINE:
keyspace = "knowledge"
```

**Sasisha utatuzi wa usanidi wa Cassandra** (katika eneo sawa kama huduma ya usanidi):
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="knowledge")
```

#### Mabadiliko ya 6: Huduma ya Maktaba - Tumia Vipengele Vilivyobadilika
**Faili:** `trustgraph-flow/trustgraph/librarian/service.py`

**Laini ya 51** - Ondoa jina la eneo la kuhifadhi data lililopangwa:
```python
# DELETE THIS LINE:
keyspace = "librarian"
```

**Sasisha utatuzi wa usanidi wa Cassandra** (katika eneo sawa na huduma ya usanidi):
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="librarian")
```

### Sehemu ya 3: Hamisha Usimamizi wa Mkusanyiko hadi Huduma ya Usanidi

#### Muhtasari
Hamisha mkusanyiko kutoka kwa nafasi ya kuhifadhi "Cassandra librarian" hadi uhifadhi wa huduma ya usanidi. Hii huondoa mada za usimamizi wa uhifadhi zilizopangwa mapema na hurahisisha usanifu kwa kutumia mfumo uliopo wa usambazaji wa usanidi.

#### Usanifu wa Sasa
```
API Request → Gateway → Librarian Service
                            ↓
                    CollectionManager
                            ↓
                    Cassandra Collections Table (librarian keyspace)
                            ↓
                    Broadcast to 4 Storage Management Topics (hardcoded)
                            ↓
        Wait for 4+ Storage Service Responses
                            ↓
                    Response to Gateway
```

#### Usanifu Mpya
```
API Request → Gateway → Librarian Service
                            ↓
                    CollectionManager
                            ↓
                    Config Service API (put/delete/getvalues)
                            ↓
                    Cassandra Config Table (class='collections', key='user:collection')
                            ↓
                    Config Push (to all subscribers on config-push-queue)
                            ↓
        All Storage Services receive config update independently
```

#### Mabadiliko ya 7: Msimamizi wa Mkusanyiko - Tumia API ya Huduma ya Usanidi
**Faili:** `trustgraph-flow/trustgraph/librarian/collection_manager.py`

**Ondoa:**
Matumizi ya `LibraryTableStore` (Mistari 33, 40-41)
Uanzishaji wa watengenezaji wa usimamizi wa hifadhi (Mistari 86-140)
Njia ya `on_storage_response` (Mistari 400-430)
Ufuatiliaji wa `pending_deletions` (Mistari 57, 90-96, na matumizi katika maeneo mengine)

**Ongeza:**
Mteja wa huduma ya usanidi kwa simu za API (mfumo wa ombi/jibu)

**Uwekaji wa Mteja wa Usanidi:**
```python
# In __init__, add config request/response producers/consumers
from trustgraph.schema.services.config import ConfigRequest, ConfigResponse

# Producer for config requests
self.config_request_producer = Producer(
    client=pulsar_client,
    topic=config_request_queue,
    schema=ConfigRequest,
)

# Consumer for config responses (with correlation ID)
self.config_response_consumer = Consumer(
    taskgroup=taskgroup,
    client=pulsar_client,
    flow=None,
    topic=config_response_queue,
    subscriber=f"{id}-config",
    schema=ConfigResponse,
    handler=self.on_config_response,
)

# Tracking for pending config requests
self.pending_config_requests = {}  # request_id -> asyncio.Event
```

**Badilisha `list_collections` (Mistari 145-180):**
```python
async def list_collections(self, user, tag_filter=None, limit=None):
    """List collections from config service"""
    # Send getvalues request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='getvalues',
        type='collections',
    )

    # Send request and wait for response
    response = await self.send_config_request(request)

    # Parse collections from response
    collections = []
    for key, value_json in response.values.items():
        if ":" in key:
            coll_user, collection = key.split(":", 1)
            if coll_user == user:
                metadata = json.loads(value_json)
                collections.append(CollectionMetadata(**metadata))

    # Apply tag filtering in-memory (as before)
    if tag_filter:
        collections = [c for c in collections if any(tag in c.tags for tag in tag_filter)]

    # Apply limit
    if limit:
        collections = collections[:limit]

    return collections

async def send_config_request(self, request):
    """Send config request and wait for response"""
    event = asyncio.Event()
    self.pending_config_requests[request.id] = event

    await self.config_request_producer.send(request)
    await event.wait()

    return self.pending_config_requests.pop(request.id + "_response")

async def on_config_response(self, message, consumer, flow):
    """Handle config response"""
    response = message.value()
    if response.id in self.pending_config_requests:
        self.pending_config_requests[response.id + "_response"] = response
        self.pending_config_requests[response.id].set()
```

**Badilisha `update_collection` (Mistari 182-312):**
```python
async def update_collection(self, user, collection, name, description, tags):
    """Update collection via config service"""
    # Create metadata
    metadata = CollectionMetadata(
        user=user,
        collection=collection,
        name=name,
        description=description,
        tags=tags,
    )

    # Send put request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='put',
        type='collections',
        key=f'{user}:{collection}',
        value=json.dumps(metadata.to_dict()),
    )

    response = await self.send_config_request(request)

    if response.error:
        raise RuntimeError(f"Config update failed: {response.error.message}")

    # Config service will trigger config push automatically
    # Storage services will receive update and create collections
```

**Badilisha `delete_collection` (Mistari 314-398):**
```python
async def delete_collection(self, user, collection):
    """Delete collection via config service"""
    # Send delete request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='delete',
        type='collections',
        key=f'{user}:{collection}',
    )

    response = await self.send_config_request(request)

    if response.error:
        raise RuntimeError(f"Config delete failed: {response.error.message}")

    # Config service will trigger config push automatically
    # Storage services will receive update and delete collections
```

**Muundo wa Meta Data ya Mkusanyiko:**
Hifadhiwa katika jedwali la usanidi kama: `class='collections', key='user:collection'`
Thamani ni CollectionMetadata iliyopigwa muundo wa JSON (bila mashamba ya wakati)
Mashamba: `user`, `collection`, `name`, `description`, `tags`
Mfano: `class='collections', key='alice:my-docs', value='{"user":"alice","collection":"my-docs","name":"My Documents","description":"...","tags":["work"]}'`

#### Mabadiliko ya 8: Huduma ya Maktaba - Ondoa Miundombinu ya Usimamizi wa Uhifadhi
**Faili:** `trustgraph-flow/trustgraph/librarian/service.py`

**Ondoa:**
Wafalme wa usimamizi wa uhifadhi (Mistari 173-190):
  `vector_storage_management_producer`
  `object_storage_management_producer`
  `triples_storage_management_producer`
Mfumo wa matumizi ya majibu ya uhifadhi (Mistari 192-201)
Msimamizi `on_storage_response` (Mistari 467-473)

**Badilisha:**
Uanzishaji wa CollectionManager (Mistari 215-224) - ondoa vigezo vya mtayarishaji wa uhifadhi

**Kumbuka:** API ya nje ya mkusanyiko inabaki bila kubadilika:
`list-collections`
`update-collection`
`delete-collection`

#### Mabadiliko ya 9: Ondoa Jedwali la Mkusanyiko kutoka LibraryTableStore
**Faili:** `trustgraph-flow/trustgraph/tables/library.py`

**Futa:**
Kauli ya kuunda jedwali la Mkusanyiko (Mistari 114-127)
Maneno yaliyotayarishwa ya Mkusanyiko (Mistari 205-240)
Mbinu zote za mkusanyiko (Mistari 578-717):
  `ensure_collection_exists`
  `list_collections`
  `update_collection`
  `delete_collection`
  `get_collection`
  `create_collection`

**Mazingatio:**
Mkusanyiko sasa huhifadhiwa kwenye meza ya usanidi.
Mabadiliko yanayoweza kusababisha migogoro yanayokubalika - hakuna uhamisho wa data unaohitajika.
Inarahisisha huduma ya "librarian" kwa kiasi kikubwa.

#### Mabadiliko ya 10: Huduma za Uhifadhi - Usimamizi wa Mkusanyiko Kulingana na Usanidi ✅ IMEKAMILIKA

**Hali:** Vifaa vyote 11 vya uhifadhi vimehamishwa ili kutumia `CollectionConfigHandler`.

**Huduma Zinazoathirika (jumla ya 11):**
Uingizaji wa hati: milvus, pinecone, qdrant
Uingizaji wa grafu: milvus, pinecone, qdrant
Uhifadhi wa vitu: cassandra
Uhifadhi wa "triples": cassandra, falkordb, memgraph, neo4j

**Faili:**
`trustgraph-flow/trustgraph/storage/doc_embeddings/milvus/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/pinecone/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/milvus/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/pinecone/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/qdrant/write.py`
`trustgraph-flow/trustgraph/storage/objects/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/triples/falkordb/write.py`
`trustgraph-flow/trustgraph/storage/triples/memgraph/write.py`
`trustgraph-flow/trustgraph/storage/triples/neo4j/write.py`

**Mfumo wa Utendaji (huduma zote):**

1. **Jisajili "config handler" katika `__init__`:**
```python
# Add after AsyncProcessor initialization
self.register_config_handler(self.on_collection_config)
self.known_collections = set()  # Track (user, collection) tuples
```

2. **Teleza kidhibiti cha usanidi:**
```python
async def on_collection_config(self, config, version):
    """Handle collection configuration updates"""
    logger.info(f"Collection config version: {version}")

    if "collections" not in config:
        return

    # Parse collections from config
    # Key format: "user:collection" in config["collections"]
    config_collections = set()
    for key in config["collections"].keys():
        if ":" in key:
            user, collection = key.split(":", 1)
            config_collections.add((user, collection))

    # Determine changes
    to_create = config_collections - self.known_collections
    to_delete = self.known_collections - config_collections

    # Create new collections (idempotent)
    for user, collection in to_create:
        try:
            await self.create_collection_internal(user, collection)
            self.known_collections.add((user, collection))
            logger.info(f"Created collection: {user}/{collection}")
        except Exception as e:
            logger.error(f"Failed to create {user}/{collection}: {e}")

    # Delete removed collections (idempotent)
    for user, collection in to_delete:
        try:
            await self.delete_collection_internal(user, collection)
            self.known_collections.discard((user, collection))
            logger.info(f"Deleted collection: {user}/{collection}")
        except Exception as e:
            logger.error(f"Failed to delete {user}/{collection}: {e}")
```

3. **Anzisha kukusanya data inayojulikana wakati wa kuanza:**
```python
async def start(self):
    """Start the processor"""
    await super().start()
    await self.sync_known_collections()

async def sync_known_collections(self):
    """Query backend to populate known_collections set"""
    # Backend-specific implementation:
    # - Milvus/Pinecone/Qdrant: List collections/indexes matching naming pattern
    # - Cassandra: Query keyspaces or collection metadata
    # - Neo4j/Memgraph/FalkorDB: Query CollectionMetadata nodes
    pass
```

4. **Kuboresha mbinu zilizopo za utendaji:**
```python
# Rename and remove response sending:
# handle_create_collection → create_collection_internal
# handle_delete_collection → delete_collection_internal

async def create_collection_internal(self, user, collection):
    """Create collection (idempotent)"""
    # Same logic as current handle_create_collection
    # But remove response producer calls
    # Handle "already exists" gracefully
    pass

async def delete_collection_internal(self, user, collection):
    """Delete collection (idempotent)"""
    # Same logic as current handle_delete_collection
    # But remove response producer calls
    # Handle "not found" gracefully
    pass
```

5. **Ondoa miundomino ya usimamizi wa hifadhi:**
   Ondoa usanidi na uanzishaji wa `self.storage_request_consumer`
   Ondoa usanidi wa `self.storage_response_producer`
   Ondoa njia ya utaratibu wa `on_storage_management`
   Ondoa vipimo (metrics) vya usimamizi wa hifadhi
   Ondoa uingizaji (imports): `StorageManagementRequest`, `StorageManagementResponse`

**Mazingatio Maalum ya Seva ya Nyuma (Backend):**

**Vihifadhi vya data (Vector stores) (Milvus, Pinecone, Qdrant):** Fuatilia `(user, collection)` ya kimantiki katika `known_collections`, lakini inaweza kuunda mkusanyiko mwingi wa seva ya nyuma kwa kila kipimo. Endeleza mtindo wa uundaji wa polepole. Operesheni za kufuta lazima iondoe matoleo yote ya kipimo.

**Cassandra Objects:** Mikusanyiko ni sifa za mstari, sio muundo. Fuatilia taarifa za kiwango cha keyspace.

**Vihifadhi vya grafu (Graph stores) (Neo4j, Memgraph, FalkorDB):** Tafuta nodi za `CollectionMetadata` wakati wa kuanza. Unda/futa nodi za metadata wakati wa kusawazisha.

**Cassandra Triples:** Tumia API ya `KnowledgeGraph` kwa operesheni za mkusanyiko.

**Mambo Muhimu ya Ubunifu:**

**Ulinganifu wa muda (Eventual consistency):** Hakuna utaratibu wa ombi/jibu, utaratibu wa kusukuma usanidi hutangazwa
**Ulinganifu (Idempotency):** Operesheni zote za kuunda/kufuta lazima ziwe salama kufanywa tena
**Usimamizi wa makosa (Error handling):** Leta makosa lakini usizuie sasisho za usanidi
**Kujirejesha (Self-healing):** Operesheni ambazo zimefeli zitajaribu tena wakati wa sasisho la usanidi lijayo
**Muundo wa ufunguo wa mkusanyiko (Collection key format):** `"user:collection"` katika `config["collections"]`

#### Mabadiliko ya 11: Sasisha Mpango wa Mkusaniko - Ondoa Alama za Muda (Timestamps)
**Faili:** `trustgraph-base/trustgraph/schema/services/collection.py`

**Badilisha CollectionMetadata (Mistari 13-21):**
Ondoa sehemu za `created_at` na `updated_at`:
```python
class CollectionMetadata(Record):
    user = String()
    collection = String()
    name = String()
    description = String()
    tags = Array(String())
    # Remove: created_at = String()
    # Remove: updated_at = String()
```

**Badilisha `CollectionManagementRequest` (Mistari 25-47):**
Ondoa sehemu za wakati:
```python
class CollectionManagementRequest(Record):
    operation = String()
    user = String()
    collection = String()
    timestamp = String()
    name = String()
    description = String()
    tags = Array(String())
    # Remove: created_at = String()
    # Remove: updated_at = String()
    tag_filter = Array(String())
    limit = Integer()
```

**Sababu:**
Wakati (Timestamps) havi faida kwa makusanyo.
Huduma ya usanidi (config) inadhibiti ufuatiliaji wake wa toleo.
Inarahisisha muundo na kupunguza uhifadhi.

#### Faida za Uhamishaji wa Huduma ya Usanidi

1. ✅ **Inaondoa masuala ya usimamizi wa uhifadhi yaliyopangwa awali** - Inatatua kizuizi cha wateja wengi.
2. ✅ **Uratibu rahisi zaidi** - Hakuna utaratibu ngumu wa kusubiri majibu kutoka kwa huduma 4+ za uhifadhi.
3. ✅ **Ulinganifu wa muda** - Huduma za uhifadhi husasishwa kwa kujitegemea kupitia utaratibu wa usanidi.
4. ✅ **Uaminifu bora zaidi** - Uratibu wa kudumu wa usanidi dhidi ya ombi/jibu lisilo la kudumu.
5. ✅ **Mfumo wa usanidi uliounganishwa** - Makusanyo yanatibiwa kama usanidi.
6. ✅ **Inapunguza utata** - Inondoa mistari ~300 ya nambari ya uratibu.
7. ✅ **Inafaa kwa wateja wengi** - Usanidi tayari una msaada wa kutenganisha wateja kupitia nafasi.
8. ✅ **Ufuatiliaji wa toleo** - Mfumo wa toleo wa huduma ya usanidi hutoa kumbukumbu ya uhakiki.

## Maelezo ya Utendaji

### Utangamano wa Nyuma

**Mabadiliko ya Vigezo:**
Mabadiliko ya majina ya vigezo vya CLI ni mabadiliko ambayo yanaweza kusababisha matatizo lakini yanapokelewa (kipengele hapo kwa sasa hakifanyi kazi).
Huduma zinafanya kazi bila vigezo (tumia chaguo-msingi).
Nafasi chaguo-msingi zimehifadhiwa: "config", "knowledge", "librarian".
Kichefuchefu chaguo-msingi: `persistent://tg/config/config`

**Usimamizi wa Makusanyo:**
**Mabadiliko ambayo yanaweza kusababisha matatizo:** Jedwali la makusanyo limeondolewa kutoka kwa nafasi ya "librarian".
**Hakuna uhamishaji wa data unaotolewa** - inakubalika kwa hatua hii.
API ya makusanyo ya nje haijabadilika (operesheni za kuorodhesha/kusasisha/kufuta).
Muundo wa metadata ya makusanyo umeboreshwa (wakati umeondolewa).

### Mahitaji ya Majaribio

**Majaribio ya Vigezo:**
1. Thibitisha kwamba kiparamu `--config-push-queue` hufanya kazi kwenye huduma ya "graph-embeddings".
2. Thibitisha kwamba kiparamu `--config-push-queue` hufanya kazi kwenye huduma ya "text-completion".
3. Thibitisha kwamba kiparamu `--config-push-queue` hufanya kazi kwenye huduma ya usanidi.
4. Thibitisha kwamba kiparamu `--cassandra-keyspace` hufanya kazi kwa huduma ya usanidi.
5. Thibitisha kwamba kiparamu `--cassandra-keyspace` hufanya kazi kwa huduma ya "cores".
6. Thibitisha kwamba kiparamu `--cassandra-keyspace` hufanya kazi kwa huduma ya "librarian".
7. Thibitisha kwamba huduma zinafanya kazi bila vigezo (zinatumia chaguo-msingi).
8. Thibitisha uwekaji wa wateja wengi na majina ya kichefuchefu na nafasi maalum.

**Majaribio ya Usimamizi wa Makusanyo:**
9. Thibitisha operesheni `list-collections` kupitia huduma ya usanidi.
10. Thibitisha kwamba `update-collection` huunda/kusasisha kwenye jedwali la usanidi.
11. Thibitisha kwamba `delete-collection` huondoa kutoka kwenye jedwali la usanidi.
12. Thibitisha kwamba utaratibu wa "config push" huwashwa wakati wa sasisho za makusanyo.
13. Thibitisha kwamba utaratibu wa kuchujwa wa lebo hufanya kazi na uhifadhi unaotegemea usanidi.
14. Thibitisha kwamba operesheni za makusanyo hufanya kazi bila sehemu za wakati.

### Mfano wa Uwekaji wa Wateja Wengi
```bash
# Tenant: tg-dev
graph-embeddings \
  -p pulsar+ssl://broker:6651 \
  --pulsar-api-key <KEY> \
  --config-push-queue persistent://tg-dev/config/config

config-service \
  -p pulsar+ssl://broker:6651 \
  --pulsar-api-key <KEY> \
  --config-push-queue persistent://tg-dev/config/config \
  --cassandra-keyspace tg_dev_config
```

## Uchambuzi wa Athari

### Huduma Zinazoathiriwa na Mabadiliko 1-2 (Kubadilisha Jina la Paramu ya CLI)
Huduma zote zinazorithi kutoka kwa AsyncProcessor au FlowProcessor:
config-service
cores-service
librarian-service
graph-embeddings
document-embeddings
text-completion-* (wote watoa huduma)
extract-* (wote waangamizi)
query-* (huduma zote za kuulizia)
retrieval-* (huduma zote za RAG)
storage-* (huduma zote za kuhifadhi)
Na huduma zingine 20+

### Huduma Zinazoathiriwa na Mabadiliko 3-6 (Nafasi ya Cassandra)
config-service
cores-service
librarian-service

### Huduma Zinazoathiriwa na Mabadiliko 7-11 (Usimamizi wa Mkusanyiko)

**Mabadiliko ya Mara Moja:**
librarian-service (collection_manager.py, service.py)
tables/library.py (ondoa meza ya mkusanyiko)
schema/services/collection.py (ondoa alama ya muda)

**Mabadiliko Yaliyokamilika (Mabadiliko ya 10):** ✅
Huduma zote za kuhifadhi (jumla ya 11) - zimehamishwa kwa utaratibu wa kusukuma usanidi kwa mkusanyiko kupitia `CollectionConfigHandler`
Mfumo wa usimamizi wa kuhifadhi umeondolewa kutoka `storage.py`

## Mambo ya Kuzingatia ya Baadaye

### Mfumo wa Nafasi ya Mtumiaji Kila Mmoja

Huduma zingine hutumia **nafasi za mtumiaji kila mmoja** kwa njia ya moja kwa moja, ambapo kila mtumiaji hupata nafasi yake mwenyewe ya Cassandra:

**Huduma zenye nafasi za mtumiaji kila mmoja:**
1. **Huduma ya Uulizia ya Triples** (`trustgraph-flow/trustgraph/query/triples/cassandra/service.py:65`)
   Inatumia `keyspace=query.user`
2. **Huduma ya Uulizia ya Vitabu** (`trustgraph-flow/trustgraph/query/objects/cassandra/service.py:479`)
   Inatumia `keyspace=self.sanitize_name(user)`
3. **Ufikiaji wa Moja kwa Moja wa KnowledgeGraph** (`trustgraph-flow/trustgraph/direct/cassandra_kg.py:18`)
   Paramu ya chaguo-msingi `keyspace="trustgraph"`

**Hali:** Hizi **hazibadiliki** katika maelezo haya.

**Hakikisha Upya wa Baadaye:**
Tathmini ikiwa mfumo wa nafasi ya mtumiaji kila mmoja huunda masuala ya kutenganisha wateja
Fikiria ikiwa usambazaji wa wateja mbalimbali unahitaji muundo wa mbele ya nafasi (k.m., `tenant_a_user1`)
Angalia uwezekano wa migongano ya kitambulisho cha mtumiaji kati ya wateja
Tathmini ikiwa nafasi moja iliyoshirikiwa kwa kila mteja na kutenganisha mstari kwa msingi wa mtumiaji ni bora

**Kumbuka:** Hii haizuie utekelezaji wa sasa wa wateja mbalimbali lakini inapaswa kukaguliwa kabla ya utekelezaji wa wateja mbalimbali wa uzalishaji.

## Awamu za Utendaji

### Awamu ya 1: Marekebisho ya Paramu (Mabadiliko 1-6)
Marekebisho ya jina la paramu `--config-push-queue`
Ongeza msaada wa paramu `--cassandra-keyspace`
**Matokeo:** Mpangilio wa folyo na nafasi ya wateja mbalimbali umeanzishwa

### Awamu ya 2: Uhamishaji wa Usimamizi wa Mkusanyiko (Mabadiliko 7-9, 11)
Hamisha uhifadhi wa mkusanyiko kwa huduma ya usanidi
Ondoa meza ya mkusanyiko kutoka kwa librarian
Sasisha mfumo wa mkusanyiko (ondoa alama za muda)
**Matokeo:** Huondoa mada zilizokota za usimamizi wa uhifadhi, hurahisisha librarian

### Awamu ya 3: Masasisho ya Huduma ya Uhifadhi (Mabadiliko ya 10) ✅ IMEKAMILIKA
Zesasisha huduma zote za kuhifadhi ili zitumie utaratibu wa kusukuma usanidi kwa mkusanyiko kupitia `CollectionConfigHandler`
Ondoa miundombinu ya ombi/jibu la usimamizi wa uhifadhi
Ondoa ufafanuzi wa zamani wa mfumo
**Matokeo:** Usimamizi kamili wa mkusanyiko unaotegemea usanidi umefikiwa

## Marejeleo
GitHub Issue: https://github.com/trustgraph-ai/trustgraph/issues/582
Faili Zinazohusiana:
  `trustgraph-base/trustgraph/base/async_processor.py`
  `trustgraph-base/trustgraph/base/cassandra_config.py`
  `trustgraph-base/trustgraph/schema/core/topic.py`
  `trustgraph-base/trustgraph/schema/services/collection.py`
  `trustgraph-flow/trustgraph/config/service/service.py`
  `trustgraph-flow/trustgraph/cores/service.py`
  `trustgraph-flow/trustgraph/librarian/service.py`
  `trustgraph-flow/trustgraph/librarian/collection_manager.py`
  `trustgraph-flow/trustgraph/tables/library.py`
