# Maelezo ya Kiufundi: Uboreshaji wa Utendaji wa Hifadhidata ya Maarifa ya Cassandra

**Hali:** Rasimu
**Mwandishi:** Msaidizi
**Tarehe:** 2025-09-18

## Muhtasari

Maelezo haya yanashughulikia masuala ya utendaji katika utekelezaji wa hifadhidata ya maarifa ya TrustGraph ya Cassandra na yanapendekeza uboreshaji kwa uhifadhi na utafutaji wa data ya RDF.

## Utendaji wa Sasa

### Muundo wa Skimu

Utendaji wa sasa hutumia muundo wa jedwali moja katika `trustgraph-flow/trustgraph/direct/cassandra_kg.py`:

```sql
CREATE TABLE triples (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY (collection, s, p, o)
);
```

**Faharasa Pili:**
`triples_s` KWA `s` (somo)
`triples_p` KWA `p` (kitenzi)
`triples_o` KWA `o` (kielele)

### Mifumo ya Umasiliano

Utaratibu wa sasa unaoendeshwa unao na mifumo 8 tofauti ya masiliano:

1. **get_all(mkusanyiko, kikomo=50)** - Pata vitriple vyote kwa mkusanyiko
   ```sql
   SELECT s, p, o FROM triples WHERE collection = ? LIMIT 50
   ```

2. **get_s(collection, s, limit=10)** - Utafiti kwa mada.
   ```sql
   SELECT p, o FROM triples WHERE collection = ? AND s = ? LIMIT 10
   ```

3. **get_p(collection, p, limit=10)** - Utafiti kwa kutumia vigezo.
   ```sql
   SELECT s, o FROM triples WHERE collection = ? AND p = ? LIMIT 10
   ```

4. **get_o(collection, o, limit=10)** - Utafiti kwa kutumia kitu.
   ```sql
   SELECT s, p FROM triples WHERE collection = ? AND o = ? LIMIT 10
   ```

5. **get_sp(collection, s, p, limit=10)** - Utafiti kwa mada + predikati
   ```sql
   SELECT o FROM triples WHERE collection = ? AND s = ? AND p = ? LIMIT 10
   ```

6. **get_po(collection, p, o, limit=10)** - Utafiti kwa kutumia vigezo na kitu ⚠️
   ```sql
   SELECT s FROM triples WHERE collection = ? AND p = ? AND o = ? LIMIT 10 ALLOW FILTERING
   ```

7. **get_os(collection, o, s, limit=10)** - Utafiti kwa kutumia kitu pamoja na mada ⚠️
   ```sql
   SELECT p FROM triples WHERE collection = ? AND o = ? AND s = ? LIMIT 10 ALLOW FILTERING
   ```

8. **get_spo(collection, s, p, o, limit=10)** - Mechi kamili ya triple.
   ```sql
   SELECT s as x FROM triples WHERE collection = ? AND s = ? AND p = ? AND o = ? LIMIT 10
   ```

### Muundo wa Sasa

**Faili: `trustgraph-flow/trustgraph/direct/cassandra_kg.py`**
Darasa moja la `KnowledgeGraph` linaloshughulikia shughuli zote
Uunganisho wa kikundi kupitia orodha ya kimataifa ya `_active_clusters`
Jina la jedwali lililobainishwa: `"triples"`
Spishi kwa kila mfumo wa mtumiaji
Nakala ya SimpleStrategy kwa sababu 1

**Maeneo ya Uunganisho:**
**Njia ya Kuandika:** `trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
**Njia ya Umasilisho:** `trustgraph-flow/trustgraph/query/triples/cassandra/service.py`
**Hifadhi ya Maarifa:** `trustgraph-flow/trustgraph/tables/knowledge.py`

## Matatizo ya Utendaji Yanayobainika

### Matatizo ya Ngazi ya Muundo

1. **Muundo Usiofaa wa Ufunguo Mkuu**
   Sasa: `PRIMARY KEY (collection, s, p, o)`
   Hupelekea uwekaji duni wa data kwa mifumo ya kawaida ya ufikiaji
   Inahitaji matumizi ya gharama kubwa ya fahirisi za sekondari

2. **Matumizi Mengi ya Fahirisi za Sekondari** ⚠️
   Fahirisi tatu za sekondari kwenye safu zenye maadili mengi (s, p, o)
   Fahirisi za sekondari katika Cassandra ni ghali na hazipunguzi kasi vizuri
   Maswali 6 na 7 yanahitaji `ALLOW FILTERING`, ambayo inaonyesha muundo duni wa data

3. **Hatari ya Sehemu Zenye Trafiki Kubwa**
   Ufunguo mmoja wa sehemu `collection` unaweza kuunda sehemu zenye trafiki kubwa
   Mkusanyiko mkubwa utajikuta katika nodi moja
   Hakuna mkakati wa usambazaji wa mizigo

### Matatizo ya Ngazi ya Umasilisho

1. **Matumizi ya ALLOW FILTERING** ⚠️
   Aina mbili za maswali (get_po, get_os) zinahitaji `ALLOW FILTERING`
   Maswali haya husifia sehemu nyingi na ni ghali sana
   Utendaji unapungua kwa kasi kadri ya ukubwa wa data

2. **Mifumo ya Ufikiaji Yasiyo na Ufanisi**
   Hakuna uboreshaji kwa mifumo ya kawaida ya maswali ya RDF
   Hakuna fahirisi za pamoja kwa mchanganyiko wa maswali unaoonekana mara kwa mara
   Hakuna utambuzi wa mifumo ya utaftaji wa grafu

3. **Ukosefu wa Uboreshaji wa Umasilisho**
   Hakuna kuhifadhi kwa masimulizi yaliyotayarishwa
   Hakuna vidokezo au mikakati ya uboreshaji wa maswali
   Hakuna utambuzi wa upangishaji zaidi ya LIMIT rahisi

## Taarifa ya Tatizo

Utekelezaji wa sasa wa hifadhi ya maarifa ya Cassandra una matatizo mawili muhimu ya utendaji:

### 1. Utendaji Usio na Ufanisi wa Maswali ya get_po

Swali la `get_po(collection, p, o)` halipunguzi kasi kwa sababu linahitaji `ALLOW FILTERING`:

```sql
SELECT s FROM triples WHERE collection = ? AND p = ? AND o = ? LIMIT 10 ALLOW FILTERING
```

**Sababu ya kuwa hii ni tatizo:**
`ALLOW FILTERING` inalazimisha Cassandra kuchanganua kila sehemu ndani ya mkusanyiko.
Utendaji hupungua kwa mstari sawa na ukubwa wa data.
Hii ni muundo wa kawaida wa swali la RDF (kutafuta vitu ambavyo vina uhusiano maalum wa tabia-jambo).
Huunda mzigo mkubwa kwenye kundi kadri data inavyoongezeka.

### 2. Mkakati Usiofaa wa Uwekaji Pamoja

Ufunguo mkuu wa sasa `PRIMARY KEY (collection, s, p, o)` hutoa faida ndogo katika uwekaji pamoja:

**Matatizo na uwekaji pamoja wa sasa:**
`collection` kama funguo ya sehemu haisambati data kwa ufanisi.
Makusanyiko mengi yana data tofauti, na kuifanya uwekaji pamoja kuwa usiofaa.
Hakuna utambuzi kwa mifumo ya kawaida ya ufikiaji katika maswali ya RDF.
Makusanyiko makubwa huunda sehemu zenye mzigo mwingi kwenye nodi moja.
Safu za uwekaji pamoja (s, p, o) haziboreshi kwa mifumo ya kawaida ya utaftaji wa grafu.

**Athari:**
Maswali hayanapata faida kutoka kwa ukaribu wa data.
Matumizi duni ya kumbukumbu (cache).
Usambazaji usio sawa wa mzigo katika nodi za kundi.
Zuio la uwezo wa kupanuka (scalability) kadri makusanyiko yanavyoongezeka.

## Suluhisho Lililopendekezwa: Mkakati wa Utofauti wa Jedwali 4

### Muhtasari

Badilisha jedwali moja `triples` na jedwali nne zilizoundwa kwa madhumuni maalum, kila moja iliyoboreshwa kwa mifumo maalum ya swali. Hii inafutilia hitaji la fahirisi za sekondari na ALLOW FILTERING huku ikiwapa utendaji bora kwa aina zote za swali. Jedwali la nne linaruhusu uondoaji wa makusanyiko kwa ufanisi licha ya funguo za sehemu zilizounganishwa.

### Muundo Mpya wa Skimu

**Jedwali la 1: Maswali Yanayozingatia Sijali (triples_s)**
```sql
CREATE TABLE triples_s (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY ((collection, s), p, o)
);
```
**Inaboresha:** get_s, get_sp, get_os
**Ufunguo wa Sehemu:** (mkusanyiko, s) - Usambazaji bora kuliko mkusanyiko pekee
**Kukusanya:** (p, o) - Huwezesha utafutaji wa ufanisi wa vigezo/vitendo kwa ajili ya somo

**Jedwali 2: Maswali ya Vigezo-Vitendo (triples_p)**
```sql
CREATE TABLE triples_p (
    collection text,
    p text,
    o text,
    s text,
    PRIMARY KEY ((collection, p), o, s)
);
```
**Inaboresha:** get_p, get_po (inabadilisha ALLOW FILTERING!)
**Ufunguo wa Sehemu:** (mkusanyiko, p) - Ufikiaji wa moja kwa moja kupitia kigezo.
**Kukusanyika:** (o, s) - Ufuatiliaji wa vitu na masomo unaofaa.

**Jedwali la 3: Maswali Yanayozingatia Vitu (triples_o)**
```sql
CREATE TABLE triples_o (
    collection text,
    o text,
    s text,
    p text,
    PRIMARY KEY ((collection, o), s, p)
);
```
**Inaboresha:** get_o
**Ufunguo wa Sehemu:** (mkusanyiko, o) - Ufikiaji wa moja kwa moja kwa kutumia kitu
**Kukusanya:** (s, p) - Ufuatiliaji wa ufanisi wa somo-tabia

**Jedwali la 4: Usimamizi wa Mkusaniko na Maswali ya SPO (triples_collection)**
```sql
CREATE TABLE triples_collection (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY (collection, s, p, o)
);
```
**Inaboresha:** get_spo, delete_collection
**Ufunguo wa Sehemu (Partition Key):** mkusanyiko pekee - Huwezesha operesheni bora za kiwango cha mkusanyiko.
**Kukusanyika (Clustering):** (s, p, o) - Mpangilio wa kawaida wa triple.
**Madhumuni:** Matumizi mawili, kwa utafutaji sahihi wa SPO na kama faharasa ya kufuta.

### Ramani ya Utafutaji (Query Mapping)

| Utafutaji Asili | Jedwali Linalolengwa | Ubora wa Kuboresha |
|----------------|-------------|------------------------|
| get_all(collection) | triples_s | RUHASA YA KUCHANUA (inayokubalika kwa skani) |
| get_s(collection, s) | triples_s | Ufikiaji wa moja kwa moja wa sehemu. |
| get_p(collection, p) | triples_p | Ufikiaji wa moja kwa moja wa sehemu. |
| get_o(collection, o) | triples_o | Ufikiaji wa moja kwa moja wa sehemu. |
| get_sp(collection, s, p) | triples_s | Sehemu + kukusanyika. |
| get_po(collection, p, o) | triples_p | **HAKUNA tena RUHASA LA KUCHANUA!** |
| get_os(collection, o, s) | triples_o | Sehemu + kukusanyika. |
| get_spo(collection, s, p, o) | triples_collection | Utafutaji wa ufunguo wa moja kwa moja. |
| delete_collection(collection) | triples_collection | Soma faharasa, futa kwa wingi. |

### Mkakati wa Kufuta Mkusaniko

Pamoja na ufunguo wa sehemu mchanganyiko, hatuwezi tu kutekeleza `DELETE FROM table WHERE collection = ?`. Badala yake:

1. **Awamu ya Kusoma:** Tafuta `triples_collection` ili kuorodhesha triple zote:
   ```sql
   SELECT s, p, o FROM triples_collection WHERE collection = ?
   ```
   Hii ni bora kwa sababu `collection` ndiyo ufunguo wa kundi kwa jedwali hili.

2. **Awamu ya Ufutilishaji:** Kwa kila seti tatu (s, p, o), futa kutoka kwenye meza zote 4 kwa kutumia ufunguo kamili wa kundi:
   ```sql
   DELETE FROM triples_s WHERE collection = ? AND s = ? AND p = ? AND o = ?
   DELETE FROM triples_p WHERE collection = ? AND p = ? AND o = ? AND s = ?
   DELETE FROM triples_o WHERE collection = ? AND o = ? AND s = ? AND p = ?
   DELETE FROM triples_collection WHERE collection = ? AND s = ? AND p = ? AND o = ?
   ```
   Imefunganishwa katika makundi ya 100 ili kuongeza ufanisi.

**Uchambuzi wa Usawa:**
✅ Inaendelea kudumisha utendaji bora wa maswali kwa kutumia vipande vilivyogawanywa.
✅ Hakuna vipande ambavyo hupita kasi kwa makusanyo makubwa.
❌ Mantiki ya kufuta ni ngumu zaidi (soma kisha futa).
❌ Muda wa kufuta unalingana na ukubwa wa mkusanyiko.

### Faida

1. **Inaondoa ALLOW FILTERING** - Kila swali lina njia bora ya kufikia (isipokuwa skani ya get_all).
2. **Hakuna Faharasa za Pili** - Kila jedwali NI faharasa kwa mtindo wake wa swali.
3. **Usambazaji Bora wa Data** - Funguo za pamoja za kugawanya zinapanua mzigo kwa ufanisi.
4. **Utendaji Unaoweza Kushawishiwa** - Muda wa swali unalingana na ukubwa wa matokeo, sio data jumla.
5. **Inatumia Nguvu za Cassandra** - Imeundwa kwa usanifu wa Cassandra.
6. **Inaruhusu Ufuta wa Makusanyo** - triples_collection hutumika kama faharasa ya kufuta.

## Mpango wa Utendaji

### Faili Zinazohitaji Marekebisho

#### Faili Kuu ya Utendaji

**`trustgraph-flow/trustgraph/direct/cassandra_kg.py`** - Inahitajika kuandikwa upya kabisa.

**Mbinu Zinazohitajika Kubadilishwa:**
```python
# Schema initialization
def init(self) -> None  # Replace single table with three tables

# Insert operations
def insert(self, collection, s, p, o) -> None  # Write to all three tables

# Query operations (API unchanged, implementation optimized)
def get_all(self, collection, limit=50)      # Use triples_by_subject
def get_s(self, collection, s, limit=10)     # Use triples_by_subject
def get_p(self, collection, p, limit=10)     # Use triples_by_po
def get_o(self, collection, o, limit=10)     # Use triples_by_object
def get_sp(self, collection, s, p, limit=10) # Use triples_by_subject
def get_po(self, collection, p, o, limit=10) # Use triples_by_po (NO ALLOW FILTERING!)
def get_os(self, collection, o, s, limit=10) # Use triples_by_subject
def get_spo(self, collection, s, p, o, limit=10) # Use triples_by_subject

# Collection management
def delete_collection(self, collection) -> None  # Delete from all three tables
```

#### Faili za Uunganishaji (Hakuna Mabadiliko ya Mantiki Yanayohitajika)

**`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`**
Hakuna mabadiliko yanayohitajika - hutumia API ya KnowledgeGraph iliyopo
Inafaidika moja kwa moja kutoka kwa uboreshaji wa utendaji

**`trustgraph-flow/trustgraph/query/triples/cassandra/service.py`**
Hakuna mabadiliko yanayohitajika - hutumia API ya KnowledgeGraph iliyopo
Inafaidika moja kwa moja kutoka kwa uboreshaji wa utendaji

### Faili za Majaribio Zinazohitaji Mabadiliko

#### Majaribio ya Kitengo
**`tests/unit/test_storage/test_triples_cassandra_storage.py`**
Sasisha matarajio ya majaribio kwa mabadiliko ya schema
Ongeza majaribio kwa utangamano wa meza nyingi
Hakikisha hakuna ALLOW FILTERING katika mipango ya swali

**`tests/unit/test_query/test_triples_cassandra_query.py`**
Sasisha madai ya utendaji
Jaribu mifumo yote 8 ya swali dhidi ya meza mpya
Hakikisha uelekezaji wa swali hadi meza sahihi

#### Majaribio ya Uunganishaji
**`tests/integration/test_cassandra_integration.py`**
Majaribio ya mwisho na schema mpya
Ulinganisho wa benchmarking wa utendaji
Uthibitisho wa utangamano wa data katika meza

**`tests/unit/test_storage/test_cassandra_config_integration.py`**
Sasisha majaribio ya uthibitisho wa schema
Jaribu hali za uhamishaji

### Mkakati wa Utendaji

#### Awamu ya 1: Schema na Mbinu za Msingi
1. **Andika upya mbinu ya `init()`** - Unda meza nne badala ya moja
2. **Andika upya mbinu ya `insert()`** - Andika kwa wingi kwenye meza zote nne
3. **Teleza taarifa zilizotayarishwa** - Kwa utendaji bora
4. **Ongeza mantiki ya uelekezaji wa meza** - Elekeza maswali hadi meza bora
5. **Teleza uondoaji wa mkusanyiko** - Soma kutoka kwa triples_collection, ondoa kwa wingi kutoka kwenye meza zote

#### Awamu ya 2: Uboreshaji wa Mbinu ya Swali
1. **Andika upya kila mbinu ya get_*** ili itumie meza bora
2. **Ondoa matumizi yote ya ALLOW FILTERING**
3. **Teleza matumizi bora ya ufunguo wa uwekaji**
4. **Ongeza uandikaji wa utendaji wa swali**

#### Awamu ya 3: Usimamizi wa Mkusaniko
1. **Sasisha `delete_collection()`** - Ondoa kutoka kwenye meza zote tatu
2. **Ongeza uthibitisho wa utangamano** - Hakikisha meza zote zinaendelea kuwa sawa
3. **Teleza shughuli za wingi** - Kwa shughuli za meza nyingi za atomiki

### Maelezo Muhimu ya Utendaji

#### Mkakati wa Kuandika kwa Wingi
```python
def insert(self, collection, s, p, o):
    batch = BatchStatement()

    # Insert into all four tables
    batch.add(self.insert_subject_stmt, (collection, s, p, o))
    batch.add(self.insert_po_stmt, (collection, p, o, s))
    batch.add(self.insert_object_stmt, (collection, o, s, p))
    batch.add(self.insert_collection_stmt, (collection, s, p, o))

    self.session.execute(batch)
```

#### Mantiki ya Uelekezaji wa Maswali
```python
def get_po(self, collection, p, o, limit=10):
    # Route to triples_p table - NO ALLOW FILTERING!
    return self.session.execute(
        self.get_po_stmt,
        (collection, p, o, limit)
    )

def get_spo(self, collection, s, p, o, limit=10):
    # Route to triples_collection table for exact SPO lookup
    return self.session.execute(
        self.get_spo_stmt,
        (collection, s, p, o, limit)
    )
```

#### Mantiki ya Ufutilishaji wa Mkusanyiko
```python
def delete_collection(self, collection):
    # Step 1: Read all triples from collection table
    rows = self.session.execute(
        f"SELECT s, p, o FROM {self.collection_table} WHERE collection = %s",
        (collection,)
    )

    # Step 2: Batch delete from all 4 tables
    batch = BatchStatement()
    count = 0

    for row in rows:
        s, p, o = row.s, row.p, row.o

        # Delete using full partition keys for each table
        batch.add(SimpleStatement(
            f"DELETE FROM {self.subject_table} WHERE collection = ? AND s = ? AND p = ? AND o = ?"
        ), (collection, s, p, o))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.po_table} WHERE collection = ? AND p = ? AND o = ? AND s = ?"
        ), (collection, p, o, s))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.object_table} WHERE collection = ? AND o = ? AND s = ? AND p = ?"
        ), (collection, o, s, p))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.collection_table} WHERE collection = ? AND s = ? AND p = ? AND o = ?"
        ), (collection, s, p, o))

        count += 1

        # Execute every 100 triples to avoid oversized batches
        if count % 100 == 0:
            self.session.execute(batch)
            batch = BatchStatement()

    # Execute remaining deletions
    if count % 100 != 0:
        self.session.execute(batch)

    logger.info(f"Deleted {count} triples from collection {collection}")
```

#### Uboreshaji wa Matamshi Yaliyotayarishwa
```python
def prepare_statements(self):
    # Cache prepared statements for better performance
    self.insert_subject_stmt = self.session.prepare(
        f"INSERT INTO {self.subject_table} (collection, s, p, o) VALUES (?, ?, ?, ?)"
    )
    self.insert_po_stmt = self.session.prepare(
        f"INSERT INTO {self.po_table} (collection, p, o, s) VALUES (?, ?, ?, ?)"
    )
    self.insert_object_stmt = self.session.prepare(
        f"INSERT INTO {self.object_table} (collection, o, s, p) VALUES (?, ?, ?, ?)"
    )
    self.insert_collection_stmt = self.session.prepare(
        f"INSERT INTO {self.collection_table} (collection, s, p, o) VALUES (?, ?, ?, ?)"
    )
    # ... query statements
```

## Mkakati wa Uhamishaji

### Mbinu ya Uhamishaji wa Data

#### Chaguo la 1: Uwekaji wa Blue-Green (Inapendekezwa)
1. **Weka mfumo mpya pamoja na mfumo uliopo** - Tumia majina tofauti ya jedwali kwa muda
2. **Kipindi cha kuandika mara mbili** - Andika kwenye mifumo ya zamani na mipya wakati wa mabadiliko
3. **Uhamishaji wa nyuma** - Nakili data iliyopo kwenye jedwali jipya
4. **Badilisha maswali** - Elekeza maswali kwenye jedwali jipya baada ya uhamishaji wa data
5. **Futa jedwali la zamani** - Baada ya kipindi cha uhakiki

#### Chaguo la 2: Uhamishaji wa Moja kwa Moja
1. **Kuongeza mfumo** - Unda jedwali jipya kwenye eneo la funguo lililopo
2. **Skripti ya uhamishaji wa data** - Nakili kwa wingi kutoka kwenye jedwali la zamani hadi kwenye jedwali jipya
3. **Sasisho la programu** - Weka programu mpya baada ya uhamishaji kukamilika
4. **Kusafisha jedwali la zamani** - Ondoa jedwali la zamani na fahirisi

### Utangamano wa Nyuma

#### Mkakati wa Uwekaji
```python
# Environment variable to control table usage during migration
USE_LEGACY_TABLES = os.getenv('CASSANDRA_USE_LEGACY', 'false').lower() == 'true'

class KnowledgeGraph:
    def __init__(self, ...):
        if USE_LEGACY_TABLES:
            self.init_legacy_schema()
        else:
            self.init_optimized_schema()
```

#### Skripti ya Uhamishaji
```python
def migrate_data():
    # Read from old table
    old_triples = session.execute("SELECT collection, s, p, o FROM triples")

    # Batch write to new tables
    for batch in batched(old_triples, 100):
        batch_stmt = BatchStatement()
        for row in batch:
            # Add to all three new tables
            batch_stmt.add(insert_subject_stmt, row)
            batch_stmt.add(insert_po_stmt, (row.collection, row.p, row.o, row.s))
            batch_stmt.add(insert_object_stmt, (row.collection, row.o, row.s, row.p))
        session.execute(batch_stmt)
```

### Mbinu ya Uthibitisho

#### Vipimo vya Ulinganifu wa Data
```python
def validate_migration():
    # Count total records in old vs new tables
    old_count = session.execute("SELECT COUNT(*) FROM triples WHERE collection = ?", (collection,))
    new_count = session.execute("SELECT COUNT(*) FROM triples_by_subject WHERE collection = ?", (collection,))

    assert old_count == new_count, f"Record count mismatch: {old_count} vs {new_count}"

    # Spot check random samples
    sample_queries = generate_test_queries()
    for query in sample_queries:
        old_result = execute_legacy_query(query)
        new_result = execute_optimized_query(query)
        assert old_result == new_result, f"Query results differ for {query}"
```

## Mbinu ya Majaribio

### Majaribio ya Utendaji

#### Hali za Majaribio ya Kiwango
1. **Ulinganisho wa Utendaji wa Maswali**
   Vipimo vya utendaji kabla na baada kwa aina zote 8 za maswali
   Lenga uboreshaji wa utendaji wa `get_po` (ondoa `ALLOW FILTERING`)
   Pima muda wa maswali chini ya saizi tofauti za data

2. **Majaribio ya Upakiaji**
   Utendaji wa maswali kwa wakati mmoja
   Uwezo wa kuandika na shughuli za kikundi
   Matumizi ya kumbukumbu na CPU

3. **Majaribio ya Uwezo wa Kupanuka**
   Utendaji na saizi zinazoongezeka za mkusanyiko
   Usambazaji wa maswali ya mkusanyiko mwingi
   Matumizi ya nodi za kundi

#### Kijiko cha Majaribio
**Kidogo:** 10K ya vitatu kwa kila mkusanyiko
**Katikati:** 100K ya vitatu kwa kila mkusanyiko
**Kubwa:** 1M+ ya vitatu kwa kila mkusanyiko
**Mkusanyiko mwingi:** Jaribu usambazaji wa sehemu

### Majaribio ya Utendaji

#### Marekebisho ya Majaribio ya Kitengo
```python
# Example test structure for new implementation
class TestCassandraKGPerformance:
    def test_get_po_no_allow_filtering(self):
        # Verify get_po queries don't use ALLOW FILTERING
        with patch('cassandra.cluster.Session.execute') as mock_execute:
            kg.get_po('test_collection', 'predicate', 'object')
            executed_query = mock_execute.call_args[0][0]
            assert 'ALLOW FILTERING' not in executed_query

    def test_multi_table_consistency(self):
        # Verify all tables stay in sync
        kg.insert('test', 's1', 'p1', 'o1')

        # Check all tables contain the triple
        assert_triple_exists('triples_by_subject', 'test', 's1', 'p1', 'o1')
        assert_triple_exists('triples_by_po', 'test', 'p1', 'o1', 's1')
        assert_triple_exists('triples_by_object', 'test', 'o1', 's1', 'p1')
```

#### Sasisho la Mtihani wa Uunganishaji
```python
class TestCassandraIntegration:
    def test_query_performance_regression(self):
        # Ensure new implementation is faster than old
        old_time = benchmark_legacy_get_po()
        new_time = benchmark_optimized_get_po()
        assert new_time < old_time * 0.5  # At least 50% improvement

    def test_end_to_end_workflow(self):
        # Test complete write -> query -> delete cycle
        # Verify no performance degradation in integration
```

### Mpango wa Kurudisha Nyuma

#### Mbinu ya Kurudisha Nyuma Haraka
1. **Kubadili jenereta la mazingira** - Rudi kwenye jedwali la zamani mara moja
2. **Endelea kutumia jedwali la zamani** - Usifute hadi utendaji uthibitishwe
3. **Arifa za ufuatiliaji** - Vinjari vya kiotomatiki vya kurudisha nyuma kulingana na viwango vya makosa/uwezekano wa kuchelewesha

#### Uthibitisho wa Kurudisha Nyuma
```python
def rollback_to_legacy():
    # Set environment variable
    os.environ['CASSANDRA_USE_LEGACY'] = 'true'

    # Restart services to pick up change
    restart_cassandra_services()

    # Validate functionality
    run_smoke_tests()
```

## Hatari na Mambo ya Kuzingatia

### Hatari za Utendaji
**Kuongezeka kwa muda wa kuandika** - Operesheni 4 za kuandika kwa kila kuingiza (33% zaidi kuliko mfumo wa meza 3)
**Uongezekaji wa matumizi ya nafasi** - Mahitaji 4 ya nafasi (33% zaidi kuliko mfumo wa meza 3)
**Hitilafu za kuandika kwa wingi** - Inahitajika udhibiti wa makosa unaofaa
**Uchaguzi wa kufuta** - Kufuta kwa mkusanyiko inahitaji mzunguko wa kusoma na kisha kufuta

### Hatari za Uendeshaji
**Uchaguzi wa uhamisho** - Uhamishaji wa data kwa data kubwa
**Changamoto za utangamano** - Kuhakikisha meza zote zinaendelea kusawazishwa
**Mapungufu ya ufuatiliaji** - Inahitajika metriki mpya kwa operesheni za meza nyingi

### Mikakati ya Kupunguza Hatari
1. **Uanzishaji wa hatua kwa hatua** - Anza na mkusanyiko mdogo
2. **Ufuatiliaji kamili** - Fuatilia metriki zote za utendaji
3. **Uthibitisho otomatiki** - Uchunguzi wa utangamano wa mara kwa mara
4. **Uwezo wa kurejesha haraka** - Uchaguzi wa meza kulingana na mazingira

## Vigezo vya Mafanikio

### Maboresho ya Utendaji
[ ] **Kuondoa ALLOW FILTERING** - Maswali ya `get_po` na `get_os` yanatumika bila kuchujwa
[ ] **Kupunguza muda wa swali** - Kuboresha kwa 50% au zaidi katika muda wa majibu ya swali
**Usambazaji bora wa mzigo** - Hakuna sehemu zenye mzigo mwingi, usambazaji sare katika kila nodi ya kundi
[ ] **Utendaji unaoweza kuongezeka** - Muda wa swali unalingana na ukubwa wa matokeo, sio data jumla

### Mahitaji ya Utendaji
[ ] **Ulinganishaji wa API** - Msimbo wote uliopo unaendelea kufanya kazi bila mabadiliko
[ ] **Utangamano wa data** - Meza zote tatu zinaendelea kusawazishwa
[ ] **Hakuna upotevu wa data** - Uhamishaji unahifadhi triples zote zilizopo
[ ] **Ulinganishaji wa nyuma** - Uwezo wa kurejea kwenye mpango wa zamani

### Mahitaji ya Uendeshaji
[ ] **Uhamisho salama** - Uanzishaji wa kijani na bluu na uwezo wa kurejesha
[ ] **Mazingira ya ufuatiliaji** - Metri kamili kwa operesheni za meza nyingi
[ ] **Mazingira ya majaribio** - Mfumo wote wa maswali umejaribiwa na viwango vya utendaji
[ ] **Nyaraka** - Mbinu zilizosasishwa za uanzishaji na uendeshaji

## Ratiba

### Awamu ya 1: Utendaji
[ ] Andika upya `cassandra_kg.py` na mpango wa meza nyingi
[ ] Leta operesheni za kuandika kwa wingi
[ ] Ongeza utendaji wa tamko lililoboreshwa
[ ] Sasisha vipimo vya kitengo

### Awamu ya 2: Majaribio ya Uunganisho
[ ] Sasisha vipimo vya uunganisho
[ ] Vipimo vya utendaji
[ ] Majaribio ya mzigo na kiasi cha data ya kweli
[ ] Skripti za uthibitisho wa utangamano wa data

### Awamu ya 3: Upangaji wa Uhamishaji
[ ] Skripti za uanzishaji wa kijani na bluu
[ ] Zana za uhamishaji wa data
[ ] Sasisho za dashibodi ya ufuatiliaji
[ ] Taratibu za kurejesha

### Awamu ya 4: Uanzishaji wa Uzalishaji
[ ] Uanzishaji wa hatua kwa hatua katika uzalishaji
[ ] Ufuatiliaji na uthibitisho wa utendaji
[ ] Usafishaji wa meza za zamani
[ ] Sasisho za nyaraka

## Hitimisho

Mbinu hii ya kupunguza data katika meza nyingi inashughulikia moja kwa moja matatizo mawili muhimu ya utendaji:

1. **Inaondoa ALLOW FILTERING iliyogharimu** kwa kutoa miundo bora ya meza kwa kila mfumo wa swali
2. **Inaboresha ufanisi wa uwekaji** kupitia ufunguo wa pamoja wa sehemu ambazo husambaza mzigo vizuri

Mbinu hii inatumia nguvu za Cassandra huku ikiendelea kudumisha ulinganishaji kamili wa API, kuhakikisha kuwa msimbo uliopo unafaidika kiotomatiki kutoka kwa maboresho ya utendaji.
