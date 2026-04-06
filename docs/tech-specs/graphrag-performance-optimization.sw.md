# GraphRAG Utendaji Uboreshaji Maelezo ya Kiufundi

## Muhtasari

Maelezo haya yanaeleza uboreshaji kamili wa utendaji wa algorithm ya GraphRAG (Graph Retrieval-Augmented Generation) katika TrustGraph. Matumizi ya sasa yana vizuizi vya utendaji muhimu ambavyo hu limit scalability na muda wa majibu. Maelezo haya yanashughulikia maeneo manne makuu ya uboreshaji:

1. **Uboreshaji wa Ufuatiliaji wa Grafu**: Ondoa maswali ya hivi karibuni ya database na utumie utafiti wa kikundi.
2. **Uboreshaji wa Utatuzi wa Labe**: Badilisha upataji wa mlolongo wa lebo kwa operesheni za sambamba/kikundi.
3. **Uboreshaji wa Mkakati wa Kumbukumbu**: Implement caching kwa akili pamoja na uondoshaji wa LRU na utaratibu wa kupata data.
4. **Uboreshaji wa Maswali**: Ongeza kumbukumbu ya matokeo na caching ya embeddings ili kuboresha muda wa majibu.

## Malengo

- **Punguza Idadi ya Maswali ya Database**: Punguza kwa 50-80% jumla ya maswali ya database kupitia kikundi na caching.
- **Boresha Muda wa Majibu**: Lenga ujenzi wa subgraph wa haraka 3-5x na utatuzi wa lebo wa haraka 2-3x.
- **Boresha Scalability**: Unga grafu kubwa zaidi za maarifa na usimamizi bora wa kumbukumbu.
- **Dumishe Usahihi**: Dumishe utendakazi na ubora wa matokeo ya GraphRAG iliyopo.
- **Wezesha Ujazo**: Boresha uwezo wa usindikaji sambamba kwa maombi mengi sambamba.
- **Punguza Uwepo wa Kumbukumbu**: Implement miundo ya data na usimamizi wa kumbukumbu bora.
- **Ongeza Ufuatiliaji**: Jumuisha metriki za utendaji na uwezo wa ufuatiliaji.
- **Hakikisha Utiaji Njia**: Ongeza utunzaji sahihi wa makosa na mitaratibu ya muda.

## Asili

Matumizi ya sasa ya GraphRAG katika `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py` ina masuala muhimu ya utendaji ambayo yanaathiri sana scalability ya mfumo:

### Matatizo ya Sasa ya Utendaji

**1. Ufuatiliaji Usio na Ufanisi wa Grafu (`follow_edges` function, mistari 79-127)**
- Hufanya maswali 3 tofauti ya database kwa kila entiti kwa kila ngazi.
- Mfumo wa swali: maswali yanayozingatia mada, yanayozingatia predikat, na yanayozingatia kitu kwa kila entiti.
- Hakuna kikundi: Kila swali hutumia entiti moja tu wakati mmoja.
- Hakuna ugunduzi wa mzunguko: Inaweza kutembelea nodi sawa mara nyingi.
- Matumizi ya recursive bila kumbukumbu hupelekea utata wa kielelekeo.
- Utata wa muda: O(entities × max_path_length × triple_limit³)

**2. Utatuzi Mfululizo wa Labe (`get_labelgraph` function, mistari 144-171)**
- Hufanya usindikaji wa kila sehemu ya triple (mada, predikat, kitu) mfululizo.
- Kila wito wa `maybe_label` inaweza kusababisha swali la database.
- Hakuna utekelezaji au kikundi sambamba wa maswali ya lebo.
- Hupelekea hadi simu 3 × subgraph_size za database.

**3. Mkakati wa Msingi wa Kumbukumbu (`maybe_label` function, mistari 62-77)**
- Cache rahisi ya kamusi bila mipaka ya saizi au TTL.
- Hakuna sera ya kuondolewa kwa cache hupelekea ukuaji usio na kikomo wa kumbukumbu.
- Upotezaji wa cache husababisha maswali ya database ya kibinafsi.
- Hakuna kupata data au uongezaji mahiri wa cache.

**4. Mfumo Usio bora wa Maswali**
- Maswali ya ufanano wa vector ya entiti hayahifadhiwi kati ya maombi sawa.
- Hakuna kumbukumbu ya matokeo kwa mifumo ya swali iliyorudiwa.
- Uboreshaji wa maswali unokosekana kwa mifumo ya kawaida ya ufikiaji.

**5. Masuala Muhimu ya Muda wa Kitu (`rag.py:96-102`)**
- **Kitu cha GraphRag kinaundwa kila maombi**: Instance mpya huundwa kwa kila swali, na kupoteza faida zote za cache.
- **Kitu cha swali kina muda mfupi sana**: Huundwa na kuharibiwa ndani ya utekelezaji wa swali moja (mistari 201-207).
- **Cache ya lebo huwezeshwa kila maombi**: Uongezaji wa cache na maarifa yaliyokusanywa hayapotei kati ya maombi.
- **Utoaji wa upya wa mteja**: Wateja wa database wanaweza kuanzishwa tena kwa kila maombi.
- **Uboreshaji usio na maombi**: Haiwezi kufaidika na mifumo ya swali au kushiriki matokeo.

### Uchambuzi wa Athari za Utendaji

Jalada la mbaya zaidi linalowezekana kwa swali la kawaida:
- **Uongezaji wa Entiti**: Swali 1 la ufanano wa vector
- **Ufuatiliaji wa Grafu**: entities × max_path_length × 3 × maswali ya triple_limit
- **Utatuzi wa Labe**: maswali ya lebo ya `subgraph_size` × 3 ya kibinafsi

Kwa vigezo vya chagu msingi (entities 50, urefu wa njia 2, kikomo cha triple 30, saizi ya subgraph 150):
- **Maswali ya chini**: 1 + (50 × 2 × 3 × 30) + (150 × 3) = **maswali 9,451 ya database**
- **Muda wa majibu**: 15-30 sekunde kwa grafu za ukubwa wa wastani
- **Matumizi ya kumbukumbu**: Ukuaji usio na kikomo wa cache baada ya muda
- **Ufanisi wa cache**: 0% - caches huwezeshwa kila maombi
- **Utoaji wa kitu**: Kitu cha GraphRag + Kitu cha swali kinaundwa/kuharibiwa kwa kila maombi

Maelezo haya yanashughulikia pengo hizi kwa kutumia maswali ya kikundi, caching kwa akili, na usindikaji sambamba. Kwa kuongeza ufanisi wa mifumo ya swali na ufikiaji wa data, TrustGraph inaweza:
- Unga grafu kubwa za maarifa na milioni ya entiti
- Kutoa muda wa majibu wa chini ya sekunde kwa swali la kawaida
- Kushughulikia maombi ya GraphRAG ya sambamba mamia
- Kuongezeka kwa ufanisi na saizi na utata wa grafu

## Ubunifu wa Kiufundi

### Usanifu

Uboreshaji wa utendaji wa GraphRAG unahitaji vipengele hivi vya kiufundi:

#### 1. **Urekebishaji wa Usanifu wa Muda wa Kitu**
   - **Fanya GraphRag kuwa wa muda mrefu**: Hamisha instance ya GraphRag hadi ngazi ya Processor ili kudumu katika maombi.
   - **Dumishe caches**: Dumishe cache ya lebo, cache ya embedding, na cache ya matokeo ya swali kati ya maombi.
   - **Boresha Kitu cha Swali**: Rekebisha Swali kama muktadha wa utekelezaji nyepesi, sio kontena ya data.
   - **Usaidizi wa miunganisho**: Dumishe miunganisho ya mteja wa database katika maombi.

   Moduli: `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` (imebadilishwa)

#### 2. **Njia Iliyo bora ya Ufuatiliaji wa Grafu**
   - Badilisha `follow_edges` ya recursive na utafutaji wa msingi wa upana wa iterative
   - Implement utunzaji wa kikundi wa entiti katika kila ngazi ya utafutaji
- Ongeza ugunduzi wa mzunguko kwa kufuatilia nodi zilizotembelea
- Jumuisha kumalizika mapema wakati mipaka inafikiwa

   Moduli: `trustgraph-flow/trustgraph/retrieval/graph_rag/optimized_traversal.py`

#### 3. **Mfumo Sambamba wa Utatuzi wa Labe**
   - Kundi maswali ya lebo kwa entiti nyingi wakati mmoja
   - Implement mifumo ya async/kusubiri kwa ufikiaji wa sambamba wa database
   - Ongeza kupata data mahiri kwa mifumo ya kawaida ya lebo
   - Jumusha mikakati ya uongezaji wa lebo

   Moduli: `trustgraph-flow/trustgraph/retrieval/graph_rag/label_resolution.py`

#### 4. **Mkakati wa Kina wa Kumbukumbu**
- Implement cache ya LRU na TTL
- Zana za ufuatiliaji wa utendaji wa cache
- Usalama wa maswali na utunzaji wa rasilimali

**Mbinu ya Ufuatiliaji ya Kumbukumbu**:
```python
class LRUCacheWithTTL:
    def __init__(self, max_size: int, default_ttl: int = 3600):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.access_times = {}

    async def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            # Check TTL expiration
            if time.time() - self.access_times[key] > self.default_ttl:
                del self.cache[key]
                del self.access_times[key]
                return None

            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    async def put(self, key: str, value: Any):
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
```

#### 5. **Uboreshaji wa Swali na Ufuatiliaji**
- **Ukusanyaji wa Metriki za Utendaji**:
- **Upekuzi na Muda**:
- **Usimamizi wa Rasilimali**:
- **Ufuatiliaji**:

**Muda wa Majibu**:
- Ufuatiliaji wa utendaji wa GraphRAG
- Ufuatiliaji wa maswali ya database
- Ufuatiliaji wa matumizi ya kumbukumbu
- Ufuatiliaji wa utekelezaji wa maombi

## Mkakati wa Kujaribu

### Kujaribu Kawaida
- Kujaribu sehemu kwa sehemu kwa utafutaji, caching, na utatuzi wa lebo
- Ujaribu bandia wa mashambulio ya database kwa utendaji
- Kujaribu cache ya uondoshaji na utekelezaji wa TTL
- Kujaribu utunzaji na muda wa makosa

### Kujaribu Kuunganisha
- Kujaribu swali la GraphRAG kamili na uboreshaji
- Kujaribu mashambulio ya database ya kweli
- Kujaribu uendeshaji sambamba na usimamizi wa rasilimali
- Kujaribu ugunduzi na usimamizi wa rasilimali
- Kujaribu utangamano na API iliyopo ya GraphRAG
- Kujaribu na nyuma tofauti za database
- Kuhakikisha usahihi wa matokeo ikilinganisha na utumizi wa sasa

### Kujaribu Utendaji
- Kujaribu utendaji dhidi ya utumizi wa sasa
- Kujaribu mzigo kwa saizi tofauti na utata wa grafu
- Kujaribu shinikizo kwa mipaka ya kumbukumbu na muunganisho
- Kujaribu utangamano kwa uboreshaji wa utendaji

### Kujaribu Utangamano
- Hakikisha utangamano wa API ya GraphRAG iliyopo
- Jaribu na nyuma tofauti za database
- Hakikisha usahihi wa matokeo ikilinganisha na utumizi wa sasa

## Mpango wa Utekelezaji

### Njia ya Utekelezaji Moja kwa Moja
Kwa kuwa API zinaidhinishwa kubadilika, implement uboreshaji moja kwa moja bila utata wa uhamishaji:

1. **Badilisha njia ya `follow_edges`**: Andika upya na utafutaji ulioidhinishwa wa kikundi
2. **Boresha `get_labelgraph`**: Implement utatuzi sambamba wa lebo
3. **Ongeza GraphRag ya muda mrefu**: Badilisha Processor ili itumie instance ya GraphRag iliyodumu
4. **Implement cache ya lebo**: Ongeza safu ya caching kwenye darasa la GraphRag

### Nguvu ya Marekebisho
- **Darasa la swali**: Badilisha ~50 mistari katika `follow_edges`, ongeza ~30 mistari ya utunzaji wa kikundi
- **Darasa la GraphRag**: Ongeza safu ya caching (~40 mistari)
- **Darasa la Processor**: Badilisha ili utumie instance ya GraphRag iliyodumu (~20 mistari)
- **Jumla**: ~140 mistari ya mabadiliko iliyolengwa, haswa ndani ya madarasa yaliyopo

## Ratiba

**Wiki ya 1: Utumizi wa Msingi**
- Badilisha `follow_edges` na utafutaji wa kikundi wa iterative
- Implement utatuzi wa sambamba wa lebo katika `get_labelgraph`
- Ongeza instance ya GraphRag iliyodumu kwa Processor
- Implement safu ya caching ya lebo

**Wiki ya 2: Kujaribu na Kuunganisha**
- Kujaribu kawaida kwa mantiki mpya ya utafutaji na caching
- Kujaribu utendaji dhidi ya utumizi wa sasa
- Kujaribu kuunganisha na data ya grafu ya kweli
- Tathmini ya msimamizi wa msimamizi wa msimamizi wa msimamizi wa msimamizi
- Kujaribu utangamano

**Wiki ya 3: Utekelezaji**
- Tepeleza utumizi uliorekebishwa
- Fuatilia uboreshaji wa utendaji
- Rekebisha TTL ya cache na saizi za kikundi kulingana na matumizi halisi

## Maswali Yaliyofungwa

- **Pooli ya Muunganisho wa Database**: Je, tunapaswa kutumia pooli ya muunganisho ya database maalum au kutegemea pooli ya mteja wa database iliyopo?
- **Usaidizi wa Kumbukumbu**: Je, cache ya lebo na ya embedding inapaswa kuendelea katika kuchelewesha huduma?
- **Kumbukumbu Iliyosambaa**: Kwa usimamizi wa idadi nyingi, je, tunapaswa kutumia kumbukumbu iliyosambaa kwa Redis/Memcached?
- **Umbizo la Matokeo ya Swali**: Je, tunapaswa kuongeza ufanisi wa uwakilishi wa ndani wa triple kwa ufanisi bora wa kumbukumbu?
- **Uunganisho wa Ufuatiliaji**: Metriki gani zinapaswa kuonyeshwa kwenye mifumo ya ufuatiliaji iliyopo (Prometheus, n.k.)?

## Marejeleo

- [Utekelezaji wa awali wa GraphRAG](trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py)
- [Kanuni za Usanifu za TrustGraph](architecture-principles.md)
- [Maelezo ya Usimamizi wa Mkusanyiko](collection-management.md)