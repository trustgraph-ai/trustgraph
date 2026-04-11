# Mifumo ya Uwasilishaji na Ufuatiliaji (Pub/Sub)

## Muhtasari

Hati hii inaorodhesha miunganisho yote kati ya mfumo wa TrustGraph na miundomino ya uwasilishaji na ufuatiliaji. Kwa sasa, mfumo huu umewekwa ili kutumia Apache Pulsar. Uchunguzi huu unaeleza maeneo yote ya kuunganisha ili kutoa taarifa kwa urekebishaji wa baadaye kuelekea uainishaji wa uwasilishaji na ufuatiliaji unaoweza kusanidiwa.

## Hali ya Sasa: Maeneo ya Kuunganisha ya Pulsar

### 1. Matumizi ya Moja kwa Moja ya Mteja wa Pulsar

**Mahali:** `trustgraph-flow/trustgraph/gateway/service.py`

Lango la API huleta na kuunda mteja wa Pulsar moja kwa moja:

**Laini ya 20:** `import pulsar`
**Laini za 54-61:** Uundaji wa moja kwa moja wa `pulsar.Client()` pamoja na `pulsar.AuthenticationToken()` inayohitajika.
**Laini za 33-35:** Usanidi chaguo-msingi wa hosti wa Pulsar kutoka kwa vigezo vya mazingira.
**Laini za 178-192:** Vigezo vya CLI kwa `--pulsar-host`, `--pulsar-api-key`, na `--pulsar-listener`.
**Laini za 78, 124:** Hupitisha `pulsar_client` kwa `ConfigReceiver` na `DispatcherManager`.

Hii ndio eneo pekee ambalo huunda mteja wa Pulsar moja kwa moja nje ya safu ya uainishaji.

### 2. Muundo wa Msingi wa Mchakato

**Mahali:** `trustgraph-base/trustgraph/base/async_processor.py`

Darasa la msingi kwa mchakato wote hutoa uwezo wa kuunganisha na Pulsar:

**Laini ya 9:** `import _pulsar` (kwa usimamizi wa makosa)
**Laini ya 18:** `from . pubsub import PulsarClient`
**Laini ya 38:** Huunda `pulsar_client_object = PulsarClient(**params)`
**Laini za 104-108:** Vipengele ambavyo huonyesha `pulsar_host` na `pulsar_client`
**Laini ya 250:** Njia ya tuli `add_args()` huita `PulsarClient.add_args(parser)` kwa vigezo vya CLI
**Laini za 223-225:** Usimamizi wa makosa kwa `_pulsar.Interrupted`

Mchakato wote hurithi kutoka kwa `AsyncProcessor`, na hivyo kuwa eneo kuu la kuunganisha.

### 3. Uainishaji wa Mtumiaji

**Mahali:** `trustgraph-base/trustgraph/base/consumer.py`

Huchukua meseji kutoka kwa folyo na kutoa kazi za utendaji:

**Uingizaji wa Pulsar:**
**Laini ya 12:** `from pulsar.schema import JsonSchema`
**Laini ya 13:** `import pulsar`
**Laini ya 14:** `import _pulsar`

**Matumizi maalum ya Pulsar:**
**Laini za 100, 102:** `pulsar.InitialPosition.Earliest` / `pulsar.InitialPosition.Latest`
**Laini ya 108:** `JsonSchema(self.schema)` wrapper
**Laini ya 110:** `pulsar.ConsumerType.Shared`
**Laini za 104-111:** `self.client.subscribe()` pamoja na vigezo maalum ya Pulsar
**Laini za 143, 150, 65:** `consumer.unsubscribe()` na `consumer.close()` methods
**Laini ya 162:** `_pulsar.Timeout` exception
**Laini za 182, 205, 232:** `consumer.acknowledge()` / `consumer.negative_acknowledge()`

**Faili ya spec:** `trustgraph-base/trustgraph/base/consumer_spec.py`
**Laini ya 22:** Inarejelea `processor.pulsar_client`

### 4. Uainishaji wa Mtume

**Mahali:** `trustgraph-base/trustgraph/base/producer.py`

Hutuma meseji kwa folyo:

**Uingizaji wa Pulsar:**
**Laini ya 2:** `from pulsar.schema import JsonSchema`

**Matumizi maalum ya Pulsar:**
**Laini ya 49:** `JsonSchema(self.schema)` wrapper
**Laini za 47-51:** `self.client.create_producer()` pamoja na vigezo maalum ya Pulsar (mada, schema, chunking_enabled)
**Laini za 31, 76:** `producer.close()` method
**Laini za 64-65:** `producer.send()` pamoja na meseji na vipengele

**Faili ya spec:** `trustgraph-base/trustgraph/base/producer_spec.py`
**Laini ya 18:** Inarejelea `processor.pulsar_client`

### 5. Uainishaji wa Mchapishaji

**Mahali:** `trustgraph-base/trustgraph/base/publisher.py`

Uchapishaji wa meseji usiohusisha na uwekaji wa folyo:

**Uingizaji wa Pulsar:**
**Laini ya 2:** `from pulsar.schema import JsonSchema`
**Laini ya 6:** `import pulsar`

**Matumizi maalum ya Pulsar:**
**Laini ya 52:** `JsonSchema(self.schema)` wrapper
**Laini za 50-54:** `self.client.create_producer()` pamoja na vigezo maalum ya Pulsar
**Laini za 101, 103:** `producer.send()` pamoja na meseji na vipengele vya hiari
**Laini za 106-107:** `producer.flush()` na `producer.close()` methods

### 6. Uainishaji wa Mlisani

**Mahali:** `trustgraph-base/trustgraph/base/subscriber.py`

Inatoa usambazaji wa ujumbe kwa wapokeaji wengi kutoka kwa folyo:

**Uingizaji kutoka Pulsar:**
**Laini ya 6:** `from pulsar.schema import JsonSchema`
**Laini ya 8:** `import _pulsar`

**Matumizi maalum ya Pulsar:**
**Laini ya 55:** `JsonSchema(self.schema)` wrapper
**Laini ya 57:** `self.client.subscribe(**subscribe_args)`
**Laini 101, 136, 160, 167-172:** Vizuizi vya Pulsar: `_pulsar.Timeout`, `_pulsar.InvalidConfiguration`, `_pulsar.AlreadyClosed`
**Laini 159, 166, 170:** Mbinu za mtumiaji: `negative_acknowledge()`, `unsubscribe()`, `close()`
**Laini 247, 251:** Utambuzi wa ujumbe: `acknowledge()`, `negative_acknowledge()`

**Faili ya spec:** `trustgraph-base/trustgraph/base/subscriber_spec.py`
**Laini ya 19:** Inarejelea `processor.pulsar_client`

### 7. Mfumo wa Schemas (Heart of Darkness)

**Mahali:** `trustgraph-base/trustgraph/schema/`

Schemas kila ujumbe katika mfumo huu imefafanuliwa kwa kutumia mfumo wa schemas wa Pulsar.

**Vipengele muhimu:** `schema/core/primitives.py`
**Laini ya 2:** `from pulsar.schema import Record, String, Boolean, Array, Integer`
Schemas zote hurithi kutoka kwa darasa la msingi la Pulsar `Record`
Aina zote za sehemu ni aina za Pulsar: `String()`, `Integer()`, `Boolean()`, `Array()`, `Map()`, `Double()`

**Sampuli za schemas:**
`schema/services/llm.py` (Laini ya 2): `from pulsar.schema import Record, String, Array, Double, Integer, Boolean`
`schema/services/config.py` (Laini ya 2): `from pulsar.schema import Record, Bytes, String, Boolean, Array, Map, Integer`

**Jina la mada:** `schema/core/topic.py`
**Laini 2-3:** Muundo wa mada: `{kind}://{tenant}/{namespace}/{topic}`
Muundo huu wa URI ni maalum kwa Pulsar (k.m.e., `persistent://tg/flow/config`)

**Athari:**
Ufafanuzi wote wa ujumbe wa ombi/jibu katika msimbo wote hutumia schemas za Pulsar
Hii inajumuisha huduma za: config, flow, llm, prompt, query, storage, agent, collection, diagnosis, library, lookup, nlp_query, objects_query, retrieval, structured_query
Ufafanuzi wa schemas huingizwa na kutumika kwa kina katika processors na huduma zote

## Muhtasari

### Utegemezi wa Pulsar kwa Kategoria

1. **Uundaji wa mteja:**
   Moja kwa moja: `gateway/service.py`
   Imefichwa: `async_processor.py` → `pubsub.py` (PulsarClient)

2. **Usafirishaji wa ujumbe:**
   Mtumiaji: `consumer.py`, `consumer_spec.py`
   Mtayarishaji: `producer.py`, `producer_spec.py`
   Mchapishaji: `publisher.py`
   Msubiri: `subscriber.py`, `subscriber_spec.py`

3. **Mfumo wa schemas:**
   Aina za msingi: `schema/core/primitives.py`
   Schemas zote za huduma: `schema/services/*.py`
   Jina la mada: `schema/core/topic.py`

4. **Dhima maalum za Pulsar zinazohitajika:**
   Ujumbe unaotegemea mada
   Mfumo wa schemas (Rekodi, aina za sehemu)
   Usajili uliogawanywa
   Utambuzi wa ujumbe (chanya/hasi)
   Nafasi ya mtumiaji (mapema/ya hivi karibuni)
   Sifa za ujumbe
   Nafasi ya awali na aina za mtumiaji
   Usaidizi wa chunking
   Mada za kudumu vs. zisizo za kudumu

### Changamoto za Urekebishaji

Habari njema: Safu ya uainishaji (Mtumiaji, Mtayarishaji, Mchapishaji, Msubiri) hutoa uainishaji safi wa mwingiliano mwingi wa Pulsar.

Changamoto:
1. **Ukuaji wa mfumo wa schemas:** Ufafanuzi kila ujumbe hutumia `pulsar.schema.Record` na aina za Pulsar
2. **Enums maalum za Pulsar:** `InitialPosition`, `ConsumerType`
3. **Vizuizi vya Pulsar:** `_pulsar.Timeout`, `_pulsar.Interrupted`, `_pulsar.InvalidConfiguration`, `_pulsar.AlreadyClosed`
4. **Mifumo ya mbinu:** `acknowledge()`, `negative_acknowledge()`, `subscribe()`, `create_producer()`, n.k.
5. **Muundo wa URI ya mada:** Muundo wa `kind://tenant/namespace/topic` wa Pulsar

### Hatua Zinazofuata

Ili kufanya miundombinu ya p/s kuwa configurable, tunahitaji:

1. Kuunda kiolesura cha uainishaji kwa mfumo wa mteja/schema
2. Kuainisha enums na vizuizi maalum za Pulsar
3. Kuunda wrappers za schemas au ufafanuzi mbadala wa schemas
4. Kutekeleza kiolesura kwa wateja na mifumo mingine (Kafka, RabbitMQ, Redis Streams, n.k.)
5. Kusasisha `pubsub.py` ili iwe configurable na iunge mkono mifumo mingi
6. Kutoa njia ya uhamishaji kwa usakinishaji uliopo

## Mfumo Mkuu wa 1: Mfumo wa Adapta na Safu ya Tafsiri ya Schemas

### Maarifa Muhimu
Mfumo wa schemas ndio msingi wa mfumo huu.



**1. Endelea kutumia muundo wa Pulsar kama uwakilishi wa ndani**
Usiandike upya maelezo yote ya muundo.
Muundo utabaki `pulsar.schema.Record` ndani.
Tumia adapta ili kutafsiri katika eneo kati ya programu yetu na mfumo wa utumaji/kupokea.

**2. Unda safu ya utengwa kwa utumaji/kupokea:**

```
┌─────────────────────────────────────┐
│   Existing Code (unchanged)         │
│   - Uses Pulsar schemas internally  │
│   - Consumer/Producer/Publisher     │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│   PubSubFactory (configurable)      │
│   - Creates backend-specific client │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        │             │
┌───────▼─────┐  ┌────▼─────────┐
│ PulsarAdapter│  │ KafkaAdapter │  etc...
│ (passthrough)│  │ (translates) │
└──────────────┘  └──────────────┘
```

**3. Tafakikata viambishi vya dhahabu:**
`PubSubClient` - muunganisho wa mteja
`PubSubProducer` - kutuma ujumbe
`PubSubConsumer` - kupokea ujumbe
`SchemaAdapter` - kutafsiri muundo wa Pulsar kuwa/kutoka JSON au muundo maalum wa mfumo wa nyuma

**4. Maelezo ya utekelezaji:**

Kwa **adapta ya Pulsar**: Karibu kupita moja kwa moja, tafsiri ndogo.

Kwa **mfumo mwingine wa nyuma** (Kafka, RabbitMQ, n.k.):
Tafsiri vitu vya rekodi ya Pulsar kuwa JSON/bytes
Linganisha dhana kama:
  `InitialPosition.Earliest/Latest` → auto.offset.reset ya Kafka
  `acknowledge()` → kukubali kwa Kafka
  `negative_acknowledge()` → mfumo wa kurudisha au DLQ
  URI za mada → majina ya mada maalum ya mfumo wa nyuma

### Uchambuzi

**Faida:**
✅ Mabadiliko madogo ya msimbo kwa huduma zilizopo
✅ Muundo unaendelea kuwa kama ilivyo (hakuna marekebisho makubwa)
✅ Njia ya hatua kwa hatua ya uhamishaji
✅ Watumiaji wa Pulsar hawona tofauti
✅ Mifumo mipya ya nyuma inaongezwa kupitia adapta

**Hasara:**
⚠️ Bado ina utegemezi wa Pulsar (kwa maelezo ya muundo)
⚠️ Mizozo mingine inapotafsiri dhana

### Toleo Mbadala

Unda **mfumo wa muundo wa TrustGraph** ambao hautegemei mfumo wowote wa kutuma na kupokea (kwa kutumia madarasa ya data au Pydantic), kisha uzalisha muundo wa Pulsar/Kafka/n.k. kutoka humo. Hii inahitaji kuandikewa tena kila faili ya muundo na inaweza kusababisha mabadiliko.

### Mapendekezo kwa Rasimu ya 1

Anza na **mbinu ya adapta** kwa sababu:
1. Ni ya vitendo - inafanya kazi na msimbo uliopo
2. Inathibitisha dhana kwa hatari ndogo
3. Inaweza kubadilika kuwa mfumo wa asili wa muundo baadaye ikiwa inahitajika
4. Inadumishwa kupitia usanidi: variable moja ya mazingira inabadilisha mifumo ya nyuma

## Mbinu ya Rasimu ya 2: Mfumo wa Muundo Usio na Utendaji wa Nyuma na Madarasa ya Data

### Dhana Kuu

Tumia **madarasa ya data ya Python** kama muundo wa muundo wa kati. Kila mfumo wa nyuma wa kutuma na kupokea hutoa utafsiri wake mwenyewe wa kuandika/kusoma kwa madarasa ya data, na kuondoa hitaji kwamba muundo wa Pulsar uendelee kuwa katika msimbo.

### Ulinganifu wa Muundo katika Kiwango cha Kiwanda

Badala ya kutafsiri muundo wa Pulsar, **kila mfumo wa nyuma hutoa utunzaji wake mwenyewe wa muundo** ambao unafanya kazi na madarasa ya data ya Python ya kawaida.

### Mtiririko wa Mchapishaji

```python
# 1. Get the configured backend from factory
pubsub = get_pubsub()  # Returns PulsarBackend, MQTTBackend, etc.

# 2. Get schema class from the backend
# (Can be imported directly - backend-agnostic)
from trustgraph.schema.services.llm import TextCompletionRequest

# 3. Create a producer/publisher for a specific topic
producer = pubsub.create_producer(
    topic="text-completion-requests",
    schema=TextCompletionRequest  # Tells backend what schema to use
)

# 4. Create message instances (same API regardless of backend)
request = TextCompletionRequest(
    system="You are helpful",
    prompt="Hello world",
    streaming=False
)

# 5. Send the message
producer.send(request)  # Backend serializes appropriately
```

### Mchakato wa Mtumiaji

```python
# 1. Get the configured backend
pubsub = get_pubsub()

# 2. Create a consumer
consumer = pubsub.subscribe(
    topic="text-completion-requests",
    schema=TextCompletionRequest  # Tells backend how to deserialize
)

# 3. Receive and deserialize
msg = consumer.receive()
request = msg.value()  # Returns TextCompletionRequest dataclass instance

# 4. Use the data (type-safe access)
print(request.system)   # "You are helpful"
print(request.prompt)   # "Hello world"
print(request.streaming)  # False
```

### Kile Kinachotokea Nyuma ya Kulabu

**Kwa mfumo wa nyuma (backend) wa Pulsar:**
`create_producer()` → huunda mtayarishaji (producer) wa Pulsar ukitumia schema ya JSON au rekodi iliyoundwa moja kwa moja.
`send(request)` → huhifadhi (hufanya serialization) darasa la data (dataclass) kuwa muundo wa JSON/Pulsar, na hutuma kwa Pulsar.
`receive()` → hupokea ujumbe wa Pulsar, na huhifadhi tena (hufanya deserialization) kurudi kuwa darasa la data.

**Kwa mfumo wa nyuma (backend) wa MQTT:**
`create_producer()` → huunganisha na programu (broker) ya MQTT, hakuna haja ya usajili wa schema.
`send(request)` → hubadilisha darasa la data kuwa JSON, na hutuma kwenye mada (topic) ya MQTT.
`receive()` → huhudhuria mada (topic) ya MQTT, na huhifadhi tena JSON kurudi kuwa darasa la data.

**Kwa mfumo wa nyuma (backend) wa Kafka:**
`create_producer()` → huunda mtayarishaji (producer) wa Kafka, na husajili schema ya Avro ikiwa inahitajika.
`send(request)` → huhifadhi darasa la data kuwa muundo wa Avro, na hutuma kwa Kafka.
`receive()` → hupokea ujumbe wa Kafka, na huhifadhi tena Avro kurudi kuwa darasa la data.

### Vipengele Muhimu vya Ubunifu

1. **Uundaji wa kitu (object) cha schema:** Kitu (object) cha darasa la data (dataclass) (`TextCompletionRequest(...)`) ni sawa bila kujali mfumo wa nyuma (backend).
2. **Mfumo wa nyuma (backend) hutunza uhifadhi:** Kila mfumo wa nyuma (backend) unajua jinsi ya kuhifadhi darasa lake la data kuwa muundo unaotumwa.
3. **Ufafanuzi wa schema wakati wa uundaji:** Unapounda mtayarishaji (producer)/mpokeaji (consumer), unataja aina ya schema.
4. **Usalama wa aina (type) unahifadhiwa:** Unapata kitu (object) sahihi cha `TextCompletionRequest`, sio kamusi (dict).
5. **Hakuna uvujaji wa mfumo wa nyuma (backend):** Msimbo wa programu kamwe hauingize maktaba maalum za mfumo wa nyuma (backend).

### Mfano wa Ubadilishaji

**Hali ya sasa (maalum kwa Pulsar):**
```python
# schema/services/llm.py
from pulsar.schema import Record, String, Boolean, Integer

class TextCompletionRequest(Record):
    system = String()
    prompt = String()
    streaming = Boolean()
```

**Mpya (Sio tegemezi ya mfumo wa nyuma):**
```python
# schema/services/llm.py
from dataclasses import dataclass

@dataclass
class TextCompletionRequest:
    system: str
    prompt: str
    streaming: bool = False
```

### Uunganisho wa Seva ya Nyuma (Backend)

Kila seva ya nyuma hushughulikia us serialization/deserialization wa madatakesi:

**Seva ya nyuma ya Pulsar:**
Huunda madatakesi `pulsar.schema.Record` moja kwa moja kutoka kwa madatakesi.
Au huserialize madatakesi hadi JSON na kutumia mfumo wa JSON wa Pulsar.
Inaendelea kudumisha utangamano na matumizi ya sasa ya Pulsar.

**Seva ya nyuma ya MQTT/Redis:**
Huserialize madatakesi ya aina ya JSON moja kwa moja.
Tumia `dataclasses.asdict()` / `from_dict()`.
Nyepesi, haihitaji usajili wa mfumo.

**Seva ya nyuma ya Kafka:**
Huunda mifumo ya Avro kutoka kwa maelezo ya madatakesi.
Tumia usajili wa mfumo wa Confluent.
Us serialization wa salama wa aina na udhamini wa mabadiliko ya mfumo.

### Muundo

```
┌─────────────────────────────────────┐
│   Application Code                  │
│   - Uses dataclass schemas          │
│   - Backend-agnostic                │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│   PubSubFactory (configurable)      │
│   - get_pubsub() returns backend    │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        │             │
┌───────▼─────────┐  ┌────▼──────────────┐
│ PulsarBackend   │  │ MQTTBackend       │
│ - JSON schema   │  │ - JSON serialize  │
│ - or dynamic    │  │ - Simple queues   │
│   Record gen    │  │                   │
└─────────────────┘  └───────────────────┘
```

### Maelezo ya Utendaji

**1. Ufafanuzi wa muundo:** Darasa za data za kawaida na maelezo ya aina
   `str`, `int`, `bool`, `float` kwa vipengele vya msingi
   `list[T]` kwa safu
   `dict[str, T]` kwa ramani
   Darasa za data zilizounganishwa kwa aina ngumu

**2. Kila mfumo hutoa:**
   Mfumo wa ubadilishaji: `dataclass → bytes/wire format`
   Mfumo wa kurejesha: `bytes/wire format → dataclass`
   Usajili wa muundo (ikiwa inahitajika, kama Pulsar/Kafka)

**3. Dhana ya mtumiaji/mtayarishaji:**
   Tayari ipo (consumer.py, producer.py)
   Sasisha ili kutumia ubadilishaji wa mfumo
   Ondoa uingizaji wa moja kwa moja wa Pulsar

**4. Ulinganisho wa aina:**
   Pulsar `String()` → Python `str`
   Pulsar `Integer()` → Python `int`
   Pulsar `Boolean()` → Python `bool`
   Pulsar `Array(T)` → Python `list[T]`
   Pulsar `Map(K, V)` → Python `dict[K, V]`
   Pulsar `Double()` → Python `float`
   Pulsar `Bytes()` → Python `bytes`

### Njia ya Uhamishaji

1. **Tengeneza matoleo ya darasa za data** ya muundo wote katika `trustgraph/schema/`
2. **Sasisha madarasa ya mfumo** (Mtumiaji, Mtayarishaji, Mchapishaji, Mwasili) ili kutumia ubadilishaji unaotolewa na mfumo
3. **Teleza PulsarBackend** na muundo wa JSON au uzalishaji wa Rekodi wa moja kwa moja
4. **Jaribu na Pulsar** ili kuhakikisha utangamano wa nyuma na matumizi yaliyopo
5. **Ongeza mifumo mipya** (MQTT, Kafka, Redis, n.k.) kama inahitajika
6. **Ondoa uingizaji wa Pulsar** kutoka kwa faili za muundo

### Faida

✅ **Hakuna utegemezi wa pub/sub** katika ufafanuzi wa muundo
✅ **Python ya kawaida** - rahisi kuelewa, kuangalia aina, na kutoa maelezo
✅ **Zana za kisasa** - inafanya kazi na mypy, kukamilisha kiotomatiki kwa IDE, na vichujio
✅ **Imeboreshwa kwa mfumo** - kila mfumo hutumia ubadilishaji wa asili
✅ **Hakuna gharama ya tafsiri** - ubadilishaji wa moja kwa moja, hakuna adapta
✅ **Usalama wa aina** - vitu halisi na aina sahihi
✅ **Uthibitisho rahisi** - inaweza kutumia Pydantic ikiwa inahitajika

### Changamoto na Suluhisho

**Changamoto:** `Record` ya Pulsar ina uthibitisho wa uwanja wakati wa utekelezaji
**Suluhisho:** Tumia darasa za data za Pydantic kwa uthibitisho ikiwa inahitajika, au vipengele vya darasa za data ya Python 3.10+ na `__post_init__`

**Changamoto:** Vipengele vingine maalum vya Pulsar (kama aina ya `Bytes`)
**Suluhisho:** Linganisha na aina ya `bytes` katika darasa ya data, mfumo hutunza uandikaji ipasavyo

**Changamoto:** Majina ya mada (`persistent://tenant/namespace/topic`)
**Suluhisho:** Dhani majina ya mada katika ufafanuzi wa muundo, mfumo hubadilisha kuwa muundo sahihi

**Changamoto:** Maendeleo na toleo la muundo
**Suluhisho:** Kila mfumo hushughulikia hii kulingana na uwezo wake (matoleo ya muundo ya Pulsar, rejista ya muundo ya Kafka, n.k.)

**Changamoto:** Aina ngumu zilizounganishwa
**Suluhisho:** Tumia darasa za data zilizounganishwa, mifumo inabadilisha/kurejesha kwa uangalifu

### Maamuzi ya Ubunifu

1. **Darasa za data za kawaida au Pydantic?**
   ✅ **Maamuzi: Tumia darasa za data za Python za kawaida**
   Rahisi, hakuna utegemezi wa ziada
   Uthibitisho hauhitajiki kwa mazoea
   Rahisi kuelewa na kudumisha

2. **Maendeleo ya muundo:**
   ✅ **Maamuzi: Hakuna utaratibu wa toleo unaohitajika**
   Miondoko ni thabiti na ya muda mrefu
   Marekebisho kawaida huongeza sehemu mpya (utangamano wa nyuma)
   Mifumo inashughulikia maendeleo ya muundo kulingana na uwezo wake

3. **Ulingano wa nyuma:**
   ✅ **Maamuzi: Mabadiliko makubwa ya toleo, utangamano wa nyuma hauhitajiki**
   Itakuwa mabadiliko ya kuvunja na maagizo ya uhamishaji
   Kutoa mtego huruhusu muundo bora
   Mwongozo wa uhamishaji utatolewa kwa matumizi yaliyopo

4. **Aina zilizounganishwa na miundo ngumu:**
   ✅ **Maamuzi: Tumia darasa za data zilizounganishwa kwa asili**
   Darasa za data za Python zinashughulikia uunganishaji kikamilifu
   `list[T]` kwa safu, `dict[K, V]` kwa ramani
   Mifumo inabadilisha/kurejesha kwa uangalifu
   Mfano:
     ```python
     @dataclass
     class Value:
         value: str
         is_uri: bool

     @dataclass
     class Triple:
         s: Value              # Nested dataclass
         p: Value
         o: Value

     @dataclass
     class GraphQuery:
         triples: list[Triple]  # Array of nested dataclasses
         metadata: dict[str, str]
     ```

5. **Maelezo ya msingi na sehemu za hiari:**
   ✅ **Uamuzi: Mchanganyiko wa sehemu za lazima, maelezo ya msingi, na sehemu za hiari**
   Sehemu za lazima: Hakuna maelezo ya msingi
   Sehemu zilizo na maelezo ya msingi: Zipo kila wakati, zina maelezo ya msingi yanayofaa
   Sehemu za hiari kabisa: `T | None = None`, huachwa kutoka kwenye serialization wakati `None`
   Mfano:
     ```python
     @dataclass
     class TextCompletionRequest:
         system: str              # Required, no default
         prompt: str              # Required, no default
         streaming: bool = False  # Optional with default value
         metadata: dict | None = None  # Truly optional, can be absent
     ```

   **Maana muhimu ya usanifu:**

   Wakati `metadata = None`:
   ```json
   {
       "system": "...",
       "prompt": "...",
       "streaming": false
       // metadata field NOT PRESENT
   }
   ```

   Wakati `metadata = {}` (tupu wazi):
   ```json
   {
       "system": "...",
       "prompt": "...",
       "streaming": false,
       "metadata": {}  // Field PRESENT but empty
   }
   ```

   **Tofauti kuu:**
   `None` → sehemu ambayo haina katika JSON (hairekebishwi)
   Thamani tupu (`{}`, `[]`, `""`) → sehemu inayoonekana na thamani tupu
   Hii ina umuhimu wa maana: "haiyapatikani" dhidi ya "tupu kwa uwazi"
   Mifumo ya kurekebisha data lazima zisipite sehemu za `None`, badala ya kuzirekebisha kama `null`

## Mfumo wa Awali wa 3: Maelezo ya Utendaji

### Muundo wa Jina la Kawaida la Kundi

Badilisha majina ya kundi maalum ya kila mfumo na muundo wa kawaida ambao mifumo inaweza kulinganisha ipasavyo.

**Muundo:** `{qos}/{tenant}/{namespace}/{queue-name}`

Ambako:
`qos`: Ngazi ya Huduma ya Ubora
  `q0` = juhudi za kawaida (tuma na usisahau, hakuna utambuzi)
  `q1` = angalau mara moja (inahitaji utambuzi)
  `q2` = hasiwa mara moja (utambuzi wa awamu mbili)
`tenant`: Kikundi cha mantiki kwa ushirikaji wa wateja wengi
`namespace`: Kikundi kidogo ndani ya mteja
`queue-name`: Jina halisi la kundi/mada

**Mfano:**
```
q1/tg/flow/text-completion-requests
q2/tg/config/config-push
q0/tg/metrics/stats
```

### Ramani ya Mada za Seva ya Nyuma (Backend)

Kila seva ya nyuma (backend) inaunganisha muundo wa jumla na muundo wake wa asili:

**Seva ya Nyuma ya Pulsar:**
```python
def map_topic(self, generic_topic: str) -> str:
    # Parse: q1/tg/flow/text-completion-requests
    qos, tenant, namespace, queue = generic_topic.split('/', 3)

    # Map QoS to persistence
    persistence = 'persistent' if qos in ['q1', 'q2'] else 'non-persistent'

    # Return Pulsar URI: persistent://tg/flow/text-completion-requests
    return f"{persistence}://{tenant}/{namespace}/{queue}"
```

**Umfumo wa Nyuma wa MQTT:**
```python
def map_topic(self, generic_topic: str) -> tuple[str, int]:
    # Parse: q1/tg/flow/text-completion-requests
    qos, tenant, namespace, queue = generic_topic.split('/', 3)

    # Map QoS level
    qos_level = {'q0': 0, 'q1': 1, 'q2': 2}[qos]

    # Build MQTT topic including tenant/namespace for proper namespacing
    mqtt_topic = f"{tenant}/{namespace}/{queue}"

    return mqtt_topic, qos_level
```

### Kazi ya Msaidizi ya Mada Iliyosasishwa

```python
# schema/core/topic.py
def topic(queue_name, qos='q1', tenant='tg', namespace='flow'):
    """
    Create a generic topic identifier that can be mapped by backends.

    Args:
        queue_name: The queue/topic name
        qos: Quality of service
             - 'q0' = best-effort (no ack)
             - 'q1' = at-least-once (ack required)
             - 'q2' = exactly-once (two-phase ack)
        tenant: Tenant identifier for multi-tenancy
        namespace: Namespace within tenant

    Returns:
        Generic topic string: qos/tenant/namespace/queue_name

    Examples:
        topic('my-queue')  # q1/tg/flow/my-queue
        topic('config', qos='q2', namespace='config')  # q2/tg/config/config
    """
    return f"{qos}/{tenant}/{namespace}/{queue_name}"
```

### Usanidi na Uanzishaji

**Vigezo vya Amri na Vigezo vya Mazingira:**

```python
# In base/async_processor.py - add_args() method
@staticmethod
def add_args(parser):
    # Pub/sub backend selection
    parser.add_argument(
        '--pubsub-backend',
        default=os.getenv('PUBSUB_BACKEND', 'pulsar'),
        choices=['pulsar', 'mqtt'],
        help='Pub/sub backend (default: pulsar, env: PUBSUB_BACKEND)'
    )

    # Pulsar-specific configuration
    parser.add_argument(
        '--pulsar-host',
        default=os.getenv('PULSAR_HOST', 'pulsar://localhost:6650'),
        help='Pulsar host (default: pulsar://localhost:6650, env: PULSAR_HOST)'
    )

    parser.add_argument(
        '--pulsar-api-key',
        default=os.getenv('PULSAR_API_KEY', None),
        help='Pulsar API key (env: PULSAR_API_KEY)'
    )

    parser.add_argument(
        '--pulsar-listener',
        default=os.getenv('PULSAR_LISTENER', None),
        help='Pulsar listener name (env: PULSAR_LISTENER)'
    )

    # MQTT-specific configuration
    parser.add_argument(
        '--mqtt-host',
        default=os.getenv('MQTT_HOST', 'localhost'),
        help='MQTT broker host (default: localhost, env: MQTT_HOST)'
    )

    parser.add_argument(
        '--mqtt-port',
        type=int,
        default=int(os.getenv('MQTT_PORT', '1883')),
        help='MQTT broker port (default: 1883, env: MQTT_PORT)'
    )

    parser.add_argument(
        '--mqtt-username',
        default=os.getenv('MQTT_USERNAME', None),
        help='MQTT username (env: MQTT_USERNAME)'
    )

    parser.add_argument(
        '--mqtt-password',
        default=os.getenv('MQTT_PASSWORD', None),
        help='MQTT password (env: MQTT_PASSWORD)'
    )
```

**Fungua Kazi:**

```python
# In base/pubsub.py or base/pubsub_factory.py
def get_pubsub(**config) -> PubSubBackend:
    """
    Create and return a pub/sub backend based on configuration.

    Args:
        config: Configuration dict from command-line args
                Must include 'pubsub_backend' key

    Returns:
        Backend instance (PulsarBackend, MQTTBackend, etc.)
    """
    backend_type = config.get('pubsub_backend', 'pulsar')

    if backend_type == 'pulsar':
        return PulsarBackend(
            host=config.get('pulsar_host'),
            api_key=config.get('pulsar_api_key'),
            listener=config.get('pulsar_listener'),
        )
    elif backend_type == 'mqtt':
        return MQTTBackend(
            host=config.get('mqtt_host'),
            port=config.get('mqtt_port'),
            username=config.get('mqtt_username'),
            password=config.get('mqtt_password'),
        )
    else:
        raise ValueError(f"Unknown pub/sub backend: {backend_type}")
```

**Matumizi katika AsyncProcessor:**

```python
# In async_processor.py
class AsyncProcessor:
    def __init__(self, **params):
        self.id = params.get("id")

        # Create backend from config (replaces PulsarClient)
        self.pubsub = get_pubsub(**params)

        # Rest of initialization...
```

### Kiolesura cha Nyuma

```python
class PubSubBackend(Protocol):
    """Protocol defining the interface all pub/sub backends must implement."""

    def create_producer(self, topic: str, schema: type, **options) -> BackendProducer:
        """
        Create a producer for a topic.

        Args:
            topic: Generic topic format (qos/tenant/namespace/queue)
            schema: Dataclass type for messages
            options: Backend-specific options (e.g., chunking_enabled)

        Returns:
            Backend-specific producer instance
        """
        ...

    def create_consumer(
        self,
        topic: str,
        subscription: str,
        schema: type,
        initial_position: str = 'latest',
        consumer_type: str = 'shared',
        **options
    ) -> BackendConsumer:
        """
        Create a consumer for a topic.

        Args:
            topic: Generic topic format (qos/tenant/namespace/queue)
            subscription: Subscription/consumer group name
            schema: Dataclass type for messages
            initial_position: 'earliest' or 'latest' (MQTT may ignore)
            consumer_type: 'shared', 'exclusive', 'failover' (MQTT may ignore)
            options: Backend-specific options

        Returns:
            Backend-specific consumer instance
        """
        ...

    def close(self) -> None:
        """Close the backend connection."""
        ...
```

```python
class BackendProducer(Protocol):
    """Protocol for backend-specific producer."""

    def send(self, message: Any, properties: dict = {}) -> None:
        """Send a message (dataclass instance) with optional properties."""
        ...

    def flush(self) -> None:
        """Flush any buffered messages."""
        ...

    def close(self) -> None:
        """Close the producer."""
        ...
```

```python
class BackendConsumer(Protocol):
    """Protocol for backend-specific consumer."""

    def receive(self, timeout_millis: int = 2000) -> Message:
        """
        Receive a message from the topic.

        Raises:
            TimeoutError: If no message received within timeout
        """
        ...

    def acknowledge(self, message: Message) -> None:
        """Acknowledge successful processing of a message."""
        ...

    def negative_acknowledge(self, message: Message) -> None:
        """Negative acknowledge - triggers redelivery."""
        ...

    def unsubscribe(self) -> None:
        """Unsubscribe from the topic."""
        ...

    def close(self) -> None:
        """Close the consumer."""
        ...
```

```python
class Message(Protocol):
    """Protocol for a received message."""

    def value(self) -> Any:
        """Get the deserialized message (dataclass instance)."""
        ...

    def properties(self) -> dict:
        """Get message properties/metadata."""
        ...
```

### Urekebishaji wa Darasa Zilizopo

Madarasa yaliyopo ya `Consumer`, `Producer`, `Publisher`, `Subscriber` yanabaki kwa kiasi kikubwa bila kubadilishwa:

**Jukumu la sasa (hakikisha):**
Mfumo wa uzi usio na usumbufu na vikundi vya kazi
Mantiki ya kuunganisha tena na udhibiti wa kujaribu tena
Ukusanyaji wa metriki
Udhibiti wa kiwango
Usimamizi wa ushindani

**Mabadiliko yanayohitajika:**
Ondoa uingizaji wa moja kwa moja wa Pulsar (`pulsar.schema`, `pulsar.InitialPosition`, n.k.)
Kubali `BackendProducer`/`BackendConsumer` badala ya mteja wa Pulsar
Agiza shughuli halisi za kutuma/kupokea kwa mifumo ya nyuma
Linganisha dhana za jumla na simu za mfumo wa nyuma

**Mfano wa urekebishaji:**

```python
# OLD - consumer.py
class Consumer:
    def __init__(self, client, topic, subscriber, schema, ...):
        self.client = client  # Direct Pulsar client
        # ...

    async def consumer_run(self):
        # Uses pulsar.InitialPosition, pulsar.ConsumerType
        self.consumer = self.client.subscribe(
            topic=self.topic,
            schema=JsonSchema(self.schema),
            initial_position=pulsar.InitialPosition.Earliest,
            consumer_type=pulsar.ConsumerType.Shared,
        )

# NEW - consumer.py
class Consumer:
    def __init__(self, backend_consumer, schema, ...):
        self.backend_consumer = backend_consumer  # Backend-specific consumer
        self.schema = schema
        # ...

    async def consumer_run(self):
        # Backend consumer already created with right settings
        # Just use it directly
        while self.running:
            msg = await asyncio.to_thread(
                self.backend_consumer.receive,
                timeout_millis=2000
            )
            await self.handle_message(msg)
```

### Tabia Maalum za Seva (Backend)

**Seva ya Pulsar:**
Inahusisha `q0` → `non-persistent://`, `q1`/`q2` → `persistent://`
Inasaidia aina zote za watumiaji (walioshirikiana, wa kipekee, wa chechezi)
Inasaidia nafasi ya awali (ya kwanza/ya mwisho)
Utambuzi wa asili wa ujumbe
Inasaidia usajili wa schema

**Seva ya MQTT:**
Inahusisha `q0`/`q1`/`q2` → Viwango vya QoS vya MQTT 0/1/2
Inajumuisha mpangilio/nafasi katika njia ya mada kwa ajili ya utenganishaji
Inazalisha kiotomatiki vitambulisho vya wateja kutoka kwa majina ya usajili
Inapuuza nafasi ya awali (hakuna historia ya ujumbe katika MQTT ya msingi)
Inapuuza aina ya mtumiaji (MQTT hutumia vitambulisho vya wateja, sio vikundi vya watumiaji)
Mfumo rahisi wa kuchapisha/kusajili

### Muhtasari wa Maamuzi ya Ubunifu

1. ✅ **Jina la kawaida la folyo:** Muundo wa `qos/tenant/namespace/queue-name`
2. ✅ **QoS katika kitambulisho cha folyo:** Huamuliwa na ufafanuzi wa folyo, sio usanidi
3. ✅ **Uunganishaji upya:** Unashughulikiwa na madarasa ya Mtumiaji/Mzalishaji, sio seva
4. ✅ **Mada za MQTT:** Zijumuishie mpangilio/nafasi kwa ajili ya utenganishaji sahihi
5. ✅ **Historia ya ujumbe:** MQTT inapuuza parameter ya `initial_position` (ongezeko la baadaye)
6. ✅ **Vitambulisho vya wateja:** Seva ya MQTT inazalisha kiotomatiki kutoka kwa jina la usajili

### Ongezeko za Baadaye

**Historia ya ujumbe wa MQTT:**
Inaweza kuongeza safu ya hiari ya kudumu (k.m., ujumbe uliokaguliwa, duka la nje)
Itaruhusu kuunga mkono `initial_position='earliest'`
Haihitajiki kwa utekelezaji wa awali

