---
layout: default
title: "Maelekezo ya Kisaikolojia: Uunganishaji wa Vipengele vya Usanidi wa Cassandra"
parent: "Swahili (Beta)"
---

# Maelekezo ya Kisaikolojia: Uunganishaji wa Vipengele vya Usanidi wa Cassandra

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

**Hali:** Rasimu
**Mwandishi:** Msaidizi
**Tarehe:** 2024-09-03

## Muhtasari

Maelekezo haya yanashughulikia utofauti katika majina na mifumo ya usanidi kwa vigezo vya muunganisho wa Cassandra katika mfumo wa TrustGraph. Kwa sasa, mifumo miwili tofauti ya majina ya vigezo ipo (`cassandra_*` vs `graph_*`), ambayo husababisha mchanganyiko na ugumu wa matengenezo.

## Tatizo

Mfumo wa programu hutumia seti mbili tofauti za vigezo vya usanidi wa Cassandra:

1. **Moduli za /Config/Library za Maarifa** hutumia:
   `cassandra_host` (orodha ya seva)
   `cassandra_user`
   `cassandra_password`

2. **Moduli za /Storage za Grafu** hutumia:
   `graph_host` (seva moja, wakati mwingine hubadilishwa kuwa orodha)
   `graph_username`
   `graph_password`

3. **Uonyeshaji usio sawa wa amri:**
   Baadhi ya vichakata (e.g., `kg-store`) hazionyeshi mipangilio ya Cassandra kama hoja za amri
   Vichakata vingine huonyesha kwa majina na muundo tofauti
   Nakala ya usaidizi haionyeshi maadili chaguo-msingi ya vigezo vya mazingira

Seti zote mbili za vigezo zinaunganisha na kundi sawa la Cassandra lakini kwa mikataba tofauti ya majina, na kusababisha:
Mchanganyiko wa usanidi kwa watumiaji
Ongezeko la mzigo wa matengenezo
Nyaraka zisizo sawa
Uwezekano wa usanidi usio sahihi
Uwezo wa kutofanya ubadilishaji wa mipangilio kupitia hoja za amri katika vichakata vingine

## Suluhisho Lililopendekezwa

### 1. Kuweka Majina ya Vigezo

Moduli zote zitatumia majina sawa ya vigezo ya `cassandra_*`:
`cassandra_host` - Orodha ya seva (hifadhiwa ndani kama orodha)
`cassandra_username` - Jina la mtumiaji kwa uthibitishaji
`cassandra_password` - Nenosiri kwa uthibitishaji

### 2. Hoja za Amri

Vichakata vyote WILIVYO na kuonyesha usanidi wa Cassandra kupitia hoja za amri:
`--cassandra-host` - Orodha iliyoachwa na alama ya mwelekeo wa koma ya seva
`--cassandra-username` - Jina la mtumiaji kwa uthibitishaji
`--cassandra-password` - Nenosiri kwa uthibitishaji

### 3. Usaidizi wa Vigezo vya Mazingira

Ikiwa hoja za amri hazitolewi wazi, mfumo utangalia vigezo vya mazingira:
`CASSANDRA_HOST` - Orodha iliyoachwa na alama ya mwelekeo wa koma ya seva
`CASSANDRA_USERNAME` - Jina la mtumiaji kwa uthibitishaji
`CASSANDRA_PASSWORD` - Nenosiri kwa uthibitishaji

### 4. Maadili Chaguo-msingi

Ikiwa hoja za amri wala vigezo vya mazingira hazibainishwi:
`cassandra_host` huanguka kwenye `["cassandra"]`
`cassandra_username` huanguka kwenye `None` (hakuna uthibitishaji)
`cassandra_password` huanguka kwenye `None` (hakuna uthibitishaji)

### 5. Mahitaji ya Nakala ya Usaidizi

Pato la `--help` lazima:
Kuonyesha maadili ya vigezo vya mazingira kama chaguo-msingi wakati yamepangwa
Kamwe kuonyesha maadili ya nenosiri (onyesha `****` au `<set>` badala yake)
Kuonyesha wazi utaratibu wa utatuzi katika nakala ya usaidizi

Mfano wa pato la usaidizi:
```
--cassandra-host HOST
    Cassandra host list, comma-separated (default: prod-cluster-1,prod-cluster-2)
    [from CASSANDRA_HOST environment variable]

--cassandra-username USERNAME
    Cassandra username (default: cassandra_user)
    [from CASSANDRA_USERNAME environment variable]
    
--cassandra-password PASSWORD  
    Cassandra password (default: <set from environment>)
```

## Maelezo ya Utendaji

### Utaratibu wa Uamuzi wa Vigezo

Kwa kila kiparamu cha Cassandra, utaratibu wa uamuzi utakuwa:
1. Thamani ya hoja ya mstari wa amri
2. Kigezo cha mazingira (`CASSANDRA_*`)
3. Thamani chaguo-msingi

### Usimamizi wa Kiparamu cha Host

Kiparamu cha `cassandra_host`:
Mstari wa amri unapokea mnyororo ulioachiliwa na alama ya kung'aa: `--cassandra-host "host1,host2,host3"`
Kigezo cha mazingira kinapokea mnyororo ulioachiliwa na alama ya kung'aa: `CASSANDRA_HOST="host1,host2,host3"`
Daima kuhifadhiwa kama orodha ndani: `["host1", "host2", "host3"]`
Host moja: `"localhost"` → inabadilishwa kuwa `["localhost"]`
Tayari ni orodha: `["host1", "host2"]` → inatumika kama ilivyo

### Mantiki ya Uthibitisho

Uthibitisho utatumika wakati `cassandra_username` na `cassandra_password` zote zimetolewa:
```python
if cassandra_username and cassandra_password:
    # Use SSL context and PlainTextAuthProvider
else:
    # Connect without authentication
```

## Faili Zinazohitaji Marekebisho

### Moduli zinazotumia vigezo vya `graph_*` (zinazohitaji kubadilishwa):
`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/objects/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/rows/cassandra/write.py`
`trustgraph-flow/trustgraph/query/triples/cassandra/service.py`

### Moduli zinazotumia vigezo vya `cassandra_*` (zinazohitaji kusasishwa na chaguo-msingi la mazingira):
`trustgraph-flow/trustgraph/tables/config.py`
`trustgraph-flow/trustgraph/tables/knowledge.py`
`trustgraph-flow/trustgraph/tables/library.py`
`trustgraph-flow/trustgraph/storage/knowledge/store.py`
`trustgraph-flow/trustgraph/cores/knowledge.py`
`trustgraph-flow/trustgraph/librarian/librarian.py`
`trustgraph-flow/trustgraph/librarian/service.py`
`trustgraph-flow/trustgraph/config/service/service.py`
`trustgraph-flow/trustgraph/cores/service.py`

### Faili za Majaribio Zinazohitaji Kusasishwa:
`tests/unit/test_cores/test_knowledge_manager.py`
`tests/unit/test_storage/test_triples_cassandra_storage.py`
`tests/unit/test_query/test_triples_cassandra_query.py`
`tests/integration/test_objects_cassandra_integration.py`

## Mbinu ya Utendaji

### Hatua ya 1: Unda Msaidizi wa Mpangilio wa Msingi
Unda kazi za matumizi ili kuhakikisha mpangilio wa Cassandra ni sawa katika vichakata vyote:

```python
import os
import argparse

def get_cassandra_defaults():
    """Get default values from environment variables or fallback."""
    return {
        'host': os.getenv('CASSANDRA_HOST', 'cassandra'),
        'username': os.getenv('CASSANDRA_USERNAME'),
        'password': os.getenv('CASSANDRA_PASSWORD')
    }

def add_cassandra_args(parser: argparse.ArgumentParser):
    """
    Add standardized Cassandra arguments to an argument parser.
    Shows environment variable values in help text.
    """
    defaults = get_cassandra_defaults()
    
    # Format help text with env var indication
    host_help = f"Cassandra host list, comma-separated (default: {defaults['host']})"
    if 'CASSANDRA_HOST' in os.environ:
        host_help += " [from CASSANDRA_HOST]"
    
    username_help = f"Cassandra username"
    if defaults['username']:
        username_help += f" (default: {defaults['username']})"
        if 'CASSANDRA_USERNAME' in os.environ:
            username_help += " [from CASSANDRA_USERNAME]"
    
    password_help = "Cassandra password"
    if defaults['password']:
        password_help += " (default: <set>)"
        if 'CASSANDRA_PASSWORD' in os.environ:
            password_help += " [from CASSANDRA_PASSWORD]"
    
    parser.add_argument(
        '--cassandra-host',
        default=defaults['host'],
        help=host_help
    )
    
    parser.add_argument(
        '--cassandra-username',
        default=defaults['username'],
        help=username_help
    )
    
    parser.add_argument(
        '--cassandra-password',
        default=defaults['password'],
        help=password_help
    )

def resolve_cassandra_config(args) -> tuple[list[str], str|None, str|None]:
    """
    Convert argparse args to Cassandra configuration.
    
    Returns:
        tuple: (hosts_list, username, password)
    """
    # Convert host string to list
    if isinstance(args.cassandra_host, str):
        hosts = [h.strip() for h in args.cassandra_host.split(',')]
    else:
        hosts = args.cassandra_host
    
    return hosts, args.cassandra_username, args.cassandra_password
```

### Awamu ya 2: Sasisha Moduli Ukitumia Vigezo vya `graph_*`
1. Badilisha majina ya vigezo kutoka `graph_*` hadi `cassandra_*`
2. Badilisha mbinu (methods) maalum za `add_args()` kwa mbinu za kawaida za `add_cassandra_args()`
3. Tumia kazi (functions) za kawaida za usaidizi wa usanidi
4. Sasisha maandishi ya utangazaji (documentation strings)

Mfano wa mabadiliko:
```python
# OLD CODE
@staticmethod
def add_args(parser):
    parser.add_argument(
        '-g', '--graph-host',
        default="localhost",
        help=f'Graph host (default: localhost)'
    )
    parser.add_argument(
        '--graph-username',
        default=None,
        help=f'Cassandra username'
    )

# NEW CODE  
@staticmethod
def add_args(parser):
    FlowProcessor.add_args(parser)
    add_cassandra_args(parser)  # Use standard helper
```

### Awamu ya 3: Sasisha Moduli Ukitumia Vigezo vya `cassandra_*`
1. Ongeza uunganisha wa hoja za mstari wa amri ambapo haipo (k.m., `kg-store`)
2. Badilisha ufafanuzi wa hoja zilizopo kwa `add_cassandra_args()`
3. Tumia `resolve_cassandra_config()` kwa utaratibu thabiti
4. Hakikisha utunzaji thabiti wa orodha ya seva

### Awamu ya 4: Sasisha Vipimo na Nyaraka
1. Sasisha faili zote za vipimo ili zitumie majina mapya ya vigezo
2. Sasisha nyaraka za CLI
3. Sasisha nyaraka za API
4. Ongeza nyaraka za vigezo vya mazingira

## Ulinganishaji na Mifumo ya Zamani

Ili kudumisha ulinganishaji na mifumo ya zamani wakati wa mabadiliko:

1. **Maonyo ya kutolewa nje** kwa vigezo vya `graph_*`
2. **Ujumuishaji wa vigezo** - kukubali majina ya zamani na mapya awali
3. **Utoaji wa hatua kwa hatua** katika matoleo mengi
4. **Sasisho za nyaraka** pamoja na mwongozo wa uhamishaji

Mfano wa msimbo wa ulinganishaji na mifumo ya zamani:
```python
def __init__(self, **params):
    # Handle deprecated graph_* parameters
    if 'graph_host' in params:
        warnings.warn("graph_host is deprecated, use cassandra_host", DeprecationWarning)
        params.setdefault('cassandra_host', params.pop('graph_host'))
    
    if 'graph_username' in params:
        warnings.warn("graph_username is deprecated, use cassandra_username", DeprecationWarning)
        params.setdefault('cassandra_username', params.pop('graph_username'))
    
    # ... continue with standard resolution
```

## Mbinu ya Majaribio

1. **Majaribio ya kitengo** kwa mantiki ya utatuzi wa usanidi
2. **Majaribio ya ujumuishaji** na mchanganyiko mbalimbali wa usanidi
3. **Majaribio ya vigezo vya mazingira**
4. **Majaribio ya utangamano wa nyuma** na vigezo vilivyotolewa
5. **Majaribio ya Docker compose** na vigezo vya mazingira

## Sasisho za Nyaraka

1. Sasisha nyaraka zote za amri za CLI
2. Sasisha nyaraka za API
3. Unda mwongozo wa uhamishaji
4. Sasisha mifano ya Docker compose
5. Sasisha nyaraka za kumbukumbu ya usanidi

## Hatari na Kupunguza Madhara

| Hatari | Athari | Kupunguza Madhara |
|------|--------|------------|
| Mabadiliko yanayoweza kusababisha matatizo kwa watumiaji | Ya juu | Tekeleza kipindi cha utangamano wa nyuma |
| Uchanganyifu wa usanidi wakati wa mabadiliko | Ya kati | Nyaraka wazi na onyo la kutolewa |
| Kushindwa kwa majaribio | Ya kati | Sasisho kamili ya majaribio |
| Matatizo ya usakinishaji wa Docker | Ya juu | Sasisha mifano yote ya Docker compose |

## Vigezo vya Mafanikio

[ ] Moduli zote hutumia majina ya vigezo `cassandra_*` yanayofanana
[ ] Wasindikaji wote huonyesha mipangilio ya Cassandra kupitia hoja za mstari wa amri
[ ] Nakala ya msaada wa mstari wa amri inaonyesha chaguo-msingi ya vigezo vya mazingira
[ ] Maelezo ya nenosiri hayajaonyeshwa katika nakala ya msaada
[ ] Mfumo wa kurudisha nyuma wa vigezo vya mazingira unafanya kazi vizuri
[ ] `cassandra_host` inashughulikiwa kwa utaratibu kama orodha ndani
[ ] Utangamano wa nyuma umeendelezwa kwa angalau matoleo 2
[ ] Majaribio yote hupita na mfumo mpya wa usanidi
[ ] Nyaraka zimesasishwa kikamilifu
[ ] Mifano ya Docker compose inafanya kazi na vigezo vya mazingira

## Ratiba

**Wiki ya 1:** Tekeleza kusaidia usanidi wa kawaida na sasisha moduli za `graph_*`
**Wiki ya 2:** Ongeza usaidizi wa vigezo vya mazingira kwa moduli zilizopo za `cassandra_*`
**Wiki ya 3:** Sasisha majaribio na nyaraka
**Wiki ya 4:** Majaribio ya ujumuishaji na urekebishaji wa hitilafu

## Mambo ya Kuzingatia ya Baadaye

Fikiria kuongeza muundo huu kwa usanidi mwingine wa hifadhidata (e.g., Elasticsearch)
Tekeleza uthibitisho wa usanidi na ujumbe bora wa kosa
Ongeza usaidizi wa usanidi wa muunganisho wa Cassandra (e.g., pooli)
Fikiria kuongeza usaidizi wa faili za usanidi (.env files)
